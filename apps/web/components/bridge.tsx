"use client";

/** Gap Bridge pieces: severity chip, readiness radar, gap card, coverage ring, coverage heatmap. */
import { PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer, Tooltip } from "recharts";
import { rhu } from "@/lib/format";
import type { ReadinessDimension } from "@/lib/bridge-queries";
import { cn } from "@/lib/utils";

// Severity is a status: colour plus its label, never colour alone.
const SEVERITY_STYLE: Record<string, string> = {
  critical: "border-verdict-red/50 bg-verdict-red/10 text-verdict-red",
  significant: "border-verdict-amber/50 bg-verdict-amber/10 text-[#8a5a14]",
  minor: "border-ink-muted/30 bg-muted text-ink-muted",
};

export function SeverityChip({ label }: { label: string }) {
  return (
    <span data-testid="severity" className={cn("inline-flex rounded-full border px-2 py-0.5 text-xs font-medium capitalize", SEVERITY_STYLE[label])}>
      {label}
    </span>
  );
}

export function CoveredByTrustFit() {
  return (
    <span className="inline-flex rounded-full border border-blue/40 bg-blue/10 px-2 py-0.5 text-xs font-medium text-blue">
      Covered by TrustFit
    </span>
  );
}

/** Axis label wrapped onto two lines at a word boundary, anchored away from the chart. */
function AxisLabel({ x, y, payload, textAnchor }: { x?: number | string; y?: number | string; payload?: { value: string }; textAnchor?: string }) {
  const words = (payload?.value ?? "").split(" ");
  const half = Math.ceil(words.length / 2);
  const lines = words.length > 2 ? [words.slice(0, half).join(" "), words.slice(half).join(" ")] : [words.join(" ")];
  return (
    <text x={x} y={y} textAnchor={textAnchor as "start" | "middle" | "end"} fill="#4a5568" fontSize={11}>
      {lines.map((line, i) => (
        <tspan key={i} x={x} dy={i === 0 ? (lines.length > 1 ? -4 : 4) : 13}>
          {line}
        </tspan>
      ))}
    </text>
  );
}

const BRAND_BLUE = "#1f4e8c"; // single series: contrast-checked against the white card surface

