"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { FictionalBadge } from "@/components/brand";
import { conflictText, FitCategoryChip } from "@/components/fit";
import { VerdictChip } from "@/components/trust";
import { useCompanies } from "@/lib/queries";
import { useFit, useSme } from "@/lib/sme-queries";
import type { Verdict } from "@/lib/trust-types";

function PartnerRow({ smeId, companyId, name, fictional }: { smeId: string; companyId: string; name: string; fictional: boolean }) {
  const { data: fit } = useFit(smeId, companyId);
  const conflict = fit && conflictText(fit);
  return (
    <li className="flex flex-wrap items-center gap-3 py-3" data-testid={`match-${companyId}`}>
      <Link href={`/sme/${smeId}/company/${companyId}`} className="font-medium text-blue hover:underline">
        {name}
      </Link>
      {fictional && <FictionalBadge />}
      {fit && (
        <span className="ml-auto flex flex-wrap items-center gap-3 text-sm">
          <span className="text-ink-muted">Trust {fit.trust.score ?? "—"}</span>
          <span className="font-mono text-navy">Fit {fit.score ?? "—"}</span>
          <FitCategoryChip category={fit.category} label={fit.category_label} />
          <VerdictChip verdict={fit.combined_verdict as Verdict} size="sm" />
        </span>
      )}
      {conflict && <span className="w-full text-xs text-verdict-red">Competitor conflict: {conflict}</span>}
    </li>
  );
}

/** Business partners offering the role this SME needs, with Fit and the combined verdict. */
export default function Matches() {
  const { id } = useParams<{ id: string }>();
  const { data: sme } = useSme(id);
  const { data: companies } = useCompanies();
  if (!sme || !companies) return <p className="text-sm text-ink-muted">Loading…</p>;
  const partners = companies.filter((c) => c.type === "business_partner" && c.roles_offered.includes(sme.role_sought));
  return (
    <section className="rounded-xl border bg-white px-5">
      <ul className="divide-y">
        {partners.map((c) => (
          <PartnerRow key={c.id} smeId={id} companyId={c.id} name={c.name} fictional={c.fictional} />
        ))}
        {partners.length === 0 && <li className="py-3 text-sm text-ink-muted">No partner offers this role yet.</li>}
      </ul>
    </section>
  );
}
