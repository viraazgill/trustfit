"use client";

import { useTranslations } from "next-intl";
import { useRelationText } from "@/components/fit";

const CONFLICT = /^competitor conflict: (\S+) (.+)$/;

/** Exclusion reasons from the engine ("knock-out", "competitor conflict: represents X", ...) in the
 * current language. Unknown reasons are shown as the engine wrote them. */
export function useExclusionText() {
  const t = useTranslations("bridge.exclusion");
  const relationText = useRelationText();
  return (reason: string): string => {
    if (reason === "knock-out") return t("knockout");
    if (reason === "insufficient verified data") return t("insufficient");
    if (reason === "Trust verdict Red") return t("red");
    if (reason === "not a fit") return t("notAFit");
    const m = CONFLICT.exec(reason);
    if (m) return t("conflict", { detail: relationText(m[1], m[2]) });
    return reason.charAt(0).toUpperCase() + reason.slice(1);
  };
}
