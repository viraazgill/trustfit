"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Schemas } from "@/lib/api/client";

export type BridgeConfig = Schemas["PublicBridgeConfig"];
export type Readiness = Schemas["ReadinessOut"];
export type ReadinessDimension = Schemas["ReadinessDimension"];
export type Bridge = Schemas["ViewerBridge"];
export type BridgeCompany = Schemas["BridgeCompany"];

export const useBridgeConfig = () =>
  useQuery({ queryKey: ["config", "bridge"], queryFn: () => api<BridgeConfig>("/config/bridge"), staleTime: Infinity });

export const useReadiness = (smeId: string) =>
  useQuery({ queryKey: ["readiness", smeId], queryFn: () => api<Readiness>(`/smes/${smeId}/readiness`) });

/** The full Gap Bridge, computed by the API's engine (each call is saved as a bridge run). */
export const useBridge = (smeId: string, enabled = true) =>
  useQuery({
    queryKey: ["bridge", smeId],
    queryFn: () => api<Bridge>(`/smes/${smeId}/bridge`, "POST"),
    enabled,
    retry: false,
  });

export function usePutReadiness(smeId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (answers: Record<string, number>) => api<Readiness>(`/smes/${smeId}/readiness`, "PUT", { answers }),
    onSuccess: (r) => {
      qc.setQueryData(["readiness", smeId], r);
      qc.invalidateQueries({ queryKey: ["bridge", smeId] });
      qc.invalidateQueries({ queryKey: ["sme", smeId] });
    },
  });
}
