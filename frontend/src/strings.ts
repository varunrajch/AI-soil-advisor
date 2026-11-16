import type { Lang } from "./types";

// Strings only the web app needs. Everything else comes from the backend's engine.TEXT.
export const WEB_TEXT: Record<Lang, Record<string, string>> = {
  en: {
    why: "Why this plan?",
    explaining: "Explaining…",
    sources: "Sources",
    page: "page",
    by_llm: "Explained by AI from the plan and the guideline sources. Quantities always come from the rules.",
    by_rules: "Explained from the soil rules, with guideline sources.",
    making: "Making plan…",
    preparing_audio: "Preparing audio…",
    other_none: "Pick a crop to compare",
    upload_hint: "Photo of a Soil Health Card, JPG or PNG",
    choose_file: "Choose photo",
    fill_all: "Fill every soil value first.",
    api_down: "Cannot reach the server. Is the backend running on port 8000?",
    cost_unchanged: "Same cost",
  },
  te: {
    why: "ఈ ప్లాన్ ఎందుకు?",
    explaining: "వివరిస్తున్నాం…",
    sources: "ఆధారాలు",
    page: "పేజీ",
    by_llm: "ప్లాన్, మార్గదర్శక పత్రాల ఆధారంగా AI వివరణ. మోతాదులు ఎప్పుడూ నియమాల నుండే.",
    by_rules: "నేల నియమాల ఆధారంగా వివరణ, మార్గదర్శక పత్రాలతో.",
    making: "ప్లాన్ తయారవుతోంది…",
    preparing_audio: "ఆడియో సిద్ధమవుతోంది…",
    other_none: "పోల్చడానికి పంట ఎంచుకోండి",
    upload_hint: "నేల ఆరోగ్య కార్డు ఫోటో, JPG లేదా PNG",
    choose_file: "ఫోటో ఎంచుకోండి",
    fill_all: "ముందుగా అన్ని నేల విలువలు నింపండి.",
    api_down: "సర్వర్ అందుబాటులో లేదు. బ్యాక్‌ఎండ్ పోర్ట్ 8000 పై నడుస్తోందా?",
    cost_unchanged: "అదే ఖర్చు",
  },
};

export const SOIL_LABELS: Record<string, string> = {
  ph: "pH", ec: "EC (dS/m)", oc: "OC (%)", n: "N (kg/ha)",
  p: "P (kg/ha)", k: "K (kg/ha)", zn: "Zn (ppm)", b: "B (ppm)",
};

export const rupees = (x: number) => "₹" + Math.round(x).toLocaleString("en-IN");
