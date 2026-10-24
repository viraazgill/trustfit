"use client";

import Link from "next/link";
import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { FictionalBadge } from "@/components/brand";
import { VerdictChip } from "@/components/trust";
import { RequireRole } from "@/lib/auth";
import { humanize, num } from "@/lib/format";
import { useCompanies, usePublicConfig } from "@/lib/queries";
import type { Verdict } from "@/lib/trust-types";

function CompanyTable() {
  const { data, isLoading, error } = useCompanies();
  const { data: cfg } = usePublicConfig();
  const [q, setQ] = useState("");
  const roleLabel = (r: string) => cfg?.roles[r]?.label ?? humanize(r);
  const rows = (data ?? []).filter((c) => c.name.toLowerCase().includes(q.toLowerCase()));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-navy">Companies</h1>
          <p className="text-sm text-ink-muted">Latest Trust Score per company, in its default role.</p>
        </div>
        <Input placeholder="Search companies" value={q} onChange={(e) => setQ(e.target.value)} className="w-64 bg-white" />
      </div>
      {error && <p className="text-sm text-verdict-red">{error.message}</p>}
      <div className="rounded-xl border bg-white">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Company</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Role</TableHead>
              <TableHead className="text-right">Score</TableHead>
              <TableHead>Verdict</TableHead>
              <TableHead className="text-right">Confidence</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading && (
              <TableRow>
                <TableCell colSpan={6} className="text-ink-muted">
                  Loading…
                </TableCell>
              </TableRow>
            )}
            {rows.map((c) => (
              <TableRow key={c.id}>
                <TableCell>
                  <Link href={`/companies/${c.id}`} className="font-medium text-blue hover:underline">
                    {c.name}
                  </Link>
                  {c.fictional && <FictionalBadge className="ml-2" />}
                  {c.hq_state && <div className="text-xs text-ink-muted">{humanize(c.hq_state)}</div>}
                </TableCell>
                <TableCell className="text-sm">{humanize(c.type)}</TableCell>
                <TableCell className="text-sm">{c.latest ? roleLabel(c.latest.role) : "—"}</TableCell>
                <TableCell className="text-right font-mono">{c.latest?.score ?? "—"}</TableCell>
                <TableCell>{c.latest && <VerdictChip verdict={c.latest.verdict as Verdict} size="sm" />}</TableCell>
                <TableCell className="text-right font-mono text-sm">{num(c.latest?.confidence)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

export default function CompaniesPage() {
  return (
    <RequireRole role="analyst">
      <CompanyTable />
    </RequireRole>
  );
}
