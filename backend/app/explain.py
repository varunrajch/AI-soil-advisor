"""Explain a plan in plain words, grounded in guideline passages.

The LLM only explains. Every quantity comes from the rule engine, and a numeric guardrail
drops any sentence that mentions a number not present in the plan, the soil card or the sources.
"""
import json
import logging
import os
import re
import time
from typing import Callable, Dict, List, Optional, Set

import engine

from .logging_setup import log
from .rag.retriever import plan_queries, retrieve
from .schemas import Citation, ExplainPoint, ExplainResponse

logger = logging.getLogger("nela.explain")

LLM = Callable[[List[Dict[str, str]]], str]

LANG_NAME = {"en": "simple English", "te": "simple spoken Telugu (use Telugu script)"}

SYSTEM_PROMPT = """You explain a fertiliser plan to a small farmer in Andhra Pradesh.
Rules:
- The plan's quantities are final. Never change them and never introduce a new quantity, dose or price.
- Only mention these products, with exactly these names: {products}. Never name any other fertiliser.
- "Reduce", "Increase" and "Add" compare this season's bags with LAST season's bags. Each change line already
  states its reason from the soil test; use that reason and do not invent a different one.
- Explain WHY the main changes and soil fixes are needed, using the numbered sources when they support it.
- Cite sources inline like [1]. Only cite a source that directly supports the sentence. If none does,
  explain from the soil card values and cite nothing.
- Units: N, P and K are kg/ha. Zn and B are ppm. OC is %. Never give N, P or K in ppm or mg/kg.
- Write 3 to 5 short points, one or two sentences each, in {lang}.
Reply with JSON only: {{"points": [{{"text": "...", "sources": [1]}}]}}"""

# Fertilisers the LLM must not bring in unless the plan itself uses them.
OTHER_PRODUCTS = [
    "ssp", "super phosphate", "superphosphate", "ammonium sulphate", "ammonium sulfate", "complex",
    "npk", "17:17:17", "20:20", "10:26:26", "28:28", "calcium ammonium nitrate", " sop ",
    "potassium sulphate", "potassium sulfate", "potassium chloride", "ammonium phosphate",
    "ఎస్ఎస్పీ", "ఎస్.ఎస్.పి", "సూపర్ ఫాస్ఫేట్", "సూపర్‌ఫాస్ఫేట్", "కాంప్లెక్స్", "అమ్మోనియం",
]

# Fallback explanations when no LLM is available. {sources} is filled with citation markers.
RULE_TEXT = {
    "en": {
        "dose": "These amounts come from your soil test: nitrogen is {n}, phosphorus is {p}, potassium is {k}. "
                "Dosing by soil test avoids paying for fertiliser your soil does not need.",
        "phosphorus": "Your soil already has high phosphorus, so less DAP is needed this season. "
                      "Extra phosphorus stays in the soil and is wasted money.",
        "zinc": "Zinc is low (Zn {zn} ppm). Zinc shortage stunts the crop and lowers yield, so zinc sulphate is added.",
        "gypsum": "Groundnut needs calcium for pod filling, which is why gypsum is applied at flowering.",
        "organic": "Organic carbon is low ({oc}%), so farmyard manure is advised to build soil health.",
        "ph": "Soil pH is {ph}, which affects how well the crop can take up nutrients.",
    },
    "te": {
        "dose": "ఈ మోతాదులు మీ నేల పరీక్ష ఆధారంగా: నత్రజని {n}, భాస్వరం {p}, పొటాష్ {k}. "
                "నేల పరీక్ష ప్రకారం వేస్తే, అవసరం లేని ఎరువు మీద డబ్బు వృథా కాదు.",
        "phosphorus": "మీ నేలలో భాస్వరం ఇప్పటికే ఎక్కువగా ఉంది, కాబట్టి ఈ సీజన్ డీఏపీ తక్కువ చాలు. "
                      "అదనపు భాస్వరం నేలలోనే ఉండిపోతుంది, ఆ డబ్బు వృథా.",
        "zinc": "జింక్ తక్కువగా ఉంది (Zn {zn} ppm). జింక్ లోపం వల్ల పంట ఎదుగుదల, దిగుబడి తగ్గుతాయి, అందుకే జింక్ సల్ఫేట్.",
        "gypsum": "వేరుశనగ కాయలు నిండాలంటే కాల్షియం కావాలి, అందుకే పూత దశలో జిప్సం వేయాలి.",
        "organic": "సేంద్రియ కర్బనం తక్కువ ({oc}%), నేల ఆరోగ్యం కోసం పశువుల ఎరువు వేయండి.",
        "ph": "నేల pH {ph}. ఇది పంట పోషకాలు తీసుకునే శక్తిని ప్రభావితం చేస్తుంది; క్షార నేలలో జింక్ అందదు.",
    },
}
RATING_TE = {"Low": "తక్కువ", "Medium": "మధ్యస్థం", "High": "ఎక్కువ"}

NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


def _numbers(text: str) -> Set[str]:
    text = re.sub(r"\[\d+\]", "", text)  # citation markers are not quantities
    return {n.replace(",", "").rstrip("0").rstrip(".") if "." in n else n.replace(",", "")
            for n in NUMBER.findall(text)}


def allowed_numbers(plan: dict, soil: Dict[str, float], acres: float, citations: List[Citation]) -> Set[str]:
    parts = [plan["headline"], *plan["fixes"], *(c[2] for c in plan["changes"])]
    parts += [f"{a} {b}" for a, b in plan["buy"] + plan["extra_buy"] + plan["when"]]
    parts += [f"{v:g}" for v in soil.values()]
    parts += [f"{acres:g}", f"{plan['old_cost']:.0f}", f"{plan['new_cost']:.0f}",
              f"{abs(plan['new_cost'] - plan['old_cost']):.0f}"]
    parts += [c.snippet for c in citations]
    return set().union(*(_numbers(p) for p in parts))


def foreign_products(text: str, plan_text: str) -> List[str]:
    low, plan_low = f" {text.lower()} ", f" {plan_text.lower()} "
    return [w.strip() for w in OTHER_PRODUCTS if w in low and w not in plan_low]


def ph_word(ph: float) -> str:
    return "alkaline" if ph > 7.5 else "acidic" if ph < 6.5 else "neutral"


# Telugu terms the LLM must use. Each mistake below was seen in testing before this glossary existed.
TE_GLOSSARY = """Telugu wording rules (follow exactly):
- soil = నేల, soil test = నేల పరీక్ష. Never write నీరు or నీటి (water) for soil.
- nitrogen = నత్రజని, phosphorus = భాస్వరం, potassium = పొటాష్, zinc = జింక్, boron = బోరాన్,
  organic carbon = సేంద్రియ కర్బనం, bags = బస్తాలు, farmyard manure = పశువుల ఎరువు.
- alkaline = క్షార, acidic = ఆమ్ల. This soil's pH is {ph}, so it is {ph_word} ({ph_te}).
- N, P and K values are kg per hectare. Never write ppm for N, P or K. Only Zn and B are in ppm.
- Ratings in Telugu: Low = తక్కువ, Medium = మధ్యస్థం, High = ఎక్కువ. Do not write Low/Medium/High in English.
- reduce = తగ్గించండి, increase = పెంచండి, keep the same = అలాగే ఉంచండి, pods = కాయలు."""

PH_TE = {"alkaline": "క్షార నేల", "acidic": "ఆమ్ల నేల", "neutral": "తటస్థ నేల"}
MACRO_WORDS = ["nitrogen", "phosphorus", "potassium", "నత్రజని", "నైట్రోజన్", "భాస్వరం", "ఫాస్ఫరస్", "పొటాష్"]
MICRO_WORDS = ["zinc", "boron", "జింక్", "బోరాన్", "zn", " b "]


