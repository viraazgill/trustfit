"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Disclaimer } from "@/components/brand";
import { type Brief, BriefFields, briefPayload, emptyBrief } from "@/components/brief-fields";
import { RequireRole } from "@/lib/auth";
import { type FitConfig, useCreateSme, useFitConfig } from "@/lib/sme-queries";
import { cn } from "@/lib/utils";

const STEPS = ["Company profile", "India entry brief"];

interface Profile {
  name: string;
  city: string;
  employees: string;
  description: string;
}

function Wizard({ cfg }: { cfg: FitConfig }) {
  const router = useRouter();
  const create = useCreateSme();
  const [step, setStep] = useState(0);
  const [profile, setProfile] = useState<Profile>({ name: "", city: "", employees: "", description: "" });
  const [brief, setBrief] = useState<Brief>(() => emptyBrief(cfg));

  const problems = [
    !profile.name.trim() && "Enter your company name",
    step >= 1 && !brief.primary.length && "Pick at least one primary target state",
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
      { onSuccess: (sme) => router.push(`/sme/${sme.id}`) },
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-navy">New SME brief</h1>
        <ol className="mt-3 flex gap-2 text-sm">
          {STEPS.map((s, i) => (
            <li key={s} className={cn("flex items-center gap-2 rounded-full border px-3 py-1", i === step ? "border-navy bg-navy text-white" : i < step ? "border-blue text-blue" : "text-ink-muted")}>
              <span className="font-mono text-xs">{i + 1}</span> {s}
            </li>
          ))}
        </ol>
      </div>

      <div className="rounded-xl border bg-white p-6">
        {step === 0 && (
          <div className="grid gap-5 sm:grid-cols-2">
            <div className="space-y-1.5 sm:col-span-2">
              <Label htmlFor="name">Company name</Label>
              <Input id="name" value={profile.name} onChange={(e) => setProfile({ ...profile, name: e.target.value })} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="city">City (Japan)</Label>
              <Input id="city" value={profile.city} onChange={(e) => setProfile({ ...profile, city: e.target.value })} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="employees">Employees</Label>
              <Input id="employees" type="number" min={1} value={profile.employees} onChange={(e) => setProfile({ ...profile, employees: e.target.value })} />
            </div>
            <div className="space-y-1.5 sm:col-span-2">
              <Label htmlFor="description">What you make</Label>
              <Textarea id="description" value={profile.description} onChange={(e) => setProfile({ ...profile, description: e.target.value })} />
            </div>
          </div>
        )}
        {step === 1 && <BriefFields cfg={cfg} brief={brief} onChange={setBrief} />}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        {step > 0 && (
          <Button variant="outline" onClick={() => setStep(step - 1)}>
            Back
          </Button>
        )}
        {step < STEPS.length - 1 ? (
          <Button onClick={() => setStep(step + 1)} disabled={problems.length > 0}>
            Next
          </Button>
        ) : (
          <Button onClick={submit} disabled={problems.length > 0 || create.isPending}>
            {create.isPending ? "Saving…" : "Save brief"}
          </Button>
        )}
        <span className="text-sm text-verdict-amber">{problems[0]}</span>
        {create.isError && <span className="text-sm text-verdict-red">{create.error.message}</span>}
      </div>
      <Disclaimer />
    </div>
  );
}

export default function NewSme() {
  const { data: cfg } = useFitConfig();
  return <RequireRole role="viewer">{cfg ? <Wizard cfg={cfg} /> : <p className="text-sm text-ink-muted">Loading…</p>}</RequireRole>;
}
