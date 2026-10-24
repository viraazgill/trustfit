import type { Schemas } from "@/lib/api/client";

/** Mirrors `default_role()` in apps/api/app/services/scoring.py: service providers are scored with
 * service_provider_trust_role; business partners with their first role offered. "" while loading. */
export function defaultRole(
  company: Pick<Schemas["ViewerCompany"], "type" | "roles_offered"> | undefined,
  cfg: Schemas["PublicConfig"] | undefined,
): string {
  if (!company || !cfg) return "";
  if (company.type === "service_provider") return cfg.service_provider_trust_role;
  return company.roles_offered[0] ?? Object.keys(cfg.roles)[0];
}
