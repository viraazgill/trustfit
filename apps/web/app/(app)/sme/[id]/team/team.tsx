"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { FictionalBadge } from "@/components/brand";
import { CoverageHeatmap, CoverageRing, SeverityChip } from "@/components/bridge";
import { VerdictChip } from "@/components/trust";
import { useBridge, useBridgeConfig, useReadiness } from "@/lib/bridge-queries";
import { rhu } from "@/lib/format";
import { useLabel } from "@/lib/i18n";
import type { Verdict } from "@/lib/trust-types";
import { cn } from "@/lib/utils";

const STATUS_STYLE: Record<string, string> = {
  covered: "text-verdict-green",
  "partly covered": "text-verdict-amber",
  "not covered": "text-verdict-red",
};

/** The India entry team: one primary partner plus up to three service providers, greedily chosen. */
export default function Team() {
  const { id } = useParams<{ id: string }>();
  const { data: readiness } = useReadiness(id);
  const bridge = useBridge(id, !!readiness?.answered);
  const { data: cfg } = useBridgeConfig();
  const t = useTranslations("bridge");
  const tt = useTranslations("trust");
  const tl = useLabel();
  if (readiness && !readiness.answered)
    return (
      <p className="text-sm text-ink-muted">
        {t.rich("answerFirstTeam", {
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
  if (!b || !cfg) return <p className="text-sm text-ink-muted">{t("building")}</p>;

  const byId = Object.fromEntries(b.companies.map((c) => [c.company_id, c]));
  const gaps = Object.entries(b.gap_status).map(([g, s]) => ({
    id: g,
    label: b.readiness[g].label,
    severity: b.readiness[g].severity_label,
    team: s.team_coverage,
    status: s.status,
  }));
  const weak = gaps.filter((g) => g.status !== "covered");

  return (
    <div className="space-y-6">
      <div className="grid gap-5 lg:grid-cols-[auto_1fr]">
        <section className="rounded-xl border bg-white p-5">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-ink-muted">{t("teamCoverage")}</h2>
          <CoverageRing value={b.team_coverage} target={cfg.target_team_coverage} />
        </section>
        <section className="rounded-xl border bg-white p-5" data-testid="gap-status">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-ink-muted">{t("gapsAfter")}</h2>
          <ul className="space-y-1.5 text-sm">
            {gaps.map((g) => (
              <li key={g.id} className="flex flex-wrap items-center gap-3">
                <span className="w-7 font-mono text-xs text-blue">{g.id}</span>
                <span className="flex-1">{tl(`readiness.${g.id}.label`, g.label)}</span>
                <SeverityChip label={g.severity} />
                <span className={cn("w-28 text-right text-xs font-medium", STATUS_STYLE[g.status])}>
                  {t(`status.${g.status}`)} ({rhu(100 * g.team)}%)
                </span>
              </li>
            ))}
          </ul>
          {weak.length > 0 && (
            <p className="mt-3 rounded-md bg-muted px-3 py-2 text-xs text-navy" data-testid="uncovered">
              {t("stillOpen", {
                gaps: weak
                  .map((g) => `${tl(`readiness.${g.id}.label`, g.label)} (${tl(`severity.${g.severity}`, g.severity)}, ${t(`status.${g.status}`)})`)
                  .join("; "),
              })}
            </p>
          )}
        </section>
      </div>

      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-ink-muted">{t("yourTeam")}</h2>
        <div className="grid gap-4 md:grid-cols-2">
          {b.team.map((m) => {
            const c = byId[m.company_id];
            return (
              <div key={m.company_id} className="rounded-xl border bg-white p-4" data-testid={`member-${m.company_id}`}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="inline-flex flex-wrap items-center gap-2">
                    <Link href={`/sme/${id}/company/${m.company_id}`} className="font-semibold text-blue hover:underline">
                      {c.name}
                    </Link>
                    {c.fictional && <FictionalBadge />}
                  </span>
                  <span className="rounded-full bg-navy px-2 py-0.5 text-xs text-white">
                    {m.slot === "primary" ? t("primary", { role: tt(`roles.${c.trust_role}`) }) : t("serviceProvider")}
                  </span>
                </div>
                <div className="mt-2 flex items-center gap-2 text-xs text-ink-muted">
                  {t("trust")} <span className="font-mono text-navy">{c.trust_score}</span>
                  <VerdictChip verdict={c.trust_verdict as Verdict} size="sm" />
                  {c.fit !== null && <span>· {t("fit")} {c.fit}</span>}· {t("adds", { points: rhu(m.gain, 1) })}
                </div>
                <ul className="mt-3 space-y-1 text-sm">
                  {m.covers.map((cv) => (
                    <li key={`${cv.gap}-${cv.capability}`} className="flex gap-2">
                      <span className="w-7 shrink-0 font-mono text-xs text-blue">{cv.gap}</span>
                      <span className="flex-1">{tl(`capabilities.${cv.capability}`, cv.label)}</span>
                      <span className="text-xs text-ink-muted">
                        {rhu(100 * cv.strength)}%{cv.verified ? "" : t("notYetVerified")}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
      </section>

      <section className="rounded-xl border bg-white p-5">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-ink-muted">{t("matrix")}</h2>
        <CoverageHeatmap
          gaps={gaps}
          members={b.team.map((m) => ({ id: m.company_id, name: byId[m.company_id].name, perGap: byId[m.company_id].per_gap }))}
        />
      </section>
    </div>
  );
}