ACTION_VERBS = {
    "Reduce": ["reduce", "cut ", "తగ్గించ", "తగ్గింప"],
    "Increase": ["increase", "raise", "పెంచ"],
}
PRODUCT_NAMES = {"urea": ["urea", "యూరియా"], "dap": ["dap", "డీఏపీ"], "mop": ["mop", "potash", "పొటాష్"]}


def action_errors(text: str, actions: Dict[str, str]) -> List[str]:
    """A clause naming one fertiliser must not claim a different change than the plan made."""
    errors = []
    for clause in re.split(r"[.;:!?।]", text.lower()):
        named = [f for f, names in PRODUCT_NAMES.items() if any(n in clause for n in names)]
        if len(named) != 1:  # ambiguous or no product: nothing to check
            continue
        f = named[0]
        for action, verbs in ACTION_VERBS.items():
            if any(v in clause for v in verbs) and actions.get(f) not in (action, "Add" if action == "Increase" else None):
                errors.append(f"says {action.lower()} {f}, plan says {actions.get(f, '?').lower()}")
    return errors


def fact_errors(text: str, soil: Dict[str, float]) -> List[str]:
    """Soil facts the explanation must not contradict, in English and Telugu."""
    low = f" {text.lower()} "
    errors = []
    kind = ph_word(soil["ph"])
    if kind == "alkaline" and ("acidic" in low or "ఆమ్ల" in low):
        errors.append("calls alkaline soil acidic")
    if kind == "acidic" and ("alkaline" in low or "క్షార" in low):
        errors.append("calls acidic soil alkaline")
    if "నీటి" in low or "నీరు" in low:
        errors.append("says water instead of soil")
    for clause in re.split(r"[.;,]", low):
        wrong_unit = "ppm" in clause or re.search(r"mg\s*(/|per\s*)?\s*kg", clause)
        if wrong_unit and any(w in clause for w in MACRO_WORDS) and not any(w in clause for w in MICRO_WORDS):
            errors.append("gives N/P/K in ppm or mg/kg")
            break
    return errors


def guard_points(points: List[ExplainPoint], allowed: Set[str], n_sources: int,
                 plan_text: str = "", soil: Optional[Dict[str, float]] = None,
                 actions: Optional[Dict[str, str]] = None) -> List[ExplainPoint]:
    """Keep only points whose numbers are all known, that name no product outside the plan,
    and that do not contradict the soil card."""
    kept = []
    for p in points:
        unknown = _numbers(p.text) - allowed
        products = foreign_products(p.text, plan_text)
        facts = (fact_errors(p.text, soil) if soil else []) + (action_errors(p.text, actions) if actions else [])
        if unknown or products or facts:
            log(logger, logging.WARNING, "explain.dropped_point",
                unknown_numbers=sorted(unknown), foreign_products=products, fact_errors=facts)
            continue
        kept.append(ExplainPoint(text=p.text, sources=[s for s in p.sources if 1 <= s <= n_sources]))
    return kept


def parse_llm_json(text: str) -> List[ExplainPoint]:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    text = re.sub(r"```(?:json)?", "", text).strip()
    match = re.search(r"\{.*\}", text, flags=re.S)
    data = json.loads(match.group(0) if match else text)
    points = []
    for p in data.get("points", []):
        if isinstance(p, dict) and str(p.get("text", "")).strip():
            sources = [int(s) for s in p.get("sources", []) if str(s).isdigit()]
            points.append(ExplainPoint(text=str(p["text"]).strip(), sources=sources))
    return points


def rule_points(topics: List[str], soil, ratings, lang, topic_sources) -> List[ExplainPoint]:
    t = RULE_TEXT[lang]
    tr = (lambda r: RATING_TE[r]) if lang == "te" else (lambda r: r.lower())
    fields = dict(n=tr(ratings["n"]), p=tr(ratings["p"]), k=tr(ratings["k"]),
                  zn=f"{soil['zn']:g}", oc=f"{soil['oc']:g}", ph=f"{soil['ph']:g}")
    return [ExplainPoint(text=t[topic].format(**fields), sources=topic_sources.get(topic, []))
            for topic in topics]


