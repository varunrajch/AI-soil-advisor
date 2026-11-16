"""LLM explanation and its guardrails."""
from backend.app.explain import action_errors, allowed_numbers, explain_plan, guard_points
from backend.app.schemas import ExplainPoint
from backend.tests.conftest import SOIL_KEYS, fake_llm

import engine

SOIL = {k: engine.SAMPLES["Sample A"][k] for k in SOIL_KEYS}
LAST = {"urea": 3, "dap": 2, "mop": 0}


def run(llm, lang="en", index=None, embedder=None):
    return explain_plan(SOIL, "Paddy", 1, LAST, lang, index, embedder, llm)


def test_guard_drops_invented_numbers_and_products():
    plan = engine.make_plan(SOIL, "Paddy", 1, LAST, "en")
    allowed = allowed_numbers(plan, SOIL, 1, [])
    points = [
        ExplainPoint(text="Apply 20 kg zinc sulphate because zinc is low.", sources=[1, 9]),
        ExplainPoint(text="Apply 75 kg urea now.", sources=[]),                 # 75 is not in the plan
        ExplainPoint(text="Use SSP instead of DAP.", sources=[]),              # product not in the plan
    ]
    kept = guard_points(points, allowed, n_sources=2, plan_text=str(plan))
    assert [p.text for p in kept] == ["Apply 20 kg zinc sulphate because zinc is low."]
    assert kept[0].sources == [1]  # source 9 does not exist


def test_llm_points_are_returned_with_citations(small_index, embedder):
    llm = fake_llm([{"text": "Zinc is low at 0.4, so apply 20 kg zinc sulphate [1].", "sources": [1]}])
    result = run(llm, index=small_index, embedder=embedder)
    assert result.generated_by == "llm"
    assert result.points[0].sources == [1]
    assert result.citations and result.citations[0].id == 1
    system = llm.messages[0]["content"]
    assert "Urea, DAP, MOP" in system and "Never name any other fertiliser" in system


def test_falls_back_to_rules_when_every_point_is_unsafe():
    result = run(fake_llm([{"text": "Apply 999 kg urea.", "sources": []}]))
    assert result.generated_by == "rules"
    assert any("zinc" in p.text.lower() for p in result.points)


def test_falls_back_to_rules_when_llm_errors():
    def broken(messages):
        raise RuntimeError("rate limited")
    assert run(broken).generated_by == "rules"


def test_telugu_uses_llm_with_glossary(monkeypatch):
    monkeypatch.delenv("LLM_TELUGU", raising=False)
    llm = fake_llm([{"text": "జింక్ తక్కువ, అందుకే 20 కిలోలు జింక్ సల్ఫేట్.", "sources": []}])
    result = run(llm, lang="te")
    assert result.generated_by == "llm"
    system = llm.messages[0]["content"]
    assert "నేల" in system and "alkaline" in system and "క్షార" in system  # Sample A pH 8.2


def test_telugu_can_be_switched_back_to_templates(monkeypatch):
    monkeypatch.setenv("LLM_TELUGU", "0")
    llm = fake_llm([{"text": "anything", "sources": []}])
    result = run(llm, lang="te")
    assert result.generated_by == "rules"
    assert not hasattr(llm, "messages")  # the LLM was never called


def test_fact_guard_catches_past_telugu_mistakes():
    points = [
        ExplainPoint(text="pH 8.2 ఉన్న ఆమ్ల నేల.", sources=[]),                    # alkaline soil called acidic
        ExplainPoint(text="నీటి పరీక్షలో భాస్వరం తక్కువ.", sources=[]),               # "water test"
        ExplainPoint(text="నత్రజని 210 ppm, తక్కువగా ఉంది.", sources=[]),             # N in ppm
        ExplainPoint(text="జింక్ 0.4 ppm తక్కువ, pH 8.2 క్షార నేల.", sources=[]),      # correct
    ]
    allowed = {"8.2", "210", "0.4"}
    kept = guard_points(points, allowed, n_sources=0, soil=SOIL)
    assert [p.text for p in kept] == ["జింక్ 0.4 ppm తక్కువ, pH 8.2 క్షార నేల."]


def test_fact_guard_in_english():
    points = [ExplainPoint(text="Your soil is acidic at pH 8.2.", sources=[]),
              ExplainPoint(text="DAP is kept since phosphorus is low (8 mg kg⁻¹).", sources=[]),
              ExplainPoint(text="Potassium is low (95 mg/kg).", sources=[])]
    assert guard_points(points, {"8.2", "8", "95"}, n_sources=0, soil=SOIL) == []


def test_unit_guard_allows_micronutrient_ppm_next_to_npk():
    text = "Phosphorus is high at 28 kg/ha, and zinc is low at 0.4 mg/kg."
    assert guard_points([ExplainPoint(text=text, sources=[])], {"28", "0.4"}, n_sources=0, soil=SOIL)


def test_works_without_an_index():
    result = run(None)
    assert result.citations == [] and result.points


def test_action_guard_catches_wrong_change():
    actions = {"urea": "Reduce", "dap": "Keep", "mop": "Add"}
    assert action_errors("డీఏపీ పెంచాం: భాస్వరం తక్కువ.", actions)          # DAP is Keep, not increase
    assert action_errors("Increase urea to 3 bags.", actions)
    assert not action_errors("యూరియా తగ్గించాం, ఎందుకంటే గత సీజన్ ఎక్కువ.", actions)
    assert not action_errors("పొటాష్ పెంచాం, ఎందుకంటే పొటాష్ తక్కువ.", actions)  # Add counts as an increase
    assert not action_errors("Reduce urea; add MOP.", actions)               # each clause checked separately
    assert not action_errors("Urea is reduced because the old 3-bag dose was more than the crop needs.", actions)
