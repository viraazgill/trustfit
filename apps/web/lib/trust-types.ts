/**
 * Shape of a Trust engine result (analyst view), mirroring `TrustResult` in
 * packages/trustfit_engine/trustfit_engine/models.py. The API returns it as a JSON object, so it is
 * typed here rather than generated.
 */
export type Verdict = "Green" | "Amber" | "Red";
export type GateStatus = "passed" | "pending" | "failed";
export type EvidenceStatus = "missing" | "unverified" | "stale" | "excluded" | "verified";

export interface Reason {
  code: string;
  text: string;
}

export interface Stats {
  label: string;
  points: number;
  verified_points: number;
  earned_points: number;
  verified_pct: number | null;
  score_pct: number | null;
}

export interface NextCheck {
  type: "parameter" | "gate";
  id: string;
  points?: number;
  status?: EvidenceStatus;
  check: string; // where_to_check: analyst only
}

export interface TrustResult {
  company_id: string;
  role: string;
  as_of: string;
  weight_set: string;
  what_if: boolean;
  eligible: boolean;
  status: "scored" | "insufficient_data" | "not_eligible";
  score: number | null;
  band: string | null;
  confidence: number | null;
  provisional: boolean | null;
  verdict: Verdict;
  outlook: string | null;
  reasons: Reason[];
  knockouts?: Reason[];
  score_raw?: number;
  base_score?: number;
  notches?: number;
  notch_list?: { code: string; points: number }[];
  weakest_dimension?: number;
  weakest_limit?: number;
  cap?: number | null;
  cap_list?: { code: string; max_score: number }[];
  binding_limit?: "score" | "weakest_link" | "cap";
  categories?: Record<string, Stats>;
  dimensions?: Record<string, Stats>;
  gates?: Record<string, GateStatus>;
  parameters?: Record<string, { status: EvidenceStatus; level: number | null; points: number }>;
  next_checks?: NextCheck[];
}

export interface TrustRun {
  run_id: number;
  is_what_if: boolean;
  result: TrustResult;
}

export interface WhatIf {
  evidence: Record<string, number>;
  gates: Record<string, GateStatus>;
}

/** GET /config/rubrics (analyst/admin only: confidential). */
export interface Rubrics {
  version: string;
  parameter_splits: Record<string, Record<string, number>>;
  parameters: Record<
    string,
    {
      category: string;
      name: string;
      tier: string;
      recheck_days: number | null;
      knockout_at_zero: boolean;
      note: string | null;
      rubric: Record<string, string>;
      where_to_check: string;
    }
  >;
  overrides: {
    knockouts: Record<string, { label: string; check: string }>;
    caps: Record<string, { label: string; max_score: number; check: string }>;
    fake_reviews: { label: string; effect: string; check: string };
    notches: Record<string, { label: string; points: number; check: string }>;
    notch_total_limit: number;
    weakest_link_margin: number;
  };
  gates: Record<string, { label: string; check: string }>;
  freshness: { max_source_age_days: number };
}
