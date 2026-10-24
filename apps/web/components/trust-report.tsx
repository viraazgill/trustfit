"use client";

/** The SME-facing Trust report: categories, weights, scores and reasons only (never rubric detail). */
import { CategoryBar, ConfidenceMeter, DimensionCard, ReasonsList, ScoreCard } from "@/components/trust";
import { num } from "@/lib/format";
import { usePublicConfig } from "@/lib/queries";
import type { TrustReport } from "@/lib/sme-queries";
import type { Verdict } from "@/lib/trust-types";

export function TrustReportView({ report }: { report: TrustReport }) {
  const { data: cfg } = usePublicConfig();
  const dimensions = report.dimensions ?? {};
  const categories = report.categories ?? {};
  const pending = report.pending ?? [];
  if (!cfg) return null;
  const minVerified = cfg.confidence.dimension_provisional_below;
  return (
    <div className="space-y-5">
      <div className="grid gap-5 md:grid-cols-[1.2fr_1fr]">
        <ScoreCard
          status={report.status}
          score={report.score}
          band={report.band}
          verdict={report.verdict as Verdict}
          provisional={report.provisional}
          outlook={report.outlook}
        />
        <ConfidenceMeter
          value={report.confidence}
          noScoreBelow={cfg.confidence.no_score_below}
          provisionalBelow={cfg.confidence.provisional_below}
        />
      </div>
      {Object.keys(dimensions).length > 0 && (
        <div className="grid gap-4 sm:grid-cols-3">
          {Object.entries(dimensions).map(([key, d]) => (
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
        <section className="rounded-xl border bg-white p-5">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-ink-muted">Why {report.verdict}</h2>
          <ReasonsList reasons={report.reasons} />
        </section>
        <section className="rounded-xl border bg-white p-5" data-testid="what-turns-it-green">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-ink-muted">What turns it Green</h2>
          {pending.length === 0 ? (
            <p className="text-sm text-ink-muted">Nothing left to check.</p>
          ) : (
            <ul className="space-y-1.5 text-sm">
              {pending.map((p) => (
                <li key={`${p.type}-${p.id}`} className="flex gap-3">
                  <span className="w-7 shrink-0 font-mono text-xs font-semibold text-blue">{p.id}</span>
                  <span className="flex-1">
                    {p.type === "gate" ? `Verification gate: ${p.label}` : `${p.label}: ${p.count} check${p.count > 1 ? "s" : ""} to run`}
                    {p.priority && <span className="ml-2 text-xs font-medium text-verdict-amber">first</span>}
                  </span>
                  {p.points !== null && <span className="text-xs text-ink-muted">{num(p.points)} pts</span>}
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
      {Object.keys(categories).length > 0 && (
        <section className="rounded-xl border bg-white p-5">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-ink-muted">
            Categories and weights (pale = under half verified)
          </h2>
          {Object.entries(categories).map(([key, c]) => (
            <CategoryBar
              key={key}
              id={key}
              label={c.label}
              scorePct={c.score_pct}
              verifiedPct={c.verified_pct}
              points={c.weight}
              minVerified={minVerified}
            />
          ))}
        </section>
      )}
    </div>
  );
}
