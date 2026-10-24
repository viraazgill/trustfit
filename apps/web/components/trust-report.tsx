"use client";

/** The SME-facing Trust report: categories, weights, scores and reasons only (never rubric detail). */
import { useTranslations } from "next-intl";
import { CategoryBar, ConfidenceMeter, DimensionCard, ReasonsList, ScoreCard } from "@/components/trust";
import { num } from "@/lib/format";
import { useLabel } from "@/lib/i18n";
import { usePublicConfig } from "@/lib/queries";
import type { TrustReport } from "@/lib/sme-queries";
import type { Verdict } from "@/lib/trust-types";

export function TrustReportView({ report }: { report: TrustReport }) {
  const { data: cfg } = usePublicConfig();
  const t = useTranslations("trust");
  const tc = useTranslations("common");
  const label = useLabel();
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
              label={label(`trustDimensions.${key}.label`, d.label)}
              question={label(`trustDimensions.${key}.question`, cfg.dimensions[key]?.question ?? "")}
              scorePct={d.score_pct}
              verifiedPct={d.verified_pct}
              minVerified={minVerified}
            />
          ))}
        </div>
      )}
      <div className="grid gap-5 lg:grid-cols-2">
        <section className="rounded-xl border bg-white p-5">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-ink-muted">{t("why", { verdict: report.verdict })}</h2>
          <ReasonsList reasons={report.reasons} />
        </section>
        <section className="rounded-xl border bg-white p-5" data-testid="what-turns-it-green">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-ink-muted">{t("whatTurnsGreen")}</h2>
          {pending.length === 0 ? (
            <p className="text-sm text-ink-muted">{t("nothingLeft")}</p>
          ) : (
            <ul className="space-y-1.5 text-sm">
              {pending.map((p) => (
                <li key={`${p.type}-${p.id}`} className="flex gap-3">
                  <span className="w-7 shrink-0 font-mono text-xs font-semibold text-blue">{p.id}</span>
                  <span className="flex-1">
                    {p.type === "gate"
                      ? t("gateLine", { label: label(`gates.${p.id}`, p.label) })
                      : t("checksToRun", { label: label(`trustCategories.${p.id}`, p.label), count: p.count })}
                    {p.priority && <span className="ml-2 text-xs font-medium text-verdict-amber">{t("first")}</span>}
                  </span>
                  {p.points !== null && <span className="text-xs text-ink-muted">{tc("pts", { points: num(p.points) })}</span>}
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
      {Object.keys(categories).length > 0 && (
        <section className="rounded-xl border bg-white p-5">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-ink-muted">
            {t("categoriesWeights")}
          </h2>
          {Object.entries(categories).map(([key, c]) => (
            <CategoryBar
              key={key}
              id={key}
              label={label(`trustCategories.${key}`, c.label)}
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
