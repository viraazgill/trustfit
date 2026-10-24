"use client";

import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { FictionalBadge } from "@/components/brand";
import { RequireRole } from "@/lib/auth";
import { humanize } from "@/lib/format";
import { useSmes } from "@/lib/sme-queries";

function SmeList() {
  const { data: smes, isLoading, error } = useSmes();
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-navy">SME journey</h1>
          <p className="text-sm text-ink-muted">
            Your India entry brief, readiness check, matched partners and India entry team.
          </p>
        </div>
        <Link href="/sme/new" className={buttonVariants()}>
          New SME brief
        </Link>
      </div>
      {error && <p className="text-sm text-verdict-red">{error.message}</p>}
      {isLoading && <p className="text-sm text-ink-muted">Loading…</p>}
      <div className="grid gap-4 md:grid-cols-2">
        {(smes ?? []).map((s) => (
          <Link key={s.id} href={`/sme/${s.id}`} className="rounded-xl border bg-white p-5 hover:border-blue">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-semibold text-navy">{s.name}</span>
              {s.fictional && <FictionalBadge />}
            </div>
            <p className="mt-1 text-sm text-ink-muted">{s.description}</p>
            <p className="mt-3 text-xs text-ink-muted">
              {[s.city, s.country].filter(Boolean).join(", ")} · seeking a {humanize(s.role_sought).toLowerCase()} ·{" "}
              {humanize(s.sector)}
            </p>
          </Link>
        ))}
      </div>
    </div>
  );
}

export default function SmePage() {
  return (
    <RequireRole role="viewer">
      <SmeList />
    </RequireRole>
  );
}
