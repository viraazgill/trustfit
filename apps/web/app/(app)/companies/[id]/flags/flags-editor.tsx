"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  type FlagIn,
  useAddFlag,
  useCompany,
  useDeleteFlag,
  useFlags,
  usePublicConfig,
  useRubrics,
  useSetGates,
  useSetTrends,
  useTrends,
} from "@/lib/queries";
import type { GateStatus, Rubrics } from "@/lib/trust-types";
import { cn } from "@/lib/utils";

type FlagType = FlagIn["type"];
const FLAG_TYPES: { type: FlagType; label: string }[] = [
  { type: "knockout", label: "Knock-out" },
  { type: "cap", label: "Cap" },
  { type: "notch", label: "Notch" },
  { type: "fake_reviews", label: "Fake reviews" },
];
const GATE_STATES: GateStatus[] = ["passed", "pending", "failed"];
const DIRECTIONS = ["improving", "stable", "worsening"] as const;

function codesFor(type: FlagType, rubrics: Rubrics): Record<string, string> {
  const ov = rubrics.overrides;
  if (type === "knockout") return Object.fromEntries(Object.entries(ov.knockouts).map(([k, v]) => [k, v.label]));
  if (type === "cap") return Object.fromEntries(Object.entries(ov.caps).map(([k, v]) => [k, `${v.label} (max ${v.max_score})`]));
  if (type === "notch")
    return Object.fromEntries(Object.entries(ov.notches).map(([k, v]) => [k, `${v.label} (${v.points > 0 ? "+" : ""}${v.points})`]));
  return { fake_reviews: ov.fake_reviews.label };
}

function Segmented<T extends string>({ value, options, onChange, label }: { value: T; options: readonly T[]; onChange: (v: T) => void; label: string }) {
  return (
    <div className="inline-flex overflow-hidden rounded-md border" role="radiogroup" aria-label={label}>
      {options.map((o) => (
        <button
          key={o}
          type="button"
          role="radio"
          aria-checked={value === o}
          onClick={() => onChange(o)}
          className={cn("border-l px-3 py-1 text-xs first:border-l-0", value === o ? "bg-navy text-white" : "bg-white hover:bg-muted")}
        >
          {o}
        </button>
      ))}
    </div>
  );
}

function Card({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border bg-white p-5">
      <h2 className="text-sm font-semibold uppercase tracking-wider text-ink-muted">{title}</h2>
      {hint && <p className="mb-3 text-xs text-ink-muted">{hint}</p>}
      {children}
    </section>
  );
}

function FlagsCard({ id, rubrics }: { id: string; rubrics: Rubrics }) {
  const { data: flags } = useFlags(id);
  const add = useAddFlag(id);
  const del = useDeleteFlag(id);
  const [type, setType] = useState<FlagType>("knockout");
  const codes = codesFor(type, rubrics);
  const [code, setCode] = useState(Object.keys(codes)[0]);
  const [note, setNote] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");

  function pickType(t: FlagType) {
    setType(t);
    setCode(Object.keys(codesFor(t, rubrics))[0]);
  }

  return (
    <Card title="Knock-outs, caps, notches and fake reviews" hint="Each flag needs its evidence. Knock-outs make the company not eligible (Red, no score).">
      <ul className="mb-4 divide-y" data-testid="flag-list">
        {(flags ?? []).length === 0 && <li className="py-2 text-sm text-ink-muted">No flags recorded.</li>}
        {(flags ?? []).map((f) => (
          <li key={f.id} className="flex items-start gap-3 py-2 text-sm">
            <span className="w-24 shrink-0 text-xs font-medium uppercase text-coral">{f.type.replace("_", " ")}</span>
            <span className="flex-1">
              {codesFor(f.type as FlagType, rubrics)[f.code] ?? f.code}
              {f.note && <span className="block text-xs text-ink-muted">{f.note}</span>}
              {f.source_url && (
                <a href={f.source_url} target="_blank" rel="noreferrer" className="block text-xs text-blue hover:underline">
                  {f.source_url}
                </a>
              )}
            </span>
            <Button size="sm" variant="outline" onClick={() => del.mutate(f.id)} disabled={del.isPending}>
              Remove
            </Button>
          </li>
        ))}
      </ul>
      <form
        className="grid gap-2 border-t pt-4 sm:grid-cols-[auto_1fr]"
        onSubmit={(e) => {
          e.preventDefault();
          add.mutate(
            { type, code, note: note || null, source_url: sourceUrl || null },
            { onSuccess: () => (setNote(""), setSourceUrl("")) },
          );
        }}
      >
        <select aria-label="Flag type" className="h-8 rounded-md border bg-white px-2 text-sm" value={type} onChange={(e) => pickType(e.target.value as FlagType)}>
          {FLAG_TYPES.map((t) => (
            <option key={t.type} value={t.type}>
              {t.label}
            </option>
          ))}
        </select>
        <select aria-label="Flag code" className="h-8 rounded-md border bg-white px-2 text-sm" value={code} onChange={(e) => setCode(e.target.value)}>
          {Object.entries(codes).map(([k, label]) => (
            <option key={k} value={k}>
              {label}
            </option>
          ))}
        </select>
        <Input placeholder="Evidence note" value={note} onChange={(e) => setNote(e.target.value)} className="h-8 text-sm sm:col-span-2" />
        <Input placeholder="Evidence source URL" value={sourceUrl} onChange={(e) => setSourceUrl(e.target.value)} className="h-8 text-sm sm:col-span-2" />
        <div className="flex items-center gap-3 sm:col-span-2">
          <Button type="submit" disabled={add.isPending}>
            Add flag
          </Button>
          {add.isError && <span className="text-xs text-verdict-red">{add.error.message}</span>}
        </div>
      </form>
    </Card>
  );
}

