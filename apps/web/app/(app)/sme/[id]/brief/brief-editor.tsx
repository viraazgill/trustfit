"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { type Brief, BriefFields, briefPayload } from "@/components/brief-fields";
import { humanize, placeName } from "@/lib/format";
import { type FitConfig, type Sme, useFitConfig, usePatchSme, useSme } from "@/lib/sme-queries";

function toBrief(sme: Sme, cfg: FitConfig): Brief {
  const defaults = cfg.role_default_importance[sme.role_sought];
  return {
    sector: sme.sector,
    products: sme.products,
    role_sought: sme.role_sought as Brief["role_sought"],
    primary: sme.target_states.primary ?? [],
    secondary: sme.target_states.secondary ?? [],
    channels_needed: sme.channels_needed,
    volume_units_per_month: sme.volume_units_per_month ?? 1,
    after_sales_need: (sme.after_sales_need ?? "none") as Brief["after_sales_need"],
    competitors: sme.competitors.join(", "),
    importance: { ...defaults, ...sme.factor_importance },
    edited: Object.keys(sme.factor_importance),
  };
}

function Editor({ sme, cfg }: { sme: Sme; cfg: FitConfig }) {
  const patch = usePatchSme(sme.id);
  const [brief, setBrief] = useState(() => toBrief(sme, cfg));
  return (
    <div className="space-y-4">
      <div className="rounded-xl border bg-white p-6">
        <BriefFields cfg={cfg} brief={brief} onChange={setBrief} />
      </div>
      <div className="flex items-center gap-3">
        <Button onClick={() => patch.mutate(briefPayload(brief, cfg))} disabled={patch.isPending || !brief.primary.length}>
          {patch.isPending ? "Saving…" : "Save brief"}
        </Button>
        {patch.isSuccess && <span className="text-sm text-verdict-green">Saved. Fit and matches use the new brief.</span>}
        {patch.isError && <span className="text-sm text-verdict-red">{patch.error.message}</span>}
      </div>
    </div>
  );
}

function Summary({ sme }: { sme: Sme }) {
  const rows: [string, string][] = [
    ["Sector", humanize(sme.sector)],
    ["Products", sme.products.map(humanize).join(", ") || "—"],
    ["Role sought", humanize(sme.role_sought)],
    ["Primary states", sme.target_states.primary?.map(placeName).join(", ") || "—"],
    ["Secondary states", sme.target_states.secondary?.map(placeName).join(", ") || "—"],
    ["Channels", sme.channels_needed.map(humanize).join(", ") || "—"],
    ["Volume", `${sme.volume_units_per_month ?? "—"} units per month`],
    ["After-sales need", humanize(sme.after_sales_need ?? "none")],
    ["Competitors", sme.competitors.join(", ") || "—"],
  ];
  return (
    <div className="space-y-3">
      <p className="text-sm text-ink-muted">This is a demo brief: you can read it, but only its owner or an analyst can change it.</p>
      <dl className="grid grid-cols-[10rem_1fr] gap-x-4 gap-y-2 rounded-xl border bg-white p-6 text-sm">
        {rows.map(([k, v]) => (
          <div key={k} className="contents">
            <dt className="text-ink-muted">{k}</dt>
            <dd className="text-navy">{v}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

export default function BriefPage() {
  const { id } = useParams<{ id: string }>();
  const { data: sme } = useSme(id);
  const { data: cfg } = useFitConfig();
  if (!sme || !cfg) return <p className="text-sm text-ink-muted">Loading…</p>;
  return sme.mine ? <Editor sme={sme} cfg={cfg} /> : <Summary sme={sme} />;
}
