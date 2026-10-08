export interface Dataset {
  dataset_id: string;
  first_date: string;
  last_date: string;
  stock_count: number;
  row_count: number;
  fingerprint: string;
  quarantined_count: number;
  retrieved_at: string;
  crosscheck: {
    status: string;
    date?: string;
    matched?: number;
    matches?: unknown[];
  };
}
export interface RunSummary {
  run_id: string;
  kind: string;
  created_at: string;
  dataset_id: string;
  as_of?: string;
  n?: number;
  k?: number;
  seed?: number;
  methods: string[];
  feasible_methods: string[];
  cancelled: boolean;
}
export interface Method {
  method: string;
  status: string;
  objective?: number | null;
  objective_gap?: number | null;
  selection_feasible?: boolean;
  allocation_feasible?: boolean;
  feasible_fraction?: number | null;
  total_seconds?: number;
  seconds?: number;
  evaluations?: number;
  shots_used?: number;
  num_qubits?: number;
  error?: string;
  decision?: string;
  allocation?: { weights?: number[]; status?: string; violations?: string[] };
  pilots?: Method[];
  metadata?: {
    chosen_config?: string;
    result_source?: string;
    ranker_suggestion?: string | null;
    [key: string]: unknown;
  };
  trace?: {
    feasible_fraction: number;
    config: string;
    [key: string]: unknown;
  }[];
  [key: string]: unknown;
}
export interface Run {
  run_id: string;
  kind: string;
  created_at: string;
  dataset_fingerprint: string;
  cancelled: boolean;
  config: Record<string, unknown>;
  results: Method[];
  instance: {
    symbols: string[];
    sectors: string[];
    k: number;
    as_of: string;
    dataset_id: string;
    features: Record<string, number>;
  };
  budget: Record<string, unknown>;
  preparation: {
    eligible_count: number;
    return_observations: number;
    estimation_start: string;
    estimation_end: string;
    excluded: { symbol: string; reason: string }[];
    [key: string]: unknown;
  };
  software: Record<string, unknown>;
  limitations: string[];
  context_ranker?: unknown;
  allocation_references?: Record<string, unknown>;
  [key: string]: unknown;
}
export interface Job {
  id: string;
  status: string;
  created: string;
  updated: string;
  cancel_requested: number | boolean;
  config: Record<string, unknown>;
  error?: string | null;
  result_id?: string | null;
}
export interface JobDetail {
  job: Job;
  events: { id: number; time: string; message: string }[];
}
export interface Listing<T> {
  warnings: string[];
  [key: string]: T[] | string[];
}
export interface Audit {
  manifest: Record<string, unknown> & Dataset;
  constituents: {
    symbol: string;
    company?: string;
    name?: string;
    sector: string;
    isin: string;
  }[];
  quarantine: Record<string, unknown>[];
}
