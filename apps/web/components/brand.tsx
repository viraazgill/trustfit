"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
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
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border border-coral/60 bg-coral/10 px-2 py-0.5 text-xs font-medium text-[#9a4a22]",
        className,
      )}
      title="This company is fictional. It exists to demonstrate TrustFit."
    >
      Fictional demo data
    </span>
  );
}

export function Disclaimer({ className }: { className?: string }) {
  return <p className={cn("text-xs text-ink-muted", className)}>{DISCLAIMER}</p>;
}

export function AppHeader() {
  const { user, logout } = useAuth();
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
