"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Schemas } from "@/lib/api/client";
import type { GateStatus, Rubrics, TrustRun, WhatIf } from "@/lib/trust-types";

export type Company = Schemas["ViewerCompany"];
export type EvidenceRow = Schemas["EvidenceRow"];
export type EvidenceIn = Schemas["EvidenceIn"];
export type Flag = Schemas["FlagOut"];
export type FlagIn = Schemas["FlagIn"];
export type Trend = Schemas["TrendIn"];

const forever = { staleTime: Infinity } as const;

export const usePublicConfig = () =>
  useQuery({ queryKey: ["config", "public"], queryFn: () => api<Schemas["PublicConfig"]>("/config/public"), ...forever });

export const useRubrics = () =>
  useQuery({ queryKey: ["config", "rubrics"], queryFn: () => api<Rubrics>("/config/rubrics"), ...forever });

export const useCompanies = () =>
  useQuery({ queryKey: ["companies"], queryFn: () => api<Schemas["ViewerCompanyListItem"][]>("/companies") });

export const useCompany = (id: string) =>
  useQuery({ queryKey: ["company", id], queryFn: () => api<Company>(`/companies/${id}`) });

export const useEvidence = (id: string) =>
  useQuery({ queryKey: ["evidence", id], queryFn: () => api<EvidenceRow[]>(`/companies/${id}/evidence`) });

export const useFlags = (id: string) =>
  useQuery({ queryKey: ["flags", id], queryFn: () => api<Flag[]>(`/companies/${id}/flags`) });

export const useTrends = (id: string) =>
  useQuery({ queryKey: ["trends", id], queryFn: () => api<Record<string, Trend>>(`/companies/${id}/trends`) });

/** Scores through the API (every score is computed by the engine there); each call is saved as a run,
 * what-if runs are flagged and never shown to SMEs. */
export const useTrustScore = (id: string, role: string, whatIf?: WhatIf | null) =>
  useQuery({
    queryKey: ["trust", id, role, whatIf ?? null],
    queryFn: () =>
      api<TrustRun>(`/companies/${id}/trust-score`, "POST", whatIf ? { role, what_if: whatIf } : { role }),
    placeholderData: keepPreviousData,
    enabled: !!role,
  });

function useInvalidate(id: string) {
  const qc = useQueryClient();
  return (...keys: string[]) => {
    for (const k of keys) qc.invalidateQueries({ queryKey: [k, id] });
    qc.invalidateQueries({ queryKey: ["companies"] });
  };
}

export function usePutEvidence(id: string) {
  const invalidate = useInvalidate(id);
  return useMutation({
    mutationFn: ({ pid, body }: { pid: string; body: EvidenceIn }) =>
      api<EvidenceRow>(`/companies/${id}/evidence/${pid}`, "PUT", body),
    onSuccess: () => invalidate("evidence", "trust"),
  });
}

export function useAddFlag(id: string) {
  const invalidate = useInvalidate(id);
  return useMutation({
    mutationFn: (body: FlagIn) => api<Flag>(`/companies/${id}/flags`, "POST", body),
    onSuccess: () => invalidate("flags", "trust"),
  });
}

export function useDeleteFlag(id: string) {
  const invalidate = useInvalidate(id);
  return useMutation({
    mutationFn: (flagId: number) => api<void>(`/companies/${id}/flags/${flagId}`, "DELETE"),
    onSuccess: () => invalidate("flags", "trust"),
  });
}

export function useSetGates(id: string) {
  const invalidate = useInvalidate(id);
  return useMutation({
    mutationFn: (body: Record<string, GateStatus>) => api<Company>(`/companies/${id}/gates`, "PUT", body),
    onSuccess: () => invalidate("company", "trust"),
  });
}

export function useSetTrends(id: string) {
  const invalidate = useInvalidate(id);
  return useMutation({
    mutationFn: (body: Record<string, Trend>) => api<Record<string, Trend>>(`/companies/${id}/trends`, "PUT", body),
    onSuccess: () => invalidate("trends", "company", "trust"),
  });
}
