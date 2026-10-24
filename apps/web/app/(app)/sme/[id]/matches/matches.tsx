"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { FictionalBadge } from "@/components/brand";
import { SeverityChip } from "@/components/bridge";
import { FitCategoryChip } from "@/components/fit";
import { VerdictChip } from "@/components/trust";
import { type BridgeCompany, useBridge, useReadiness } from "@/lib/bridge-queries";
import { useExclusionText } from "@/lib/exclusions";
import { useLabel } from "@/lib/i18n";
import { num, rhu } from "@/lib/format";
import { useFitConfig } from "@/lib/sme-queries";
import type { Verdict } from "@/lib/trust-types";

function CompanyLink({ smeId, c }: { smeId: string; c: Pick<BridgeCompany, "company_id" | "name" | "fictional"> }) {
  return (
    <span className="inline-flex flex-wrap items-center gap-2">
      <Link href={`/sme/${smeId}/company/${c.company_id}`} className="font-medium text-blue hover:underline">
        {c.name}
      </Link>
      {c.fictional && <FictionalBadge />}
    </span>
  );
}

function Trust({ c }: { c: BridgeCompany }) {
  const t = useTranslations("bridge");
  return (
    <span className="inline-flex items-center gap-2">
      <span className="font-mono">{c.trust_score ?? "—"}</span>
      <VerdictChip verdict={c.trust_verdict as Verdict} size="sm" />
      {c.provisional && <span className="text-xs text-ink-muted">{t("provisional")}</span>}
    </span>
  );
}

/** Primary partner ranking, per-gap shortlists and excluded companies, all from the Gap Bridge. */
export default function Matches() {
  const { id } = useParams<{ id: string }>();
  const { data: readiness } = useReadiness(id);
  const { data: fitCfg } = useFitConfig();
  const bridge = useBridge(id, !!readiness?.answered);
  const t = useTranslations("bridge");
  const tl = useLabel();
  const exclusionText = useExclusionText();
  if (readiness && !readiness.answered)
    return (
      <p className="text-sm text-ink-muted">
        {t.rich("answerFirst", {
          link: () => (
            <Link href={`/sme/${id}`} className="text-blue hover:underline">
              {t("readinessLink")}
            </Link>
          ),
        })}
      </p>
    );
  if (bridge.error) return <p className="text-sm text-verdict-red">{bridge.error.message}</p>;
  const b = bridge.data;
  if (!b || !fitCfg) return <p className="text-sm text-ink-muted">{t("matching")}</p>;

  const byId = Object.fromEntries(b.companies.map((c) => [c.company_id, c]));
  const excluded = b.companies.filter((c) => !c.eligible);

  return (
    <div className="space-y-6">
      <section className="rounded-xl border bg-white p-5">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-ink-muted">{t("ranking")}</h2>
        <p className="mb-3 text-xs text-ink-muted">{t("rankingHelp")}</p>
        <table className="w-full text-sm" data-testid="primary-ranking">
          <thead>
            <tr className="border-b text-left text-xs text-ink-muted">
              <th className="py-2 font-normal">#</th>
              <th className="py-2 font-normal">{t("company")}</th>
              <th className="py-2 font-normal">{t("trust")}</th>
              <th className="py-2 font-normal">{t("fit")}</th>
              <th className="py-2 text-right font-normal">{t("gapCoverage")}</th>
              <th className="py-2 text-right font-normal">{t("match")}</th>
            </tr>
          </thead>
          <tbody>
            {b.primary_ranking.map((r, i) => {
              const c = byId[r.company_id];
              return (
                <tr key={r.company_id} className="border-b last:border-0" data-testid={`rank-${r.company_id}`}>
                  <td className="py-2 font-mono text-ink-muted">{i + 1}</td>
                  <td className="py-2">
                    <CompanyLink smeId={id} c={c} />
                  </td>
                  <td className="py-2">
                    <Trust c={c} />
                  </td>
                  <td className="py-2">
                    <span className="inline-flex items-center gap-2">
                      <span className="font-mono">{r.fit}</span>
                      <FitCategoryChip category={c.fit_category!} label={fitCfg.categories[c.fit_category!]?.label ?? ""} />
                    </span>
                  </td>
                  <td className="py-2 text-right font-mono">{rhu(r.gap_coverage, 1)}%</td>
                  <td className="py-2 text-right font-mono font-semibold text-navy">{num(r.match, 2)}</td>
                </tr>
              );
            })}
            {b.primary_ranking.length === 0 && (
              <tr>
                <td colSpan={6} className="py-3 text-ink-muted">
                  {t("noneFits")}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>

      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-ink-muted">{t("whoFills")}</h2>
        <div className="grid gap-4 md:grid-cols-2">
          {Object.entries(b.per_gap).map(([gap, entries]) => {
            const d = b.readiness[gap];
            return (
              <div key={gap} className="rounded-xl border bg-white p-4" data-testid={`shortlist-${gap}`}>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium text-navy">
                    <span className="mr-2 font-mono text-xs text-blue">{gap}</span>
                    {tl(`readiness.${gap}.label`, d.label)}
                  </span>
                  <SeverityChip label={d.severity_label} />
                </div>
                <ol className="mt-3 space-y-2 text-sm">
                  {entries.map((e) => {
                    const c = byId[e.company_id];
                    return (
                      <li key={e.company_id}>
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <CompanyLink smeId={id} c={c} />
                          <span className="flex items-center gap-2 text-xs text-ink-muted">
                            {t("covers", { pct: rhu(100 * e.coverage) })} <VerdictChip verdict={c.trust_verdict as Verdict} size="sm" />
                          </span>
                        </div>
                        <div className="text-xs text-ink-muted">{e.reason}</div>
                      </li>
                    );
                  })}
                  {entries.length === 0 && <li className="text-xs text-ink-muted">{t("noneCovers")}</li>}
                </ol>
              </div>
            );
          })}
        </div>
      </section>

      <section className="rounded-xl border bg-white p-5" data-testid="excluded">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-ink-muted">{t("excluded")}</h2>
        <p className="mb-3 text-xs text-ink-muted">{t("excludedHelp")}</p>
        <ul className="divide-y text-sm">
          {excluded.map((c) => (
            <li key={c.company_id} className="flex flex-wrap items-center justify-between gap-2 py-2" data-testid={`excluded-${c.company_id}`}>
              <CompanyLink smeId={id} c={c} />
              <span className="flex flex-wrap items-center gap-2">
                <span className="text-verdict-red">{c.excluded_because.map(exclusionText).join("; ")}</span>
                <span className="text-xs text-ink-muted">{t("trust")} {c.trust_score ?? "—"}</span>
              </span>
            </li>
          ))}
          {excluded.length === 0 && <li className="py-2 text-ink-muted">{t("nobodyExcluded")}</li>}
        </ul>
      </section>
    </div>
  );
}
