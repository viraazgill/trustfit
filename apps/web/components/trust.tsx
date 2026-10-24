"use client";

/** Shared Trust components, used by the analyst score panel and the SME-facing reports. */
import { useTranslations } from "next-intl";
import { useLabel } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import { num, pct, rhu } from "@/lib/format";
import type { Verdict } from "@/lib/trust-types";

const VERDICT_STYLE: Record<Verdict, string> = {
  Green: "bg-verdict-green text-white",
  Amber: "bg-verdict-amber text-white",
  Red: "bg-verdict-red text-white",
};

export function VerdictChip({ verdict, size = "md", className }: { verdict: Verdict; size?: "sm" | "md" | "lg"; className?: string }) {
  return (
    <span
      data-testid="verdict"
      className={cn(
        "inline-flex items-center rounded-full font-semibold tracking-wide",
        size === "sm" && "px-2 py-0.5 text-xs",
        size === "md" && "px-3 py-1 text-sm",
        size === "lg" && "px-4 py-1.5 text-base",
        VERDICT_STYLE[verdict],
        className,
      )}
    >
      {verdict}
    </span>
  );
}

export function ScoreCard({
  status,
  score,
  band,
  verdict,
  provisional,
  outlook,
}: {
  status: string;
  score: number | null;
  band: string | null;
  verdict: Verdict;
  provisional: boolean | null;
  outlook: string | null;
}) {
  const t = useTranslations("trust");
  const label = useLabel();
  const headline =
    status === "not_eligible" ? t("notEligible") : status === "insufficient_data" ? t("noScore") : null;
  return (
    <div className="flex flex-col gap-3 rounded-xl border bg-white p-6">
      <div className="text-xs font-medium uppercase tracking-wider text-ink-muted">{t("title")}</div>
      <div className="flex items-end gap-4">
        {headline ? (
          <span data-testid="score" className="text-4xl font-semibold text-navy">
            {headline}
          </span>
        ) : (
          <span data-testid="score" className="font-mono text-7xl font-semibold leading-none text-navy">
            {score}
          </span>
        )}
        {band && (
          <span data-testid="band" className="pb-1 text-lg font-medium text-blue">
            {label(`band.${band}`, band)}
          </span>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <VerdictChip verdict={verdict} size="lg" />
        {provisional && (
          <span className="rounded-full border border-verdict-amber/50 px-2 py-0.5 text-xs text-verdict-amber">
            {t("provisional")}
          </span>
        )}
        {outlook && (
          <span data-testid="outlook" className="text-sm text-ink-muted">
            {t("outlook")} <span className="font-medium text-navy">{label(`outlook.${outlook}`, outlook)}</span>
          </span>
        )}
      </div>
    </div>
  );
}

/** Verified points out of 100, with the no-score and provisional thresholds marked. */
export function ConfidenceMeter({
  value,
  noScoreBelow,
  provisionalBelow,
}: {
  value: number | null;
  noScoreBelow: number;
  provisionalBelow: number;
}) {
  const t = useTranslations("trust");
  const v = value ?? 0;
  const color = v < noScoreBelow ? "bg-verdict-red" : v < provisionalBelow ? "bg-verdict-amber" : "bg-verdict-green";
  return (
    <div className="rounded-xl border bg-white p-6">
      <div className="flex items-baseline justify-between">
        <span className="text-xs font-medium uppercase tracking-wider text-ink-muted">{t("confidence")}</span>
        <span data-testid="confidence" className="font-mono text-2xl font-semibold text-navy">
          {value === null ? "—" : rhu(v, 2)}
          <span className="text-sm text-ink-muted"> {t("perVerified")}</span>
        </span>
      </div>
      <div className="relative mt-4 h-3 rounded-full bg-muted">
        <div className={cn("h-3 rounded-full", color)} style={{ width: `${Math.min(100, v)}%` }} />
        {[noScoreBelow, provisionalBelow].map((m) => (
          <div key={m} className="absolute -top-1 h-5 w-px bg-navy/60" style={{ left: `${m}%` }}>
            <span className="absolute top-5 -translate-x-1/2 font-mono text-[10px] text-ink-muted">{m}</span>
          </div>
        ))}
      </div>
      <p className="mt-5 text-xs text-ink-muted">
        {t("confidenceHelp", { noScore: noScoreBelow, provisional: provisionalBelow })}
      </p>
    </div>
  );
}

export function DimensionCard({
  label,
  question,
  scorePct,
  verifiedPct,
  minVerified,
}: {
  label: string;
  question?: string;
  scorePct: number | null;
  verifiedPct: number | null;
  minVerified: number;
}) {
  const t = useTranslations("trust");
  const under = verifiedPct !== null && verifiedPct < minVerified;
  return (
    <div
      data-testid={`dimension-${label}`}
      className={cn("rounded-xl border bg-white p-4", under && "border-verdict-amber/60 bg-verdict-amber/5")}
    >
      <div className="text-sm font-medium text-navy">{label}</div>
      {question && <div className="text-xs text-ink-muted">{question}</div>}
      <div className="mt-2 font-mono text-3xl font-semibold text-navy">
        {scorePct === null ? "—" : rhu(scorePct, 1)}
      </div>
      <div className={cn("text-xs", under ? "font-medium text-verdict-amber" : "text-ink-muted")}>
        {t("verified", { pct: pct(verifiedPct, 2) })}
        {under && t("underMinimum", { min: minVerified })}
      </div>
    </div>
  );
}

export function CategoryBar({
  id,
  label,
  scorePct,
  verifiedPct,
  verifiedPoints,
  points,
  minVerified,
}: {
  id: string;
  label: string;
  scorePct: number | null;
  verifiedPct: number | null;
  verifiedPoints?: number;
  points: number;
  minVerified: number;
}) {
  const t = useTranslations("trust");
  const tc = useTranslations("common");
  const pale = verifiedPct === null || verifiedPct < minVerified;
  return (
    <div data-testid={`category-${id}`} className="grid grid-cols-[2rem_1fr_auto] items-center gap-3 py-1.5">
      <span className="font-mono text-sm font-semibold text-blue">{id}</span>
      <div>
        <div className="flex justify-between text-xs">
          <span className="text-navy">{label}</span>
          <span className="text-ink-muted">
            {verifiedPoints !== undefined
              ? t("ptsVerified", { verified: num(verifiedPoints), points: num(points) })
              : tc("pts", { points: num(points) })}
            {pale && t("underHalf")}
          </span>
        </div>
        <div className="mt-1 h-2.5 rounded-full bg-muted">
          <div
            className={cn("h-2.5 rounded-full bg-blue", pale && "opacity-35")}
            style={{ width: `${scorePct ?? 0}%` }}
          />
        </div>
      </div>
      <span className="w-12 text-right font-mono text-sm text-navy">{scorePct === null ? "—" : rhu(scorePct)}</span>
    </div>
  );
}

export function ReasonsList({ reasons }: { reasons: { code: string; text: string }[] }) {
  const t = useTranslations("trust");
  if (!reasons.length) return <p className="text-sm text-ink-muted">{t("noConditions")}</p>;
  return (
    <ul data-testid="reasons" className="space-y-1.5 text-sm">
      {reasons.map((r, i) => (
        <li key={i} className="flex gap-2">
          <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-coral" />
          <span>{r.text}</span>
        </li>
      ))}
    </ul>
  );
}
