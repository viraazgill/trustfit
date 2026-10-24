"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api/client";
import { usePublicConfig } from "@/lib/queries";
import { cn } from "@/lib/utils";
import { hasRole, useAuth } from "@/lib/auth";

export const DISCLAIMER = "TrustFit Score is not a credit rating or investment advice.";

export function Wordmark({ className }: { className?: string }) {
  return (
    <span className={cn("font-semibold tracking-tight", className)}>
      Trust<span className="text-coral">Fit</span>
    </span>
  );
}

export function FictionalBadge({ className }: { className?: string }) {
  const t = useTranslations("common");
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border border-coral/60 bg-coral/10 px-2 py-0.5 text-xs font-medium text-[#9a4a22]",
        className,
      )}
      title={t("fictionalTitle")}
    >
      {t("fictionalBadge")}
    </span>
  );
}

/** A visible stripe on every fictional record's page. */
export function DemoRibbon({ kind }: { kind: "company" | "sme" }) {
  const t = useTranslations("common");
  return (
    <div data-testid="demo-ribbon" className="mb-4 rounded-md border border-coral/60 bg-coral/10 px-3 py-1.5 text-xs font-medium text-[#9a4a22]">
      {t("demoRibbon", { what: t(kind === "sme" ? "thisSme" : "thisCompany") })}
    </div>
  );
}

function ResetDemoButton() {
  const qc = useQueryClient();
  const [state, setState] = useState<"idle" | "busy" | "done" | "error">("idle");
  async function reset() {
    if (!window.confirm("Reset demo data? This reloads every company, evidence row, flag and SME from the seed files.")) return;
    setState("busy");
    try {
      await api("/admin/reset-demo", "POST");
      await qc.invalidateQueries();
      setState("done");
    } catch {
      setState("error");
    }
  }
  return (
    <button className="rounded border border-coral/70 px-2 py-1 text-xs text-coral hover:bg-coral/10" onClick={reset} disabled={state === "busy"}>
      {state === "busy" ? "Resetting…" : state === "done" ? "Demo data reset" : state === "error" ? "Reset failed" : "Reset demo data"}
    </button>
  );
}

export function Disclaimer({ className }: { className?: string }) {
  const t = useTranslations("common");
  return <p className={cn("text-xs text-ink-muted", className)}>{t("disclaimer")}</p>;
}

export function AppHeader() {
  const { user, logout } = useAuth();
  const { data: cfg } = usePublicConfig();
  const router = useRouter();
  const pathname = usePathname();
  const links = [
    { href: "/companies", label: "Companies", show: hasRole(user, "analyst") },
    { href: "/sme", label: "SME journey", show: hasRole(user, "viewer") },
  ];
  return (
    <header className="bg-navy text-white print:hidden">
      <div className="mx-auto flex h-14 max-w-6xl items-center gap-6 px-4">
        <Link href="/" className="text-lg">
          <Wordmark />
        </Link>
        <nav className="flex gap-4 text-sm">
          {links
            .filter((l) => l.show)
            .map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className={cn("text-white/70 hover:text-white", pathname.startsWith(l.href) && "text-white")}
              >
                {l.label}
              </Link>
            ))}
        </nav>
        <div className="ml-auto flex items-center gap-3 text-sm">
          {user ? (
            <>
              {hasRole(user, "analyst") && cfg?.fixed_scoring_date && (
                <span className="hidden font-mono text-xs text-white/60 md:inline" title="SCORING_AS_OF is set: every score uses this date">
                  scoring date {cfg.scoring_date}
                </span>
              )}
              {hasRole(user, "admin") && <ResetDemoButton />}
              <span className="hidden text-white/70 sm:inline">
                {user.email} · <span className="font-mono text-xs uppercase">{user.role}</span>
              </span>
              <button
                className="rounded border border-white/30 px-2 py-1 text-xs hover:bg-white/10"
                onClick={() => {
                  logout();
                  router.push("/login");
                }}
              >
                Sign out
              </button>
            </>
          ) : (
            <Link href="/login" className="rounded border border-white/30 px-2 py-1 text-xs hover:bg-white/10">
              Sign in
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