/** Readiness 0-100 on the six JETRO asks. One series, so the title names it and no legend is shown. */
export function ReadinessRadar({ dimensions }: { dimensions: Record<string, ReadinessDimension> }) {
  const data = Object.entries(dimensions).map(([id, d]) => ({ id, label: d.label, ask: d.jetro_ask, readiness: d.readiness }));
  return (
    <div className="h-80 w-full" data-testid="readiness-radar" role="img" aria-label="Readiness by JETRO ask, 0 to 100">
      <ResponsiveContainer>
        <RadarChart data={data} outerRadius="66%" margin={{ top: 24, right: 72, bottom: 24, left: 72 }}>
          <PolarGrid stroke="#d9d6cf" />
          <PolarAngleAxis dataKey="label" tick={AxisLabel} />
          {/* scale between two axes, so its numbers never sit on an axis label */}
          <PolarRadiusAxis domain={[0, 100]} tickCount={5} tick={{ fill: "#4a5568", fontSize: 9 }} axisLine={false} angle={60} />
          <Radar dataKey="readiness" stroke={BRAND_BLUE} strokeWidth={2} fill={BRAND_BLUE} fillOpacity={0.15}
            dot={{ r: 4, fill: BRAND_BLUE, stroke: "#ffffff", strokeWidth: 2 }} isAnimationActive={false} />
          <Tooltip
            content={({ active, payload }) => {
              const p = active && payload?.[0]?.payload;
              if (!p) return null;
              return (
                <div className="max-w-64 rounded-md border bg-white px-3 py-2 text-xs shadow-sm">
                  <div className="font-medium text-navy">
                    {p.id} {p.label}: {rhu(p.readiness, 1)}% ready
                  </div>
                  <div className="text-ink-muted">JETRO ask: {p.ask}</div>
                </div>
              );
            }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function GapCard({ id, d }: { id: string; d: ReadinessDimension }) {
  return (
    <div data-testid={`gap-${id}`} className="rounded-xl border bg-white p-4">
      <div className="flex items-start justify-between gap-2">
        <div>
          <span className="mr-2 font-mono text-xs font-semibold text-blue">{id}</span>
          <span className="text-sm font-medium text-navy">{d.label}</span>
        </div>
        {d.covered_by_trustfit ? <CoveredByTrustFit /> : <SeverityChip label={d.severity_label} />}
      </div>
      <p className="mt-1 text-xs text-ink-muted">{d.jetro_ask}</p>
      <div className="mt-3 flex items-baseline gap-4 text-sm">
        <span>
          <span className="font-mono text-lg font-semibold text-navy">{rhu(d.readiness)}%</span>{" "}
          <span className="text-xs text-ink-muted">ready</span>
        </span>
        <span>
          <span className="font-mono text-lg font-semibold text-navy">{rhu(d.severity)}</span>{" "}
          <span className="text-xs text-ink-muted">gap severity</span>
        </span>
      </div>
      {d.covered_by_trustfit && (
        <p className="mt-2 text-xs text-blue">Every company TrustFit recommends is already Trust-scored and verified.</p>
      )}
    </div>
  );
}

/** A single headline number with a ring: the share of the SME's gap severity the team covers. */
export function CoverageRing({ value, target }: { value: number; target: number }) {
  const r = 52;
  const c = 2 * Math.PI * r;
  const pctValue = Math.max(0, Math.min(100, value));
  return (
    <div className="flex items-center gap-4" data-testid="team-coverage">
      <svg width="128" height="128" viewBox="0 0 128 128" role="img" aria-label={`Team covers ${rhu(value)}% of gap severity`}>
        <circle cx="64" cy="64" r={r} fill="none" stroke="#e8e5de" strokeWidth="12" />
        <circle cx="64" cy="64" r={r} fill="none" stroke={BRAND_BLUE} strokeWidth="12" strokeLinecap="round"
          strokeDasharray={`${(pctValue / 100) * c} ${c}`} transform="rotate(-90 64 64)" />
        <line x1="64" y1="6" x2="64" y2="18" stroke="#e8875a" strokeWidth="2" transform={`rotate(${(target / 100) * 360} 64 64)`} />
        <text x="64" y="70" textAnchor="middle" className="fill-navy font-mono text-2xl font-semibold">
          {rhu(value)}%
        </text>
      </svg>
      <div className="text-sm">
        <div className="font-medium text-navy">of your gap severity covered</div>
        <div className="text-xs text-ink-muted">The team stops growing at {target}% (coral mark) or when another member adds too little.</div>
      </div>
    </div>
  );
}

// One-hue sequential ramp (light -> dark) from the dataviz reference palette; lightest = no coverage.
const SEQ_RAMP = ["#f3f1ec", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95"];

function cellColor(v: number): string {
  if (v <= 0) return SEQ_RAMP[0];
  return SEQ_RAMP[Math.min(SEQ_RAMP.length - 1, 1 + Math.floor(v * (SEQ_RAMP.length - 1)))];
}

/** Gaps x members: each cell is that member's own coverage of the gap (0-100%). */
export function CoverageHeatmap({
  gaps,
  members,
}: {
  gaps: { id: string; label: string; severity: string; team: number }[];
  members: { id: string; name: string; perGap: Record<string, number> }[];
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-separate text-xs" style={{ borderSpacing: 2 }} data-testid="coverage-matrix">
        <thead>
          <tr>
            <th className="p-2 text-left font-normal text-ink-muted">Gap</th>
            {members.map((m) => (
              <th key={m.id} className="max-w-28 p-2 text-left font-medium text-navy">
                {m.name.replace(" (Demo)", "")}
              </th>
            ))}
            <th className="p-2 text-left font-medium text-navy">Team</th>
          </tr>
        </thead>
        <tbody>
          {gaps.map((g) => (
            <tr key={g.id}>
              <td className="p-2 text-navy">
                <span className="mr-1 font-mono text-blue">{g.id}</span>
                {g.label} <span className="text-ink-muted">({g.severity})</span>
              </td>
              {members.map((m) => {
                const v = m.perGap[g.id] ?? 0;
                return (
                  <td key={m.id} title={`${m.name}: covers ${rhu(100 * v)}% of ${g.label}`}
                    className={cn("rounded p-2 text-center font-mono", v >= 0.6 ? "text-white" : "text-navy")}
                    style={{ background: cellColor(v) }}>
                    {v > 0 ? `${rhu(100 * v)}%` : "—"}
                  </td>
                );
              })}
              <td title={`Team covers ${rhu(100 * g.team)}% of ${g.label}`}
                className={cn("rounded p-2 text-center font-mono font-semibold", g.team >= 0.6 ? "text-white" : "text-navy")}
                style={{ background: cellColor(g.team) }}>
                {rhu(100 * g.team)}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-xs text-ink-muted">Darker = more of the gap covered. Each capability counts once, from the team&apos;s strongest member.</p>
    </div>
  );
}
