"use client";

/** Inputs for an SME brief, shared by the new-SME wizard and the brief editor. */
import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { humanize } from "@/lib/format";
import type { FitConfig } from "@/lib/sme-queries";
import { cn } from "@/lib/utils";

export interface Brief {
  sector: string;
  products: string[];
  role_sought: "supplier" | "distributor" | "jv_partner";
  primary: string[];
  secondary: string[];
  channels_needed: string[];
  volume_units_per_month: number;
  after_sales_need: "none" | "basic" | "full";
  competitors: string;
  importance: Record<string, string>;
  edited: string[]; // factors whose importance the SME changed from the role default
}

export const ROLE_OPTIONS = [
  { value: "distributor", label: "Distributor" },
  { value: "supplier", label: "Supplier" },
  { value: "jv_partner", label: "JV partner" },
] as const;

export function emptyBrief(cfg: FitConfig): Brief {
  return {
    sector: cfg.sectors[0],
    products: [],
    role_sought: "distributor",
    primary: [],
    secondary: [],
    channels_needed: [],
    volume_units_per_month: 100,
    after_sales_need: "basic",
    competitors: "",
    importance: { ...cfg.role_default_importance.distributor },
    edited: [],
  };
}

/** The brief as the API expects it; factor_importance carries only the SME's changes. */
export function briefPayload(b: Brief, cfg: FitConfig) {
  const defaults = cfg.role_default_importance[b.role_sought];
  return {
    sector: b.sector,
    products: b.products,
    role_sought: b.role_sought,
    target_states: { primary: b.primary, secondary: b.secondary },
    channels_needed: b.channels_needed,
    volume_units_per_month: b.volume_units_per_month,
    after_sales_need: b.after_sales_need,
    competitors: b.competitors.split(",").map((s) => s.trim()).filter(Boolean),
    factor_importance: Object.fromEntries(
      Object.entries(b.importance).filter(([f, imp]) => imp !== defaults[f]),
    ) as Record<string, "must" | "important" | "nice" | "irrelevant">,
  };
}

export function Chip({ on, onClick, children, tone = "navy" }: { on: boolean; onClick: () => void; children: React.ReactNode; tone?: "navy" | "blue" }) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={onClick}
      className={cn(
        "rounded-full border px-3 py-1 text-xs",
        on ? (tone === "navy" ? "border-navy bg-navy text-white" : "border-blue bg-blue/15 text-blue") : "bg-white hover:bg-muted",
      )}
    >
      {children}
    </button>
  );
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      {hint && <p className="text-xs text-ink-muted">{hint}</p>}
      {children}
    </div>
  );
}