def groq_llm(api_key: str, model: str) -> LLM:
    def call(messages):
        from groq import Groq

        resp = Groq(api_key=api_key).chat.completions.create(
            model=model, messages=messages, temperature=0.2,
            response_format={"type": "json_object"})
        return resp.choices[0].message.content
    return call


def plan_actions(plan: dict) -> Dict[str, str]:
    """{"urea": "Reduce", "dap": "Keep", "mop": "Add"} from the plan's change list (urea, DAP, MOP order)."""
    return dict(zip(("urea", "dap", "mop"), (c[1] for c in plan["changes"])))


def explain_plan(soil: Dict[str, float], crop: str, acres: float, last: Dict[str, float], lang: str,
                 index, embedder, llm: Optional[LLM]) -> ExplainResponse:
    plan = engine.make_plan(soil, crop, acres, last, lang)
    ratings = plan["ratings"]
    queries = plan_queries(soil, crop, ratings)
    hits = retrieve(index, embedder, queries) if index is not None else []

    citations, topic_sources = [], {}
    for i, (topic, chunk, _score) in enumerate(hits, start=1):
        citations.append(Citation(id=i, doc=chunk.doc, title=chunk.title, page=chunk.page,
                                  url=chunk.url, snippet=chunk.text[:500]))
        topic_sources.setdefault(topic, []).append(i)
    topics = [topic for topic, _ in queries]

    # Telugu goes through the LLM too, held to the glossary and fact guard.
    # LLM_TELUGU=0 switches Telugu back to the vetted templates.
    if lang == "te" and os.environ.get("LLM_TELUGU") == "0":
        llm = None

    if llm is not None:
        t = engine.TEXT[lang]
        products = ", ".join([t["urea"], t["dap"], t["mop"]] + [name for name, _ in plan["extra_buy"]]
                             + ([t["fym"]] if ratings["oc"] == "Low" else []))
        plan_text = json.dumps(plan, ensure_ascii=False, default=str)
        sources_block = "\n\n".join(f"[{c.id}] {c.title}, page {c.page}:\n{c.snippet}" for c in citations)
        plan_block = json.dumps({k: plan[k] for k in ("headline", "buy", "extra_buy", "when", "fixes")}
                                | {"changes": [c[2] for c in plan["changes"]]}, ensure_ascii=False)
        system = SYSTEM_PROMPT.format(lang=LANG_NAME[lang], products=products)
        if lang == "te":
            kind = ph_word(soil["ph"])
            system += "\n\n" + TE_GLOSSARY.format(ph=f"{soil['ph']:g}", ph_word=kind, ph_te=PH_TE[kind])
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Crop: {crop}. Soil card: {json.dumps(soil)}. Ratings: {json.dumps(ratings)}."
                                        f"\n\nPlan:\n{plan_block}\n\nSources:\n{sources_block or '(none)'}"},
        ]
        start = time.perf_counter()
        try:
            raw_points = parse_llm_json(llm(messages))
            points = guard_points(raw_points, allowed_numbers(plan, soil, acres, citations),
                                  len(citations), plan_text, soil, plan_actions(plan))
            log(logger, logging.INFO, "explain.llm", ms=round((time.perf_counter() - start) * 1000),
                points=len(raw_points), kept=len(points), citations=len(citations))
            if points:
                return ExplainResponse(points=points, citations=citations, generated_by="llm",
                                       dropped_points=len(raw_points) - len(points))
        except Exception as e:
            log(logger, logging.WARNING, "explain.llm_failed", error=str(e)[:300])

    points = rule_points(topics, soil, ratings, lang, topic_sources)
    return ExplainResponse(points=points, citations=citations, generated_by="rules")
