"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { FictionalBadge } from "@/components/brand";
import { FitCard } from "@/components/fit";
import { TrustReportView } from "@/components/trust-report";
import { defaultRole } from "@/lib/roles";
import { humanize } from "@/lib/format";
import { useCompany, usePublicConfig } from "@/lib/queries";
import { useFit, useSme, useTrustReport } from "@/lib/sme-queries";

/** SME-safe company report: the Trust summary for the role this SME needs, plus Fit for its brief. */
export default function CompanyReport() {
  const { id, cid } = useParams<{ id: string; cid: string }>();
  const { data: sme } = useSme(id);
  const { data: company } = useCompany(cid);
  const { data: cfg } = usePublicConfig();
  const partner = !!company && !!sme && company.type === "business_partner" && company.roles_offered.includes(sme.role_sought);
  const role = partner ? sme!.role_sought : defaultRole(company, cfg);
  const report = useTrustReport(cid, role || undefined);
  const fit = useFit(id, cid, partner);

  if (!company || !sme || !role) return <p className="text-sm text-ink-muted">Loading…</p>;
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <Link href={`/sme/${id}/matches`} className="text-xs text-ink-muted hover:underline">
          ← Matches
        </Link>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-xl font-semibold text-navy" data-testid="company-name">
          {company.name}
        </h2>
        {company.fictional && <FictionalBadge />}
        <span className="text-sm text-ink-muted">
          {humanize(company.type)} · Trust scored as a {cfg?.roles[role]?.label.toLowerCase()}
          {company.hq_state && ` · ${humanize(company.hq_state)}`}
        </span>
      </div>
      {company.description && <p className="text-sm text-ink-muted">{company.description}</p>}
      {fit.data && <FitCard fit={fit.data} />}
      {fit.error && <p className="text-sm text-verdict-red">{fit.error.message}</p>}
      {report.data && <TrustReportView report={report.data} />}
    </div>
  );
}
