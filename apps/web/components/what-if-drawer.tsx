"use client";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { VerdictChip } from "@/components/trust";
import { num } from "@/lib/format";
import { usePublicConfig, useRubrics } from "@/lib/queries";
import type { TrustResult, WhatIf } from "@/lib/trust-types";

const FULL_LEVEL = 100;
const EMPTY: WhatIf = { evidence: {}, gates: {} };

function Summary({ label, r }: { label: string; r?: TrustResult }) {
  return (
    <div className="flex-1 rounded-lg border p-3">
      <div className="text-xs text-ink-muted">{label}</div>
      {r ? (
        <div className="mt-1 flex items-center gap-2">
          <span className="font-mono text-2xl font-semibold text-navy">{r.score ?? "—"}</span>
          <VerdictChip verdict={r.verdict} size="sm" />
          <span className="text-xs text-ink-muted">{num(r.confidence)} verified</span>
        </div>
      ) : (
        <div className="mt-1 text-sm text-ink-muted">—</div>
      )}
    </div>
  );
}

/** Tick parameters to treat as verified at 100% and gates to treat as passed. Preview only: what-if
 * runs are flagged in the database and never overwrite real evidence. */
export function WhatIfDrawer({
  base,
  preview,
  whatIf,
  onChange,
}: {
  base: TrustResult;
  preview?: TrustResult;
  whatIf: WhatIf | null;
  onChange: (w: WhatIf | null) => void;
}) {
  const { data: cfg } = usePublicConfig();
  const { data: rubrics } = useRubrics();
  const current = whatIf ?? EMPTY;
  const open = Object.entries(base.parameters ?? {}).filter(([, p]) => p.status !== "verified");
  const gates = Object.keys(cfg?.gates ?? {}).filter((g) => (base.gates?.[g] ?? "pending") !== "passed");

  const integrityCats = new Set(cfg?.dimensions.integrity?.categories ?? []);
  const integrityOpen = open.filter(([pid]) => integrityCats.has(rubrics?.parameters[pid]?.category ?? ""));

  function update(next: WhatIf) {
    const empty = !Object.keys(next.evidence).length && !Object.keys(next.gates).length;
    onChange(empty ? null : next);
  }
  function toggleParam(pid: string, on: boolean) {
    const evidence = { ...current.evidence };
    if (on) evidence[pid] = FULL_LEVEL;
    else delete evidence[pid];
    update({ ...current, evidence });
  }
  function toggleGate(g: string, on: boolean) {
    const next = { ...current.gates };
    if (on) next[g] = "passed";
    else delete next[g];
    update({ ...current, gates: next });
  }
  function integrityClean() {
    update({
      evidence: Object.fromEntries(integrityOpen.map(([pid]) => [pid, FULL_LEVEL])),
      gates: Object.fromEntries(gates.map((g) => [g, "passed" as const])),
    });
  }

  return (
    <Sheet>
      <SheetTrigger render={<Button className="bg-coral text-white hover:bg-coral/90" />}>What-if</SheetTrigger>
      <SheetContent className="w-full overflow-y-auto sm:max-w-md">
        <SheetHeader>
          <SheetTitle>What-if preview</SheetTitle>
          <SheetDescription>
            Treat checks as clean and see the verdict before saving anything. Real evidence is never changed.
          </SheetDescription>
        </SheetHeader>
        <div className="space-y-5 px-4 pb-6">
          <div className="flex gap-2">
            <Summary label="Now" r={base} />
            <Summary label="What-if" r={whatIf ? preview : undefined} />
          </div>
          <div className="flex flex-wrap gap-2">
            <Button onClick={integrityClean} disabled={!integrityOpen.length && !gates.length}>
              Integrity checks clean
            </Button>
            <Button variant="outline" onClick={() => onChange(null)} disabled={!whatIf}>
              Clear
            </Button>
          </div>
          {integrityOpen.length > 0 && (
            <p className="text-xs text-ink-muted">
              Preset: {integrityOpen.map(([pid]) => pid).join(", ")} at 100% and every pending gate passed.
            </p>
          )}

          <div>
            <h3 className="mb-2 text-sm font-semibold text-navy">Verification gates</h3>
            {gates.length === 0 && <p className="text-xs text-ink-muted">All gates passed.</p>}
            {gates.map((g) => (
              <label key={g} className="flex items-center gap-2 py-1 text-sm">
                <Checkbox checked={current.gates[g] === "passed"} onCheckedChange={(on) => toggleGate(g, on)} />
                <span className="font-mono text-xs text-blue">{g}</span>
                {cfg?.gates[g]?.label}
                <span className="ml-auto text-xs text-ink-muted">{base.gates?.[g] ?? "pending"}</span>
              </label>
            ))}
          </div>

          <div>
            <h3 className="mb-2 text-sm font-semibold text-navy">Parameters to set to 100%</h3>
            {open.length === 0 && <p className="text-xs text-ink-muted">Every parameter is verified.</p>}
            {open.map(([pid, p]) => (
              <label key={pid} className="flex items-center gap-2 py-1 text-sm">
                <Checkbox checked={pid in current.evidence} onCheckedChange={(on) => toggleParam(pid, on)} />
                <span className="w-7 font-mono text-xs text-blue">{pid}</span>
                <span className="flex-1">{rubrics?.parameters[pid]?.name}</span>
                <span className="text-xs text-ink-muted">
                  {num(p.points)} pts · {p.status}
                </span>
              </label>
            ))}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
