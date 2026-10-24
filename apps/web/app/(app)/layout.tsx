import { Suspense } from "react";
import { AppHeader } from "@/components/brand";

// Pages here are client components that read the URL (useParams, usePathname), so each part streams
// in under a Suspense boundary instead of blocking prerendering. They render only after the client-side
// sign-in check (RequireRole), so there is nothing to prerender: opt out of instant-navigation validation.
export const instant = false;

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <Suspense fallback={<div className="h-14 bg-navy" />}>
        <AppHeader />
      </Suspense>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">
        <Suspense fallback={<p className="text-sm text-ink-muted">Loading…</p>}>{children}</Suspense>
      </main>
    </>
  );
}
