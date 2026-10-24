"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { DemoRibbon, Disclaimer, FictionalBadge, Wordmark } from "@/components/brand";
import { PdfButton } from "@/components/pdf-button";
import { TrustReportView } from "@/components/trust-report";
import { RequireRole } from "@/lib/auth";
import { placeName } from "@/lib/format";
import { LanguageToggle, SmeIntl } from "@/lib/i18n";
import { useCompany, usePublicConfig } from "@/lib/queries";
import { defaultRole } from "@/lib/roles";
import { useTrustReport } from "@/lib/sme-queries";
import { cn } from "@/lib/utils";

/** The one-page SME-safe Trust report for one company and role. The API prints this page for the PDF. */
function Report() {
  const { cid } = useParams<{ cid: string }>();
  const params = useSearchParams();
  const { data: company } = useCompany(cid);
  const { data: cfg } = usePublicConfig();
  const role = params.get("role") ?? defaultRole(company, cfg);
  const report = useTrustReport(cid, role || undefined);
  const t = useTranslations("report");
  const tt = useTranslations("trust");
  const tc = useTranslations("common");
  const r = report.data;
  if (report.error) return <p className="text-sm text-verdict-red">{report.error.message}</p>;
  if (!company || !cfg || !r) return <p className="text-sm text-ink-muted">{tc("loading")}</p>;

  return (
    <div data-print-ready className="space-y-5">
      <div className="flex items-center justify-between gap-3 print:hidden">
        <nav className="flex gap-1 text-sm">
          {Object.keys(cfg.roles).map((key) => (
            <Link
              key={key}
              href={`/report/company/${cid}?role=${key}`}
              className={cn("rounded-md px-2.5 py-1", key === role ? "bg-navy text-white" : "text-ink-muted hover:bg-muted")}
            >
              {tt(`roles.${key}`)}
            </Link>
          ))}
        </nav>
        <span className="flex items-center gap-2">
          <LanguageToggle />
          <PdfButton path={`/companies/${cid}/report.pdf?role=${role}`} filename={`trustfit-${cid}-${role}.pdf`} />
        </span>
      </div>
      {company.fictional && <DemoRibbon kind="company" />}
      <header className="flex flex-wrap items-end justify-between gap-3 border-b pb-4">
        <div>
          <div className="text-sm">
            <Wordmark /> <span className="text-ink-muted">· {tt("title")}</span>
          </div>
          <h1 className="mt-1 flex flex-wrap items-center gap-3 text-2xl font-semibold text-navy">
            {company.name}
            {company.fictional && <FictionalBadge />}
          </h1>
          <p className="text-sm text-ink-muted">
            {tt("scoredAs", { role: tt(`roles.${role}`) })}
            {company.hq_state && ` · ${placeName(company.hq_state)}`}
          </p>
        </div>
        <p className="text-xs text-ink-muted">{t("scoredOn", { date: r.as_of, version: r.weight_set })}</p>
      </header>
      <TrustReportView report={r} />
      <Disclaimer className="border-t pt-3" />
    </div>
  );
}

export default function TrustReportPage() {
  return (
    <RequireRole role="viewer">
      <SmeIntl>
        <Report />
      </SmeIntl>
    </RequireRole>
  );
}
