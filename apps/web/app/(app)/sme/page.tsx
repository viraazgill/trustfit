"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { buttonVariants } from "@/components/ui/button";
import { Disclaimer, FictionalBadge } from "@/components/brand";
import { RequireRole } from "@/lib/auth";
import { humanize } from "@/lib/format";
import { useLabel } from "@/lib/i18n";
import { useSmes } from "@/lib/sme-queries";

function SmeList() {
  const { data: smes, isLoading, error } = useSmes();
  const t = useTranslations("sme");
  const tt = useTranslations("trust");
  const tc = useTranslations("common");
  const tl = useLabel();
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-navy">{t("journey")}</h1>
          <p className="text-sm text-ink-muted">
            {t("journeyIntro")}
          </p>
        </div>
        <Link href="/sme/new" className={buttonVariants()}>
          {t("newBrief")}
        </Link>
      </div>
      {error && <p className="text-sm text-verdict-red">{error.message}</p>}
      {isLoading && <p className="text-sm text-ink-muted">{tc("loading")}</p>}
      <div className="grid gap-4 md:grid-cols-2">
        {(smes ?? []).map((s) => (
          <Link key={s.id} href={`/sme/${s.id}`} className="rounded-xl border bg-white p-5 hover:border-blue">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-semibold text-navy">{s.name}</span>
              {s.fictional && <FictionalBadge />}
            </div>
            <p className="mt-1 text-sm text-ink-muted">{s.description}</p>
            <p className="mt-3 text-xs text-ink-muted">
              {[s.city, s.country].filter(Boolean).join(", ")} · {t("seeking", { role: tt(`roles.${s.role_sought}`) })} ·{" "}
              {tl(`sectors.${s.sector}`, humanize(s.sector))}
            </p>
          </Link>
        ))}
      </div>
      <Disclaimer />
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
