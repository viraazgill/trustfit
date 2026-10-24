"use client";

import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { CoverageRing, GapCard, ReadinessRadar } from "@/components/bridge";
import { FitCategoryChip } from "@/components/fit";
import { PdfButton } from "@/components/pdf-button";
import { VerdictChip } from "@/components/trust";
import { useBridge, useBridgeConfig, useReadiness } from "@/lib/bridge-queries";
import { useExclusionText } from "@/lib/exclusions";
import { num, rhu } from "@/lib/format";
import { useLabel } from "@/lib/i18n";
import { useFitConfig } from "@/lib/sme-queries";
import type { Verdict } from "@/lib/trust-types";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="break-inside-avoid rounded-xl border bg-white p-4">
      <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink-muted">{title}</h2>
      {children}
    </section>
  );
}

/** One-page SME report: readiness, gaps, matches and the India entry team. The API prints this page. */
export default function SmeReport() {
  const { id } = useParams<{ id: string }>();
  const { data: readiness } = useReadiness(id);
  const { data: cfg } = useBridgeConfig();
  const { data: fitCfg } = useFitConfig();
  const bridge = useBridge(id, !!readiness?.answered);
  const t = useTranslations("bridge");
  const tr = useTranslations("readiness");
  const tc = useTranslations("common");
  const tt = useTranslations("trust");
  const tl = useLabel();
  const exclusionText = useExclusionText();

  if (readiness && !readiness.answered) return <p className="text-sm text-ink-muted">{tr("notAnswered")}</p>;
  if (bridge.error) return <p className="text-sm text-verdict-red">{bridge.error.message}</p>;
  const b = bridge.data;
  if (!b || !cfg || !fitCfg || !readiness) return <p className="text-sm text-ink-muted">{tc("loading")}</p>;
  const byId = Object.fromEntries(b.companies.map((c) => [c.company_id, c]));
  const excluded = b.companies.filter((c) => !c.eligible);

  return (
    <div data-print-ready className="space-y-4">
      <div className="flex justify-end print:hidden">
        <PdfButton path={`/smes/${id}/report.pdf`} filename={`trustfit-${id}.pdf`} />
      </div>
      <div className="grid gap-4 md:grid-cols-[1fr_1.4fr]">
        <Section title={tr("radarTitle")}>
          <ReadinessRadar dimensions={readiness.dimensions ?? {}} />
        </Section>
        <div className="grid gap-3 sm:grid-cols-2">
          {Object.entries(readiness.dimensions ?? {}).map(([k, d]) => (
            <GapCard key={k} id={k} d={d} />
          ))}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-[auto_1fr]">
        <Section title={t("teamCoverage")}>
          <CoverageRing value={b.team_coverage} target={cfg.target_team_coverage} />
        </Section>
        <Section title={t("yourTeam")}>
          <ul className="space-y-2 text-sm">
            {b.team.map((m) => {
              const c = byId[m.company_id];
              return (
                <li key={m.company_id} className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-navy">{c.name}</span>
                  <span className="rounded-full bg-navy px-2 py-0.5 text-[10px] text-white">
                    {m.slot === "primary" ? t("primary", { role: tt(`roles.${c.trust_role}`) }) : t("serviceProvider")}
                  </span>
                  <span className="font-mono text-xs">{c.trust_score}</span>
                  <VerdictChip verdict={c.trust_verdict as Verdict} size="sm" />
                  <span className="w-full text-xs text-ink-muted">
                    {m.covers.map((cv) => `${cv.gap} ${tl(`capabilities.${cv.capability}`, cv.label)}`).join(" · ")}
                  </span>
                </li>
              );
            })}
          </ul>
        </Section>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Section title={t("ranking")}>
          <ol className="space-y-1.5 text-sm">
            {b.primary_ranking.map((r, i) => {
              const c = byId[r.company_id];
              return (
                <li key={r.company_id} className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs text-ink-muted">{i + 1}</span>
                  <span className="font-medium text-navy">{c.name}</span>
                  <FitCategoryChip category={c.fit_category!} label={fitCfg.categories[c.fit_category!]?.label ?? ""} />
                  <span className="ml-auto font-mono text-xs">
                    {t("match")} {num(r.match, 2)} · {t("gapCoverage")} {rhu(r.gap_coverage, 1)}%
                  </span>
                </li>
              );
            })}
          </ol>
        </Section>
        <Section title={t("excluded")}>
          <ul className="space-y-1.5 text-sm">
            {excluded.map((c) => (
              <li key={c.company_id}>
                <span className="font-medium text-navy">{c.name}</span>
                <span className="block text-xs text-verdict-red">{c.excluded_because.map(exclusionText).join("; ")}</span>
              </li>
            ))}
            {excluded.length === 0 && <li className="text-ink-muted">{t("nobodyExcluded")}</li>}
          </ul>
        </Section>
      </div>
    </div>
  );
}
