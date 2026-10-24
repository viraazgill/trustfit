import Link from "next/link";
import { Suspense } from "react";
import { buttonVariants } from "@/components/ui/button";
import { AppHeader, DISCLAIMER } from "@/components/brand";
import { cn } from "@/lib/utils";

const MODULES = [
  {
    step: "1",
    title: "Trust Score",
    question: "Can this Indian company be trusted?",
    body: "37 parameters from public records, weighted by role. Missing evidence lowers confidence, never the score; knock-outs and the weakest-link rule protect the verdict.",
  },
  {
    step: "2",
    title: "Fit Score",
    question: "Is it right for us?",
    body: "Six factors scored against your brief: sector, regions, channels, capacity, service and competing brands. Fit can lower a verdict, never raise it.",
  },
  {
    step: "3",
    title: "Gap Bridge",
    question: "What are we missing, and who can fill it?",
    body: "A 16-question readiness check on JETRO's six asks turns your gaps into an India entry team of trusted partners, and names what is still uncovered.",
  },
];

export default function Home() {
  return (
    <>
      <Suspense fallback={<div className="h-14 bg-navy" />}>
        <AppHeader />
      </Suspense>
      <main className="flex-1">
        <section className="bg-navy text-white">
          <div className="mx-auto max-w-6xl px-4 pb-16 pt-12">
            <p className="font-mono text-xs uppercase tracking-widest text-coral">For Japanese SMEs entering India · JETRO-PS-01</p>
            <h1 className="mt-4 max-w-3xl text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
              Trust decides eligibility. Fit justifies the visit.
            </h1>
            <p className="mt-4 max-w-2xl text-lg text-white/75">
              TrustFit checks Indian partners against verified public evidence, matches them to your brief, and builds the team that
              covers what you are missing.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/companies/subros" className={cn(buttonVariants({ size: "lg" }), "bg-coral text-white hover:bg-coral/90")}>
                See a Trust Score (Subros)
              </Link>
              <Link href="/sme/sorano" className={cn(buttonVariants({ size: "lg", variant: "outline" }), "border-white/40 bg-transparent text-white hover:bg-white/10")}>
                Try the SME journey (Sorano, demo data)
              </Link>
            </div>
          </div>
        </section>
        <section className="mx-auto grid max-w-6xl gap-4 px-4 py-12 md:grid-cols-3">
          {MODULES.map((m) => (
            <div key={m.title} className="rounded-xl border bg-white p-6">
              <div className="flex items-baseline gap-3">
                <span className="font-mono text-sm text-coral">{m.step}</span>
                <h2 className="text-lg font-semibold text-navy">{m.title}</h2>
              </div>
              <p className="mt-1 text-sm font-medium text-blue">{m.question}</p>
              <p className="mt-3 text-sm text-ink-muted">{m.body}</p>
            </div>
          ))}
        </section>
        <section className="mx-auto max-w-6xl px-4 pb-12">
          <p className="text-xs text-ink-muted">
            {DISCLAIMER} Subros Ltd is a real listed company scored from public sources; every other company and the SME Sorano
            Instruments are fictional demo data.
          </p>
        </section>
      </main>
    </>
  );
}
