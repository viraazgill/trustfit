"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { GapCard, ReadinessRadar } from "@/components/bridge";
import { ReadinessForm } from "@/components/readiness-form";
import { useBridgeConfig, usePutReadiness, useReadiness } from "@/lib/bridge-queries";
import { useSme } from "@/lib/sme-queries";

function Questionnaire({ smeId, initial, onDone }: { smeId: string; initial: Record<string, number>; onDone?: () => void }) {
  const { data: cfg } = useBridgeConfig();
  const put = usePutReadiness(smeId);
  const [answers, setAnswers] = useState(initial);
  if (!cfg) return null;
  const total = Object.values(cfg.dimensions).reduce((n, d) => n + Object.keys(d.questions).length, 0);
  return (
    <div className="space-y-4">
      <ReadinessForm cfg={cfg} answers={answers} onChange={setAnswers} />
      <div className="flex items-center gap-3">
        <Button onClick={() => put.mutate(answers, { onSuccess: onDone })} disabled={Object.keys(answers).length < total || put.isPending}>
          {put.isPending ? "Saving…" : "Save answers"}
        </Button>
        {onDone && (
          <Button variant="outline" onClick={onDone}>
            Cancel
          </Button>
        )}
        {put.isError && <span className="text-sm text-verdict-red">{put.error.message}</span>}
      </div>
    </div>
  );
}

/** India Entry Readiness: a radar over JETRO's six asks and one card per gap. */
export default function Readiness() {
  const { id } = useParams<{ id: string }>();
  const { data: sme } = useSme(id);
  const { data: readiness } = useReadiness(id);
  const [editing, setEditing] = useState(false);
  if (!sme || !readiness) return <p className="text-sm text-ink-muted">Loading…</p>;

  if (!readiness.answered || editing) {
    if (!sme.mine) return <p className="text-sm text-ink-muted">This SME hasn&apos;t answered the readiness check yet.</p>;
    return (
      <div className="space-y-3">
        <h2 className="text-lg font-semibold text-navy">India Entry Readiness check</h2>
        <p className="text-sm text-ink-muted">16 questions on JETRO&apos;s six asks. Your weak areas become gaps that TrustFit fills with trusted Indian partners.</p>
        <Questionnaire smeId={id} initial={readiness.answers ?? {}} onDone={editing ? () => setEditing(false) : undefined} />
      </div>
    );
  }

  const dims = readiness.dimensions ?? {};
  return (
    <div className="space-y-5">
      <div className="grid gap-5 lg:grid-cols-[1.1fr_1fr]">
        <section className="rounded-xl border bg-white p-5">
          <div className="flex items-baseline justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-ink-muted">Readiness by JETRO ask (0-100)</h2>
            {sme.mine && (
              <button className="text-xs text-blue hover:underline" onClick={() => setEditing(true)}>
                Edit answers
              </button>
            )}
          </div>
          <ReadinessRadar dimensions={dims} />
        </section>
        <section className="space-y-3">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-ink-muted">Your gaps</h2>
          <p className="text-sm text-ink-muted">
            Severity = how far from ready, weighted by how much it matters for a {sme.role_sought.replace("_", " ")}.{" "}
            <Link href={`/sme/${id}/matches`} className="text-blue hover:underline">
              See who in India can fill them →
            </Link>
          </p>
        </section>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Object.entries(dims).map(([k, d]) => (
          <GapCard key={k} id={k} d={d} />
        ))}
      </div>
    </div>
  );
}