function GatesCard({ id }: { id: string }) {
  const { data: cfg } = usePublicConfig();
  const { data: company } = useCompany(id);
  const set = useSetGates(id);
  return (
    <Card title="Verification gates" hint="Failed → Red. Pending → Amber at best.">
      <ul className="space-y-2">
        {Object.entries(cfg?.gates ?? {}).map(([g, spec]) => (
          <li key={g} className="flex flex-wrap items-center gap-3 text-sm">
            <span className="w-7 font-mono text-xs text-blue">{g}</span>
            <span className="flex-1">{spec.label}</span>
            <Segmented
              label={`${g} status`}
              value={(company?.gates[g] ?? "pending") as GateStatus}
              options={GATE_STATES}
              onChange={(v) => set.mutate({ [g]: v })}
            />
          </li>
        ))}
      </ul>
    </Card>
  );
}

function TrendsCard({ id }: { id: string }) {
  const { data: cfg } = usePublicConfig();
  const { data: trends } = useTrends(id);
  const set = useSetTrends(id);
  return (
    <Card title="Trend signals (outlook)" hint="3 or more improving → Positive; 3 or more worsening → Watch; else Stable. Never changes the verdict.">
      <ul className="space-y-3">
        {Object.entries(cfg?.outlook_signals ?? {}).map(([key, label]) => {
          const t = trends?.[key];
          return (
            <li key={key} className="grid items-center gap-2 text-sm sm:grid-cols-[1fr_auto]">
              <span>{label}</span>
              <Segmented
                label={`${label} direction`}
                value={t?.direction ?? ("" as never)}
                options={DIRECTIONS}
                onChange={(direction) => set.mutate({ [key]: { direction, note: t?.note ?? null } })}
              />
              {t && (
                <Input
                  defaultValue={t.note ?? ""}
                  placeholder="Note (e.g. FY24 → FY25 figures)"
                  className="h-8 text-xs sm:col-span-2"
                  onBlur={(e) => e.target.value !== (t.note ?? "") && set.mutate({ [key]: { direction: t.direction, note: e.target.value || null } })}
                />
              )}
            </li>
          );
        })}
      </ul>
    </Card>
  );
}

export default function FlagsPage() {
  const { id } = useParams<{ id: string }>();
  const { data: rubrics } = useRubrics();
  if (!rubrics) return <p className="text-sm text-ink-muted">Loading…</p>;
  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <div className="lg:row-span-2">
        <FlagsCard id={id} rubrics={rubrics} />
      </div>
      <GatesCard id={id} />
      <TrendsCard id={id} />
    </div>
  );
}
