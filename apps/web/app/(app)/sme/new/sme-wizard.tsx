"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Disclaimer } from "@/components/brand";
import { type Brief, BriefFields, briefPayload, emptyBrief } from "@/components/brief-fields";
import { ReadinessForm } from "@/components/readiness-form";
import { RequireRole } from "@/lib/auth";
import { api } from "@/lib/api/client";
import { type BridgeConfig, useBridgeConfig } from "@/lib/bridge-queries";
import { type FitConfig, useCreateSme, useFitConfig } from "@/lib/sme-queries";
import { cn } from "@/lib/utils";

const STEPS = ["profile", "brief", "readiness"] as const;

interface Profile {
  name: string;
  city: string;
  employees: string;
  description: string;
}

function Wizard({ cfg, bridgeCfg }: { cfg: FitConfig; bridgeCfg: BridgeConfig }) {
  const t = useTranslations("brief");
  const router = useRouter();
  const create = useCreateSme();
  const [step, setStep] = useState(0);
  const [profile, setProfile] = useState<Profile>({ name: "", city: "", employees: "", description: "" });
  const [brief, setBrief] = useState<Brief>(() => emptyBrief(cfg));
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [saveError, setSaveError] = useState<string | null>(null);
  const questionCount = Object.values(bridgeCfg.dimensions).reduce((n, d) => n + Object.keys(d.questions).length, 0);

  const problems = [
    !profile.name.trim() && t("problem.name"),
    step >= 1 && !brief.primary.length && t("problem.primary"),
    step >= 2 && Object.keys(answers).length < questionCount && t("problem.answers"),
  ].filter(Boolean) as string[];

  function submit() {
    create.mutate(
      {
        name: profile.name.trim(),
        country: "Japan",
        city: profile.city || null,
        employees: profile.employees ? Number(profile.employees) : null,
        description: profile.description || null,
        ...briefPayload(brief, cfg),
      },
      {
        onSuccess: async (sme) => {
          try {
            await api(`/smes/${sme.id}/readiness`, "PUT", { answers });
            router.push(`/sme/${sme.id}`);
          } catch (err) {
            setSaveError(err instanceof Error ? err.message : t("readinessSaveFailed"));
          }
        },
      },
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-navy">{t("newTitle")}</h1>
        <ol className="mt-3 flex gap-2 text-sm">
          {STEPS.map((s, i) => (
            <li key={s} className={cn("flex items-center gap-2 rounded-full border px-3 py-1", i === step ? "border-navy bg-navy text-white" : i < step ? "border-blue text-blue" : "text-ink-muted")}>
              <span className="font-mono text-xs">{i + 1}</span> {t(`steps.${s}`)}
            </li>
          ))}
        </ol>
      </div>

      <div className="rounded-xl border bg-white p-6">
        {step === 0 && (
          <div className="grid gap-5 sm:grid-cols-2">
            <div className="space-y-1.5 sm:col-span-2">
              <Label htmlFor="name">{t("companyName")}</Label>
              <Input id="name" value={profile.name} onChange={(e) => setProfile({ ...profile, name: e.target.value })} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="city">{t("city")}</Label>
              <Input id="city" value={profile.city} onChange={(e) => setProfile({ ...profile, city: e.target.value })} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="employees">{t("employees")}</Label>
              <Input id="employees" type="number" min={1} value={profile.employees} onChange={(e) => setProfile({ ...profile, employees: e.target.value })} />
            </div>
            <div className="space-y-1.5 sm:col-span-2">
              <Label htmlFor="description">{t("whatYouMake")}</Label>
              <Textarea id="description" value={profile.description} onChange={(e) => setProfile({ ...profile, description: e.target.value })} />
            </div>
          </div>
        )}
        {step === 1 && <BriefFields cfg={cfg} brief={brief} onChange={setBrief} />}
        {step === 2 && <ReadinessForm cfg={bridgeCfg} answers={answers} onChange={setAnswers} />}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        {step > 0 && (
          <Button variant="outline" onClick={() => setStep(step - 1)}>
            {t("back")}
          </Button>
        )}
        {step < STEPS.length - 1 ? (
          <Button onClick={() => setStep(step + 1)} disabled={problems.length > 0}>
            {t("next")}
          </Button>
        ) : (
          <Button onClick={submit} disabled={problems.length > 0 || create.isPending}>
            {create.isPending ? t("saving") : t("save")}
          </Button>
        )}
        <span className="text-sm text-verdict-amber">{problems[0]}</span>
        {create.isError && <span className="text-sm text-verdict-red">{create.error.message}</span>}
        {saveError && <span className="text-sm text-verdict-red">{saveError}</span>}
      </div>
      <Disclaimer />
    </div>
  );
}

export default function NewSme() {
  const { data: cfg } = useFitConfig();
  const { data: bridgeCfg } = useBridgeConfig();
  return (
    <RequireRole role="viewer">
      {cfg && bridgeCfg ? <Wizard cfg={cfg} bridgeCfg={bridgeCfg} /> : <p className="text-sm text-ink-muted">Loading…</p>}
    </RequireRole>
  );
}
