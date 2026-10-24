"use client";

import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import { FictionalBadge } from "@/components/brand";
import { RequireRole } from "@/lib/auth";
import { humanize, placeName } from "@/lib/format";
import { useCompany } from "@/lib/queries";
import { cn } from "@/lib/utils";

function CompanyHeader({ id }: { id: string }) {
  const { data: company, error } = useCompany(id);
  const pathname = usePathname();
  const tabs = [
    { href: `/companies/${id}`, label: "Score" },
    { href: `/companies/${id}/evidence`, label: "Evidence" },
    { href: `/companies/${id}/flags`, label: "Flags, gates and trends" },
  ];
  if (error) return <p className="text-sm text-verdict-red">{error.message}</p>;
  return (
    <div className="mb-6 space-y-3">
      <Link href="/companies" className="text-xs text-ink-muted hover:underline">
        ← All companies
      </Link>
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold text-navy">{company?.name ?? "…"}</h1>
        {company?.fictional && <FictionalBadge />}
      </div>
      {company && (
        <p className="text-sm text-ink-muted">
          {[humanize(company.type), company.cin && `CIN ${company.cin}`, company.nse_code && `NSE ${company.nse_code}`,
            company.hq_state && placeName(company.hq_state)]
            .filter(Boolean)
            .join(" · ")}
        </p>
      )}
      <nav className="flex gap-1 border-b">
        {tabs.map((t) => (
          <Link
            key={t.href}
            href={t.href}
            className={cn(
              "-mb-px border-b-2 px-3 py-2 text-sm",
              pathname === t.href ? "border-coral font-medium text-navy" : "border-transparent text-ink-muted hover:text-navy",
            )}
          >
            {t.label}
          </Link>
        ))}
      </nav>
    </div>
  );
}

export default function CompanyShell({ children }: { children: React.ReactNode }) {
  const { id } = useParams<{ id: string }>();
  return (
    <RequireRole role="analyst">
      <CompanyHeader id={id} />
      {children}
    </RequireRole>
  );
}