export function BriefFields({ cfg, brief, onChange }: { cfg: FitConfig; brief: Brief; onChange: (b: Brief) => void }) {
  const [custom, setCustom] = useState("");
  const set = (patch: Partial<Brief>) => onChange({ ...brief, ...patch });
  const toggle = (list: string[], v: string) => (list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);
  const allProducts = [...new Set([...Object.values(cfg.product_families).flat(), ...brief.products])];

  function setRole(role: Brief["role_sought"]) {
    const defaults = cfg.role_default_importance[role];
    const importance = Object.fromEntries(
      Object.keys(cfg.factors).map((f) => [f, brief.edited.includes(f) ? brief.importance[f] : defaults[f]]),
    );
    set({ role_sought: role, importance });
  }

  function cycleState(s: string) {
    if (brief.primary.includes(s)) set({ primary: brief.primary.filter((x) => x !== s), secondary: [...brief.secondary, s] });
    else if (brief.secondary.includes(s)) set({ secondary: brief.secondary.filter((x) => x !== s) });
    else set({ primary: [...brief.primary, s] });
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-5 sm:grid-cols-2">
        <Field label="Sector">
          <select
            aria-label="Sector"
            className="h-9 w-full rounded-md border bg-white px-2 text-sm"
            value={brief.sector}
            onChange={(e) => set({ sector: e.target.value })}
          >
            {cfg.sectors.map((s) => (
              <option key={s} value={s}>
                {humanize(s)}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Role you need in India">
          <div className="flex gap-2">
            {ROLE_OPTIONS.map((r) => (
              <Chip key={r.value} on={brief.role_sought === r.value} onClick={() => setRole(r.value)}>
                {r.label}
              </Chip>
            ))}
          </div>
        </Field>
      </div>

      <Field label="Products" hint="Pick the products you will sell in India, or add your own tag.">
        <div className="flex flex-wrap gap-2">
          {allProducts.map((p) => (
            <Chip key={p} on={brief.products.includes(p)} onClick={() => set({ products: toggle(brief.products, p) })}>
              {humanize(p)}
            </Chip>
          ))}
          <form
            className="flex gap-1"
            onSubmit={(e) => {
              e.preventDefault();
              const tag = custom.trim().toLowerCase().replace(/\s+/g, "_");
              if (tag && !brief.products.includes(tag)) set({ products: [...brief.products, tag] });
              setCustom("");
            }}
          >
            <Input value={custom} onChange={(e) => setCustom(e.target.value)} placeholder="Other product" className="h-7 w-36 text-xs" />
          </form>
        </div>
      </Field>

      <Field label="Target states" hint="Click once for primary (counts double), twice for secondary, again to clear.">
        <div className="flex flex-wrap gap-2" data-testid="state-picker">
          {cfg.states.map((s) => (
            <Chip key={s} on={brief.primary.includes(s) || brief.secondary.includes(s)} tone={brief.secondary.includes(s) ? "blue" : "navy"} onClick={() => cycleState(s)}>
              {humanize(s)}
              {brief.primary.includes(s) && " · primary"}
              {brief.secondary.includes(s) && " · secondary"}
            </Chip>
          ))}
        </div>
      </Field>

      <Field label="Sales channels you need" hint="Leave empty if channels don't matter (the channel factor then doesn't count).">
        <div className="flex flex-wrap gap-2">
          {cfg.channels.map((c) => (
            <Chip key={c} on={brief.channels_needed.includes(c)} onClick={() => set({ channels_needed: toggle(brief.channels_needed, c) })}>
              {humanize(c)}
            </Chip>
          ))}
        </div>
      </Field>

      <div className="grid gap-5 sm:grid-cols-3">
        <Field label="Volume (units per month)">
          <Input
            type="number"
            min={1}
            value={brief.volume_units_per_month}
            onChange={(e) => set({ volume_units_per_month: Math.max(1, Number(e.target.value) || 1) })}
          />
        </Field>
        <Field label="After-sales service need">
          <div className="flex gap-2">
            {cfg.after_sales_needs.map((n) => (
              <Chip key={n} on={brief.after_sales_need === n} onClick={() => set({ after_sales_need: n as Brief["after_sales_need"] })}>
                {humanize(n)}
              </Chip>
            ))}
          </div>
        </Field>
        <Field label="Competitors to avoid" hint="Brand names, separated by commas.">
          <Input value={brief.competitors} onChange={(e) => set({ competitors: e.target.value })} placeholder="e.g. Flowtek (Demo)" />
        </Field>
      </div>

      <Field label="How much each factor matters" hint="Pre-filled with the defaults for the role you need.">
        <div className="divide-y rounded-lg border bg-white">
          {Object.entries(cfg.factors).map(([f, spec]) => (
            <div key={f} className="flex flex-wrap items-center gap-3 px-3 py-2 text-sm">
              <span className="w-8 font-mono text-xs text-blue">{f}</span>
              <span className="flex-1">{spec.label}</span>
              <div className="flex gap-1">
                {cfg.importance_levels.map((imp) => (
                  <Chip
                    key={imp}
                    on={brief.importance[f] === imp}
                    onClick={() => set({ importance: { ...brief.importance, [f]: imp }, edited: [...new Set([...brief.edited, f])] })}
                  >
                    {humanize(imp)}
                  </Chip>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Field>
    </div>
  );
}
