"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { VerdictChip } from "@/components/trust";
import { num, todayIso } from "@/lib/format";
import { defaultRole } from "@/lib/roles";
import {
  type EvidenceRow,
  useCompany,
  useEvidence,
  usePublicConfig,
  usePutEvidence,
  useRubrics,
  useTrustScore,
} from "@/lib/queries";
import { cn } from "@/lib/utils";

const SAVE_DEBOUNCE_MS = 300;

const STATUS_STYLE: Record<string, string> = {
  verified: "border-verdict-green/40 text-verdict-green",
  stale: "border-verdict-amber/60 bg-verdict-amber/10 text-verdict-amber",
  unverified: "border-ink-muted/40 text-ink-muted",
  missing: "border-verdict-red/40 bg-verdict-red/5 text-verdict-red",
};

interface Draft {
  level: number | null;
  verified: boolean;
  source_url: string;
  source_date: string;
  checked_at: string;
  note: string;
}

const toDraft = (r: EvidenceRow): Draft => ({
  level: r.level ?? null,
  verified: r.verified ?? false,
  source_url: r.source_url ?? "",
  source_date: r.source_date ?? "",
  checked_at: r.checked_at ?? "",
  note: r.note ?? "",
});

function EvidenceEditor({ companyId, row, levels }: { companyId: string; row: EvidenceRow; levels: number[] }) {
  const { data: rubrics } = useRubrics();
  const spec = rubrics?.parameters[row.parameter_id];
  const put = usePutEvidence(companyId);
  const [draft, setDraft] = useState<Draft>(() => toDraft(row));
  const [touched, setTouched] = useState(false);

  const problem =
    draft.level === null
      ? "Pick a level to save"
      : draft.verified && !draft.source_url
        ? "A verified value needs a source URL"
        : draft.verified && !draft.source_date
          ? "A verified value needs the source date"
          : null;

  useEffect(() => {
    if (!touched || problem) return;
    const t = setTimeout(() => {
      put.mutate({
        pid: row.parameter_id,
        body: {
          level: draft.level!,
          verified: draft.verified,
          source_url: draft.source_url || null,
          source_date: draft.source_date || null,
          checked_at: draft.checked_at || null,
          note: draft.note || null,
        },
      });
    }, SAVE_DEBOUNCE_MS);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- save only when the draft changes
  }, [draft, problem, touched]);

  const edit = (patch: Partial<Draft>) => {
    setTouched(true);
    setDraft((d) => ({ ...d, ...patch }));
  };

  return (
    <div data-testid={`evidence-${row.parameter_id}`} className="border-t py-4 first:border-t-0">
      <div className="flex flex-wrap items-start gap-3">
        <span className="w-8 font-mono text-sm font-semibold text-blue">{row.parameter_id}</span>
        <div className="min-w-48 flex-1">
          <div className="text-sm font-medium text-navy">{row.name}</div>
          <div className="text-xs text-ink-muted">
            Tier {spec?.tier}
            {spec?.recheck_days ? ` · recheck every ${spec.recheck_days} days` : ""}
            {spec?.knockout_at_zero ? " · 0% is a knock-out" : ""}
            {spec?.where_to_check && ` · check: ${spec.where_to_check}`}
          </div>
        </div>
        <span className={cn("rounded-full border px-2 py-0.5 text-xs", STATUS_STYLE[row.status])}>{row.status}</span>
        <span className="w-16 text-right text-xs text-ink-muted">
          {put.isPending ? "saving…" : put.isError ? "not saved" : ""}
        </span>
      </div>

      <div className="mt-3 grid gap-3 pl-11 lg:grid-cols-[auto_1fr]">
        <div>
          <div className="inline-flex overflow-hidden rounded-md border" role="radiogroup" aria-label={`${row.parameter_id} level`}>
            {levels.map((lvl) => (
              <button
                key={lvl}
                type="button"
                role="radio"
                aria-checked={draft.level === lvl}
                title={spec?.rubric[String(lvl)]}
                onClick={() => edit({ level: lvl })}
                className={cn(
                  "border-l px-3 py-1.5 font-mono text-xs first:border-l-0",
                  draft.level === lvl ? "bg-navy text-white" : "bg-white hover:bg-muted",
                )}
              >
                {lvl}
              </button>
            ))}
          </div>
          <p className="mt-1.5 max-w-sm text-xs text-ink-muted">
            {draft.level === null ? "No level yet." : spec?.rubric[String(draft.level)]}
          </p>
        </div>
        <div className="grid gap-2 sm:grid-cols-[auto_1fr_auto_auto]">
          <label className="flex items-center gap-2 text-sm">
            <Switch checked={draft.verified} onCheckedChange={(v) => edit({ verified: v })} />
            Verified
          </label>
          <Input
            placeholder="Source URL (primary filing)"
            value={draft.source_url}
            onChange={(e) => edit({ source_url: e.target.value })}
            className="h-8 text-xs"
          />
          <label className="flex items-center gap-1 text-xs text-ink-muted">
            Source
            <Input type="date" value={draft.source_date} onChange={(e) => edit({ source_date: e.target.value })} className="h-8 w-36 text-xs" />
          </label>
          <label className="flex items-center gap-1 text-xs text-ink-muted">
            Checked
            <Input type="date" value={draft.checked_at} onChange={(e) => edit({ checked_at: e.target.value })} className="h-8 w-36 text-xs" />
            <button type="button" className="text-blue hover:underline" onClick={() => edit({ checked_at: todayIso() })}>
              today
            </button>
          </label>
          <Input
            placeholder="Analyst note (never shown to SMEs)"
            value={draft.note}
            onChange={(e) => edit({ note: e.target.value })}
            className="h-8 text-xs sm:col-span-4"
          />
          {problem && touched && <p className="text-xs text-verdict-amber sm:col-span-4">{problem}</p>}
          {put.isError && <p className="text-xs text-verdict-red sm:col-span-4">{put.error.message}</p>}
        </div>
      </div>
    </div>
  );
}

