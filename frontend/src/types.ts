export type Lang = "en" | "te";

export const SOIL_KEYS = ["ph", "ec", "oc", "n", "p", "k", "zn", "b"] as const;
export type SoilKey = (typeof SOIL_KEYS)[number];
export type Soil = Record<SoilKey, number>;

export interface LastSeason {
  urea: number;
  dap: number;
  mop: number;
}

export interface PlanRequest {
  soil: Soil;
  crop: string;
  acres: number;
  season: string;
  last: LastSeason;
  lang: Lang;
}

export interface Change {
  label: string;
  action: "Reduce" | "Increase" | "Add" | "Keep";
  text: string;
}

export interface Plan {
  crop: string;
  headline: string;
  headline_detail: string | null;
  fertiliser_changes: number;
  ratings: Record<string, string>;
  buy: [string, string][];
  extra_buy: [string, string][];
  when: [string, string][];
  changes: Change[];
  fixes: string[];
  old_cost: number;
  new_cost: number;
  bags: Record<string, number>;
  kg: Record<string, number>;
  footer: string;
}

export interface ExtractResult {
  is_soil_health_card: boolean;
  values: Record<SoilKey, number | null>;
  missing: SoilKey[];
  warnings: string[];
  farm: { crop: string | null; season: string | null; acres: number | null };
}

export interface Citation {
  id: number;
  doc: string;
  title: string;
  page: number;
  url: string | null;
  snippet: string;
}

export interface Explanation {
  points: { text: string; sources: number[] }[];
  citations: Citation[];
  generated_by: "llm" | "rules";
  dropped_points: number;
}

export interface Sample extends Soil {
  desc: string;
  crop: string;
  season: string;
  acres: number;
  last_urea: number;
  last_dap: number;
  last_mop: number;
}

// The UI string table comes from the backend (engine.TEXT): one source of truth for both apps.
export type TextTable = Record<string, any>;

export interface Meta {
  crops: string[];
  seasons: string[];
  samples: Record<string, Sample>;
  text: Record<Lang, TextTable>;
}

export interface Health {
  status: string;
  ocr_enabled: boolean;
  llm_enabled: boolean;
  rag_chunks: number;
}
