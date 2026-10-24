"use client";

import { LanguageToggle, SmeIntl } from "@/lib/i18n";

/** Every SME page: the chosen language (EN/JA) and its toggle. */
export default function SmeScope({ children }: { children: React.ReactNode }) {
  return (
    <SmeIntl>
      <div className="mb-2 flex justify-end">
        <LanguageToggle />
      </div>
      {children}
    </SmeIntl>
  );
}
