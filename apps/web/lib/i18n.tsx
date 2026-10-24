"use client";

/**
 * EN/JA for the SME pages (next-intl, client-side: both message files are bundled, so it works offline).
 * The app is English everywhere; <SmeIntl> re-provides the chosen language inside the SME pages only.
 *
 * Labels that come from config/*.yaml (readiness questions, JETRO asks, capability and factor labels...)
 * are never copied into en.json: English shows the config text, and ja.json translates them under
 * `labels.*`, keyed by id. Every Japanese string is listed for human review in messages/ja.REVIEW.md.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useSyncExternalStore } from "react";
import { NextIntlClientProvider, useTranslations } from "next-intl";
import en from "@/messages/en.json";
import ja from "@/messages/ja.json";

export type Locale = "en" | "ja";
const STORAGE_KEY = "trustfit.locale";
const MESSAGES = { en, ja: { ...ja } } as const;

const LocaleContext = createContext<{ locale: Locale; setLocale: (l: Locale) => void }>({
  locale: "en",
  setLocale: () => {},
});

// The chosen locale lives in localStorage; useSyncExternalStore reads it without a setState-in-effect and
// renders English on the server, so the first paint always matches.
const LOCALE_EVENT = "trustfit:locale";

function readLocale(): Locale {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === "ja" ? "ja" : "en";
  } catch {
    return "en";
  }
}

function subscribe(onChange: () => void) {
  window.addEventListener(LOCALE_EVENT, onChange);
  window.addEventListener("storage", onChange);
  return () => {
    window.removeEventListener(LOCALE_EVENT, onChange);
    window.removeEventListener("storage", onChange);
  };
}

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const locale = useSyncExternalStore(subscribe, readLocale, () => "en" as Locale);
  const setLocale = useCallback((l: Locale) => {
    try {
      window.localStorage.setItem(STORAGE_KEY, l);
    } catch {
      // storage unavailable: the toggle can't persist, so it stays in English
    }
    window.dispatchEvent(new Event(LOCALE_EVENT));
  }, []);
  const value = useMemo(() => ({ locale, setLocale }), [locale, setLocale]);
  return (
    <LocaleContext.Provider value={value}>
      <NextIntlClientProvider locale="en" messages={MESSAGES.en} timeZone="Asia/Kolkata">
        {children}
      </NextIntlClientProvider>
    </LocaleContext.Provider>
  );
}

export const useLocale = () => useContext(LocaleContext);

/** Applies the chosen language to the SME pages it wraps. */
export function SmeIntl({ children }: { children: React.ReactNode }) {
  const { locale } = useLocale();
  useEffect(() => {
    document.documentElement.lang = locale;
    return () => {
      document.documentElement.lang = "en";
    };
  }, [locale]);
  return (
    <NextIntlClientProvider locale={locale} messages={MESSAGES[locale]} timeZone="Asia/Kolkata">
      {children}
    </NextIntlClientProvider>
  );
}

export function LanguageToggle() {
  const { locale, setLocale } = useLocale();
  const t = useTranslations("common");
  return (
    <div className="inline-flex overflow-hidden rounded-md border bg-white text-xs print:hidden" role="radiogroup" aria-label={t("language")}>
      {(["en", "ja"] as const).map((l) => (
        <button
          key={l}
          type="button"
          role="radio"
          aria-checked={locale === l}
          onClick={() => setLocale(l)}
          className={locale === l ? "bg-navy px-2.5 py-1 text-white" : "px-2.5 py-1 hover:bg-muted"}
        >
          {l === "en" ? "EN" : "日本語"}
        </button>
      ))}
    </div>
  );
}

/** A config label in the current language: the Japanese translation under labels.<key> when there is one,
 * else the config's own (English) text. */
export function useLabel() {
  const t = useTranslations("labels");
  return useCallback((key: string, fallback: string) => (t.has(key) ? t(key) : fallback), [t]);
}
