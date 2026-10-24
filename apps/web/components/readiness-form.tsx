"use client";

/** The 16-question India Entry Readiness check, grouped by JETRO's six asks, with a progress bar. */
import type { BridgeConfig } from "@/lib/bridge-queries";
import { cn } from "@/lib/utils";

export function ReadinessForm({
  cfg,
  answers,
  onChange,
}: {
  cfg: BridgeConfig;
  answers: Record<string, number>;
  onChange: (a: Record<string, number>) => void;
}) {
  const scale = Object.entries(cfg.answer_scale).map(([k, label]) => ({ value: Number(k), label }));
  const total = Object.values(cfg.dimensions).reduce((n, d) => n + Object.keys(d.questions).length, 0);
  const done = Object.keys(answers).length;
  return (
    <div className="space-y-6">
      <div>
        <div className="flex justify-between text-xs text-ink-muted">
          <span>
            {done} of {total} answered
          </span>
          <span>0 = not started · 4 = done and validated</span>
        </div>
        <div className="mt-1 h-2 rounded-full bg-muted" role="progressbar" aria-valuenow={done} aria-valuemax={total}>
          <div className="h-2 rounded-full bg-blue transition-all" style={{ width: `${(100 * done) / total}%` }} />
        </div>
      </div>
      {Object.entries(cfg.dimensions).map(([dim, d]) => (
        <fieldset key={dim} className="space-y-3">
          <legend className="text-sm font-semibold text-navy">
            <span className="mr-2 font-mono text-blue">{dim}</span>
            {d.label}
          </legend>
          <p className="-mt-2 text-xs text-ink-muted">JETRO ask: {d.jetro_ask}</p>
          {Object.entries(d.questions).map(([q, text]) => (
            <div key={q} className="rounded-lg border bg-white p-3" data-testid={`question-${q}`}>
              <p className="text-sm text-navy">
                <span className="mr-2 font-mono text-xs text-ink-muted">{q}</span>
                {text}
              </p>
              <div className="mt-2 flex flex-wrap gap-1.5" role="radiogroup" aria-label={q}>
                {scale.map((s) => (
                  <button
                    key={s.value}
                    type="button"
                    role="radio"
                    aria-checked={answers[q] === s.value}
                    onClick={() => onChange({ ...answers, [q]: s.value })}
                    className={cn(
                      "rounded-md border px-2.5 py-1 text-xs",
                      answers[q] === s.value ? "border-navy bg-navy text-white" : "bg-white hover:bg-muted",
                    )}
                  >
                    <span className="mr-1 font-mono">{s.value}</span>
                    {s.label}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </fieldset>
      ))}
    </div>
  );
}