function LiveScore({ id }: { id: string }) {
  const { data: cfg } = usePublicConfig();
  const { data: company } = useCompany(id);
  const role = defaultRole(company, cfg);
  const { data, isFetching } = useTrustScore(id, role);
  const r = data?.result;
  return (
    <div className="sticky top-0 z-10 flex flex-wrap items-center gap-4 rounded-xl border bg-white/95 px-4 py-3 backdrop-blur">
      <span className="text-xs uppercase tracking-wider text-ink-muted">Live score · {cfg?.roles[role]?.label}</span>
      {r && (
        <>
          <span className="font-mono text-2xl font-semibold text-navy">{r.score ?? (r.eligible ? "No score" : "Not eligible")}</span>
          <VerdictChip verdict={r.verdict} size="sm" />
          <span className="text-sm text-ink-muted">{num(r.confidence)} / 100 verified</span>
        </>
      )}
      {isFetching && <span className="text-xs text-ink-muted">re-scoring…</span>}
      <Link href={`/companies/${id}`} className="ml-auto text-sm text-blue hover:underline">
        Open score panel →
      </Link>
    </div>
  );
}

export default function EvidencePage() {
  const { id } = useParams<{ id: string }>();
  const { data: cfg } = usePublicConfig();
  const { data: rows, error } = useEvidence(id);
  if (error) return <p className="text-sm text-verdict-red">{error.message}</p>;
  if (!cfg || !rows) return <p className="text-sm text-ink-muted">Loading…</p>;

  return (
    <div className="space-y-4">
      <LiveScore id={id} />
      <Accordion multiple defaultValue={Object.keys(cfg.categories)} className="rounded-xl border bg-white px-4">
        {Object.entries(cfg.categories).map(([cat, c]) => {
          const catRows = rows.filter((r) => r.category === cat);
          const verified = catRows.filter((r) => r.status === "verified").length;
          return (
            <AccordionItem key={cat} value={cat}>
              <AccordionTrigger>
                <span className="flex items-center gap-3">
                  <span className="font-mono text-blue">{cat}</span>
                  <span className="text-navy">{c.label}</span>
                  <span className="text-xs font-normal text-ink-muted">
                    {verified}/{catRows.length} verified · {cfg.dimensions[c.dimension]?.label}
                  </span>
                </span>
              </AccordionTrigger>
              <AccordionContent>
                {catRows.map((r) => (
                  <EvidenceEditor key={r.parameter_id} companyId={id} row={r} levels={cfg.scale_levels} />
                ))}
              </AccordionContent>
            </AccordionItem>
          );
        })}
      </Accordion>
    </div>
  );
}
