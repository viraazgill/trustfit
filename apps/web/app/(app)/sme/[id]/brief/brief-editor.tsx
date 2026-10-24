"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { type Brief, BriefFields, briefPayload } from "@/components/brief-fields";
import { humanize, placeName } from "@/lib/format";
import { useLabel } from "@/lib/i18n";
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
  const t = useTranslations("brief");
  const patch = usePatchSme(sme.id);
  const [brief, setBrief] = useState(() => toBrief(sme, cfg));
  return (
    <div className="space-y-4">
      <div className="rounded-xl border bg-white p-6">
        <BriefFields cfg={cfg} brief={brief} onChange={setBrief} />
      </div>
      <div className="flex items-center gap-3">
        <Button onClick={() => patch.mutate(briefPayload(brief, cfg))} disabled={patch.isPending || !brief.primary.length}>
          {patch.isPending ? t("saving") : t("save")}
        </Button>
        {patch.isSuccess && <span className="text-sm text-verdict-green">{t("saved")}</span>}
        {patch.isError && <span className="text-sm text-verdict-red">{patch.error.message}</span>}
      </div>
    </div>
  );
}

function Summary({ sme }: { sme: Sme }) {
  const t = useTranslations("brief");
  const tl = useLabel();
  const need = sme.after_sales_need ?? "none";
  const rows: [string, string][] = [
    [t("row.sector"), tl(`sectors.${sme.sector}`, humanize(sme.sector))],
    [t("row.products"), sme.products.map(humanize).join(", ") || "—"],
    [t("row.role"), t(`roleOption.${sme.role_sought}`)],
    [t("row.primary"), sme.target_states.primary?.map(placeName).join(", ") || "—"],
    [t("row.secondary"), sme.target_states.secondary?.map(placeName).join(", ") || "—"],
    [t("row.channels"), sme.channels_needed.map((c) => tl(`channels.${c}`, humanize(c))).join(", ") || "—"],
    [t("row.volume"), t("unitsPerMonth", { n: sme.volume_units_per_month ?? "—" })],
    [t("row.afterSales"), tl(`afterSales.${need}`, humanize(need))],
    [t("row.competitors"), sme.competitors.join(", ") || "—"],
  ];
  return (
    <div className="space-y-3">
      <p className="text-sm text-ink-muted">{t("readOnly")}</p>
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
