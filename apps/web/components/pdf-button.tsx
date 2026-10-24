"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { API_URL, ApiError, getToken } from "@/lib/api/client";
import { useLocale } from "@/lib/i18n";

/** Downloads a PDF the API prints from this very page (in the current language). */
export function PdfButton({ path, filename }: { path: string; filename: string }) {
  const t = useTranslations("report");
  const { locale } = useLocale();
  const [state, setState] = useState<"idle" | "busy" | "error">("idle");
  const [message, setMessage] = useState<string | null>(null);

  async function download() {
    setState("busy");
    setMessage(null);
    try {
      const sep = path.includes("?") ? "&" : "?";
      const res = await fetch(`${API_URL}${path}${sep}lang=${locale}`, { headers: { Authorization: `Bearer ${getToken()}` } });
      if (!res.ok) {
        const err = (await res.json().catch(() => null))?.error;
        throw new ApiError(res.status, err?.code ?? "error", err?.message ?? res.statusText);
      }
      const url = URL.createObjectURL(await res.blob());
      const a = Object.assign(document.createElement("a"), { href: url, download: filename });
      a.click();
      URL.revokeObjectURL(url);
      setState("idle");
    } catch (err) {
      setState("error");
      setMessage(err instanceof Error ? err.message : null);
    }
  }

  return (
    <span className="inline-flex items-center gap-2 print:hidden">
      <Button variant="outline" onClick={download} disabled={state === "busy"} data-testid="pdf-button">
        {state === "busy" ? t("preparing") : t("downloadPdf")}
      </Button>
      {state === "error" && <span className="text-xs text-verdict-red">{message ?? t("pdfFailed")}</span>}
    </span>
  );
}
