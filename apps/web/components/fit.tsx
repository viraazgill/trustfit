/** Fit card: how well one Indian company matches this SME's brief, and the combined verdict. */
import { VerdictChip } from "@/components/trust";
import { humanize, num } from "@/lib/format";
import type { FitResult } from "@/lib/sme-queries";
import type { Verdict } from "@/lib/trust-types";
import { cn } from "@/lib/utils";

const CATEGORY_STYLE: Record<string, string> = {
  strong_fit: "bg-verdict-green/10 text-verdict-green border-verdict-green/40",
  possible_fit: "bg-verdict-amber/10 text-verdict-amber border-verdict-amber/40",
  not_a_fit: "bg-verdict-red/10 text-verdict-red border-verdict-red/40",
};

const RELATION_TEXT: Record<string, string> = {
  owner: "is owned by",
  shareholder_10: "has a 10%+ shareholder in",
  exclusive: "has an exclusive deal with",
  represents: "represents",
  supplies: "supplies",
};

export function FitCategoryChip({ category, label }: { category: string; label: string }) {
  return (
    <span data-testid="fit-category" className={cn("inline-flex rounded-full border px-2.5 py-0.5 text-sm font-medium", CATEGORY_STYLE[category])}>
      {label}
    </span>
  );
}

export function conflictText(fit: Pick<FitResult, "conflict">): string | null {
  if (!fit.conflict) return null;
  return `${RELATION_TEXT[fit.conflict.relation] ?? humanize(fit.conflict.relation)} ${fit.conflict.brand}`;
}

export function FitCard({ fit }: { fit: FitResult }) {
  const conflict = conflictText(fit);
  return (
    <section className="rounded-xl border bg-white p-5" data-testid="fit-card">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-medium uppercase tracking-wider text-ink-muted">Fit Score for your brief</div>
          <div className="mt-1 flex items-end gap-3">
            <span data-testid="fit-score" className="font-mono text-5xl font-semibold leading-none text-navy">
              {fit.score ?? "—"}
            </span>
            <FitCategoryChip category={fit.category} label={fit.category_label} />
          </div>
          <p className="mt-2 text-sm text-ink-muted">
            Action: <span className="font-medium text-navy">{fit.action}</span> · fit confidence {num(fit.confidence, 1)}%
          </p>
        </div>
        <div className="rounded-lg border p-3 text-sm">
          <div className="text-xs text-ink-muted">Combined verdict</div>
          <div className="mt-1 flex items-center gap-2">
            <VerdictChip verdict={fit.combined_verdict as Verdict} />
            <span className="text-xs text-ink-muted">
              Trust {fit.trust.score ?? (fit.trust.eligible ? "no score" : "not eligible")} ({fit.trust.verdict})
            </span>
          </div>
          <div className="mt-1 text-xs text-ink-muted">Fit can lower a verdict, never raise it.</div>
        </div>
      </div>

      {conflict && (
        <div data-testid="fit-conflict" className="mt-4 rounded-lg border border-verdict-red/40 bg-verdict-red/5 px-3 py-2 text-sm text-verdict-red">
          Competitor conflict: this company {conflict}, a brand you compete with.
        </div>
      )}

      <table className="mt-4 w-full text-sm">
        <thead>
          <tr className="border-b text-left text-xs text-ink-muted">
            <th className="py-1.5 font-normal">Factor</th>
            <th className="py-1.5 font-normal">Importance</th>
            <th className="py-1.5 text-right font-normal">Weight</th>
            <th className="py-1.5 text-right font-normal">Level</th>
            <th className="py-1.5 text-right font-normal">Verified</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(fit.factors).map(([id, f]) => {
            const gap = fit.gaps.includes(id);
            return (
              <tr key={id} className={cn("border-b last:border-0", f.weight === 0 && "text-ink-muted")} data-testid={`fit-${id}`}>
                <td className="py-1.5">
                  <span className="mr-2 font-mono text-xs text-blue">{id}</span>
                  {f.label}
                  {gap && f.weight > 0 && <span className="ml-2 text-xs text-verdict-amber">gap</span>}
                </td>
                <td className="py-1.5">{humanize(f.importance)}</td>
                <td className="py-1.5 text-right font-mono">{num(f.weight, 1)}</td>
                <td className="py-1.5 text-right font-mono">{f.level ?? "unknown"}</td>
                <td className="py-1.5 text-right">{f.level === null ? "—" : f.verified ? "yes" : "no"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
