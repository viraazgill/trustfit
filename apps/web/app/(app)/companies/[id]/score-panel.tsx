"use client";

import { Suspense, useState } from "react";
import { useParams, usePathname, useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CategoryBar, ConfidenceMeter, DimensionCard, ReasonsList, ScoreCard } from "@/components/trust";
import { WhatIfDrawer } from "@/components/what-if-drawer";
import { humanize, num } from "@/lib/format";
import { defaultRole } from "@/lib/roles";
import { useCompany, usePublicConfig, useRubrics, useTrends, useTrustScore } from "@/lib/queries";
import type { TrustResult, WhatIf } from "@/lib/trust-types";

function Section({ title, children, className }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <section className={`rounded-xl border bg-white p-5 ${className ?? ""}`}>
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-ink-muted">{title}</h2>
      {children}
    </section>
  );
}

function Overrides({ r }: { r: TrustResult }) {
  const { data: rubrics } = useRubrics();
  if (r.status !== "scored") return <p className="text-sm text-ink-muted">Not applied: no score was issued.</p>;
  const notchLabel = (code: string) => rubrics?.overrides.notches[code]?.label ?? humanize(code);
  const capLabel = (code: string) => rubrics?.overrides.caps[code]?.label ?? humanize(code);
  const bound = { score: "Score + notches", weakest_link: "Weakest-link limit", cap: "Cap" }[r.binding_limit ?? "score"];
  return (
    <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm" data-testid="overrides">
      <dt className="text-ink-muted">Base score</dt>
      <dd className="font-mono">{num(r.base_score)}</dd>
      <dt className="text-ink-muted">Notches</dt>
      <dd>
        <span className="font-mono">{r.notches! > 0 ? `+${r.notches}` : r.notches}</span>
        {r.notch_list!.map((n) => (
          <div key={n.code} className="text-xs text-ink-muted">
            {n.points > 0 ? `+${n.points}` : n.points} {notchLabel(n.code)}
          </div>
        ))}
      </dd>
      <dt className="text-ink-muted">Weakest-link limit</dt>
      <dd className="font-mono">
        {num(r.weakest_limit)} <span className="text-xs text-ink-muted">(weakest dimension {num(r.weakest_dimension, 1)} + margin)</span>
      </dd>
      <dt className="text-ink-muted">Cap</dt>
      <dd>
        {r.cap ? <span className="font-mono">{r.cap}</span> : "None"}
        {r.cap_list!.map((c) => (
          <div key={c.code} className="text-xs text-ink-muted">
            {c.max_score}: {capLabel(c.code)}
          </div>
        ))}
      </dd>
      <dt className="text-ink-muted">Binding</dt>
      <dd className="font-medium text-navy" data-testid="binding">
        {bound} → final {num(r.score_raw)} shown as {r.score}
      </dd>
    </dl>
  );
}

