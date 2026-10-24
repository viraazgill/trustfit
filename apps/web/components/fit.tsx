"use client";

/** Fit card: how well one Indian company matches this SME's brief, and the combined verdict. */
import { useTranslations } from "next-intl";
import { VerdictChip } from "@/components/trust";
import { humanize, num } from "@/lib/format";
import { useLabel } from "@/lib/i18n";
import type { FitResult } from "@/lib/sme-queries";
import type { Verdict } from "@/lib/trust-types";
import { cn } from "@/lib/utils";

const CATEGORY_STYLE: Record<string, string> = {
  strong_fit: "bg-verdict-green/10 text-verdict-green border-verdict-green/40",
  possible_fit: "bg-verdict-amber/10 text-verdict-amber border-verdict-amber/40",
  not_a_fit: "bg-verdict-red/10 text-verdict-red border-verdict-red/40",
};

export function FitCategoryChip({ category, label }: { category: string; label: string }) {
  const tl = useLabel();
  return (
    <span data-testid="fit-category" className={cn("inline-flex rounded-full border px-2.5 py-0.5 text-sm font-medium", CATEGORY_STYLE[category])}>
      {tl(`fitCategory.${category}`, label)}
    </span>
  );
}

/** "represents Flowtek (Demo)" for a relation code and brand, in the current language. */
export function useRelationText() {
  const t = useTranslations("fit");
  return (relation: string, brand: string) => {
    const key = `relation.${relation}`;
    return t.has(key) ? t(key, { brand }) : `${humanize(relation)} ${brand}`;
  };
}

export function FitCard({ fit }: { fit: FitResult }) {
  const t = useTranslations("fit");
  const tc = useTranslations("common");
  const label = useLabel();
  const relationText = useRelationText();
  const conflict = fit.conflict && { detail: relationText(fit.conflict.relation, fit.conflict.brand), brand: fit.conflict.brand };
  const trustScore = fit.trust.score ?? (fit.trust.eligible ? t("trustNoScore") : t("trustNotEligible"));
  return (
    <section className="rounded-xl border bg-white p-5" data-testid="fit-card">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-medium uppercase tracking-wider text-ink-muted">{t("title")}</div>
          <div className="mt-1 flex items-end gap-3">
            <span data-testid="fit-score" className="font-mono text-5xl font-semibold leading-none text-navy">
              {fit.score ?? "—"}
            </span>
            <FitCategoryChip category={fit.category} label={fit.category_label} />
          </div>
          <p className="mt-2 text-sm text-ink-muted">
            {t("action")} <span className="font-medium text-navy">{label(`fitAction.${fit.category}`, fit.action)}</span> ·{" "}
            {t("fitConfidence", { pct: num(fit.confidence, 1) })}
          </p>
        </div>
        <div className="rounded-lg border p-3 text-sm">
          <div className="text-xs text-ink-muted">{t("combined")}</div>
          <div className="mt-1 flex items-center gap-2">
            <VerdictChip verdict={fit.combined_verdict as Verdict} />
            <span className="text-xs text-ink-muted">{t("trustSummary", { score: trustScore, verdict: fit.trust.verdict })}</span>
          </div>
          <div className="mt-1 text-xs text-ink-muted">{t("neverRaises")}</div>
        </div>
      </div>

      {conflict && (
        <div data-testid="fit-conflict" className="mt-4 rounded-lg border border-verdict-red/40 bg-verdict-red/5 px-3 py-2 text-sm text-verdict-red">
          {t("conflict", conflict)}
        </div>
      )}

      <table className="mt-4 w-full text-sm">
        <thead>
          <tr className="border-b text-left text-xs text-ink-muted">
            <th className="py-1.5 font-normal">{t("factor")}</th>
            <th className="py-1.5 font-normal">{t("importance")}</th>
            <th className="py-1.5 text-right font-normal">{t("weight")}</th>
            <th className="py-1.5 text-right font-normal">{t("level")}</th>
            <th className="py-1.5 text-right font-normal">{t("verified")}</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(fit.factors).map(([id, f]) => {
            const gap = fit.gaps.includes(id);
            return (
              <tr key={id} className={cn("border-b last:border-0", f.weight === 0 && "text-ink-muted")} data-testid={`fit-${id}`}>
                <td className="py-1.5">
                  <span className="mr-2 font-mono text-xs text-blue">{id}</span>
                  {label(`fitFactors.${id}`, f.label)}
                  {gap && f.weight > 0 && <span className="ml-2 text-xs text-verdict-amber">{t("gap")}</span>}
                </td>
                <td className="py-1.5">{label(`importance.${f.importance}`, humanize(f.importance))}</td>
                <td className="py-1.5 text-right font-mono">{num(f.weight, 1)}</td>
                <td className="py-1.5 text-right font-mono">{f.level ?? t("unknown")}</td>
                <td className="py-1.5 text-right">{f.level === null ? "—" : f.verified ? tc("yes") : tc("no")}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
