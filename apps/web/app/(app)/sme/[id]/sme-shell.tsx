"use client";

import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import { Disclaimer, FictionalBadge } from "@/components/brand";
import { RequireRole } from "@/lib/auth";
import { humanize, placeName } from "@/lib/format";
import { useSme } from "@/lib/sme-queries";
import { cn } from "@/lib/utils";

function SmeHeader({ id }: { id: string }) {
  const { data: sme, error } = useSme(id);
  const pathname = usePathname();
  const tabs = [
    { href: `/sme/${id}`, label: "Readiness" },
    { href: `/sme/${id}/matches`, label: "Matches" },
    { href: `/sme/${id}/team`, label: "India entry team" },
    { href: `/sme/${id}/brief`, label: "Brief" },
  ];
  if (error) return <p className="text-sm text-verdict-red">{error.message}</p>;
  return (
    <div className="mb-6 space-y-3 print:hidden">
      <Link href="/sme" className="text-xs text-ink-muted hover:underline">
        ← All SME briefs
      </Link>
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold text-navy">{sme?.name ?? "…"}</h1>
        {sme?.fictional && <FictionalBadge />}
      </div>
      {sme && (
        <p className="text-sm text-ink-muted">
          {[sme.city, sme.country].filter(Boolean).join(", ")} · seeking a {humanize(sme.role_sought).toLowerCase()} in{" "}
          {(sme.target_states.primary ?? []).map(placeName).join(", ")}
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

export default function SmeShell({ children }: { children: React.ReactNode }) {
  const { id } = useParams<{ id: string }>();
  return (
    <RequireRole role="viewer">
      <SmeHeader id={id} />
      {children}
      <Disclaimer className="mt-8" />
    </RequireRole>
  );
}