function Outlook({ id, outlook }: { id: string; outlook: string | null }) {
  const { data: trends } = useTrends(id);
  const { data: cfg } = usePublicConfig();
  const arrow = { improving: "▲", stable: "▶", worsening: "▼" } as const;
  const color = { improving: "text-verdict-green", stable: "text-ink-muted", worsening: "text-verdict-red" } as const;
  return (
    <div>
      <p className="mb-2 text-sm">
        Outlook: <span className="font-semibold text-navy">{outlook ?? "—"}</span>{" "}
        <span className="text-xs text-ink-muted">(shown beside the verdict; never changes it)</span>
      </p>
      <ul className="space-y-1 text-sm">
        {Object.entries(cfg?.outlook_signals ?? {}).map(([key, label]) => {
          const t = trends?.[key];
          return (
            <li key={key} className="flex justify-between gap-3">
              <span>{label}</span>
              {t ? (
                <span className={color[t.direction]}>
                  {arrow[t.direction]} {t.direction}
                </span>
              ) : (
                <span className="text-ink-muted">not entered</span>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function NextChecks({ r }: { r: TrustResult }) {
  const { data: rubrics } = useRubrics();
  const checks = r.next_checks ?? [];
  if (!checks.length) return <p className="text-sm text-ink-muted">Nothing left to check.</p>;
  return (
    <ol className="space-y-2 text-sm" data-testid="next-checks">
      {checks.slice(0, 12).map((c) => (
        <li key={`${c.type}-${c.id}`} className="flex gap-3">
          <span className="w-8 shrink-0 font-mono font-semibold text-blue">{c.id}</span>
          <span className="flex-1">
            <span className="text-navy">
              {c.type === "gate" ? rubrics?.gates[c.id]?.label : rubrics?.parameters[c.id]?.name}
            </span>
            <span className="block text-xs text-ink-muted">{c.check}</span>
          </span>
          {c.points !== undefined && (
            <span className="shrink-0 text-xs text-ink-muted">
              {num(c.points)} pts · {c.status}
            </span>
          )}
        </li>
      ))}
      {checks.length > 12 && <li className="text-xs text-ink-muted">…and {checks.length - 12} more</li>}
    </ol>
  );
}

function ScorePanel({ id }: { id: string }) {
  const { data: cfg } = usePublicConfig();
  const { data: company } = useCompany(id);
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const [whatIf, setWhatIf] = useState<WhatIf | null>(null);

  const role = params.get("role") ?? defaultRole(company, cfg);
  const base = useTrustScore(id, role);
  const preview = useTrustScore(id, role, whatIf);
  const run = whatIf ? preview.data : base.data;
  const r = run?.result;

  if (!cfg || !role) return <p className="text-sm text-ink-muted">Loading…</p>;
  const minVerified = cfg.confidence.dimension_provisional_below;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Tabs
          value={role}
          onValueChange={(v) => {
            setWhatIf(null);
            router.replace(`${pathname}?role=${v}`);
          }}
        >
          <TabsList>
            {Object.entries(cfg.roles).map(([key, v]) => (
              <TabsTrigger key={key} value={key}>
                {v.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
        <div className="flex items-center gap-2">
          {whatIf && (
            <Button variant="outline" onClick={() => setWhatIf(null)}>
              Exit what-if
            </Button>
          )}
          {base.data && <WhatIfDrawer base={base.data.result} preview={preview.data?.result} whatIf={whatIf} onChange={setWhatIf} />}
        </div>
      </div>

      {whatIf && (
        <div data-testid="what-if-banner" className="rounded-lg border border-coral bg-coral/10 px-4 py-2 text-sm text-navy">
          <strong>What-if preview, not saved.</strong> Real evidence is unchanged; this run is flagged and never shown to SMEs.
        </div>
      )}
      {(base.error || preview.error) && <p className="text-sm text-verdict-red">{(base.error ?? preview.error)!.message}</p>}

      {r && (
        <>
          <div className="grid gap-5 md:grid-cols-[1.2fr_1fr]">
            <ScoreCard status={r.status} score={r.score} band={r.band} verdict={r.verdict} provisional={r.provisional} outlook={r.outlook} />
            <ConfidenceMeter
              value={r.confidence}
              noScoreBelow={cfg.confidence.no_score_below}
              provisionalBelow={cfg.confidence.provisional_below}
            />
          </div>

          {r.dimensions && (
            <div className="grid gap-4 sm:grid-cols-3">
              {Object.entries(r.dimensions).map(([key, d]) => (
                <DimensionCard
                  key={key}
                  label={d.label}
                  question={cfg.dimensions[key]?.question}
                  scorePct={d.score_pct}
                  verifiedPct={d.verified_pct}
                  minVerified={minVerified}
                />
              ))}
            </div>
          )}

          <div className="grid gap-5 lg:grid-cols-2">
            <Section title={`Verdict: ${r.verdict}`}>
              <ReasonsList reasons={r.reasons} />
            </Section>
            <Section title="Overrides applied">
              <Overrides r={r} />
            </Section>
          </div>

          {r.categories && (
            <Section title="Categories (bar = score; pale = under half verified)">
              {Object.entries(r.categories).map(([key, c]) => (
                <CategoryBar
                  key={key}
                  id={key}
                  label={c.label}
                  scorePct={c.score_pct}
                  verifiedPct={c.verified_pct}
                  verifiedPoints={c.verified_points}
                  points={c.points}
                  minVerified={minVerified}
                />
              ))}
            </Section>
          )}

          <div className="grid gap-5 lg:grid-cols-2">
            <Section title="What turns it Green">
              <NextChecks r={r} />
            </Section>
            <Section title="Outlook">
              <Outlook id={id} outlook={r.outlook} />
            </Section>
          </div>
          <p className="text-xs text-ink-muted">
            Weight set {r.weight_set} · scored as of {r.as_of} · run #{run!.run_id}
            {run!.is_what_if && " (what-if)"}
          </p>
        </>
      )}
    </div>
  );
}

export default function CompanyScorePage() {
  const { id } = useParams<{ id: string }>();
  return (
    <Suspense>
      <ScorePanel id={id} />
    </Suspense>
  );
}
