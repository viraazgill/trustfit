"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Schemas } from "@/lib/api/client";

export type Sme = Schemas["SmeOut"];
export type SmeIn = Schemas["SmeIn"];
export type SmePatch = Schemas["SmePatch"];
export type FitResult = Schemas["ViewerFit"];
export type FitConfig = Schemas["PublicFitConfig"];
export type TrustReport = Schemas["ViewerTrustReport"];

export const useFitConfig = () =>
  useQuery({ queryKey: ["config", "fit"], queryFn: () => api<FitConfig>("/config/fit"), staleTime: Infinity });

export const useSmes = () => useQuery({ queryKey: ["smes"], queryFn: () => api<Sme[]>("/smes") });

export const useSme = (id: string) => useQuery({ queryKey: ["sme", id], queryFn: () => api<Sme>(`/smes/${id}`) });

export const useFit = (smeId: string, companyId: string, enabled = true) =>
  useQuery({
    queryKey: ["fit", smeId, companyId],
    queryFn: () => api<FitResult>(`/smes/${smeId}/fit/${companyId}`),
    enabled,
    retry: false,
  });

/** SME-safe Trust report (categories, weights, scores and reasons only). */
export const useTrustReport = (companyId: string, role?: string) =>
  useQuery({
    queryKey: ["trust-report", companyId, role ?? null],
    queryFn: () => api<TrustReport>(`/companies/${companyId}/trust-report${role ? `?role=${role}` : ""}`),
  });

export function useCreateSme() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: SmeIn) => api<Sme>("/smes", "POST", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["smes"] }),
  });
}

export function usePatchSme(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: SmePatch) => api<Sme>(`/smes/${id}`, "PATCH", body),
    onSuccess: (sme) => {
      qc.setQueryData(["sme", id], sme);
      qc.invalidateQueries({ queryKey: ["smes"] });
      qc.invalidateQueries({ queryKey: ["fit", id] });
      qc.invalidateQueries({ queryKey: ["bridge", id] });
      qc.invalidateQueries({ queryKey: ["readiness", id] });
    },
  });
}
