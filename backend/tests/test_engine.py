"""Rule engine: every quantity the farmer sees is computed here."""
import pytest

import engine
from backend.tests.conftest import SOIL_KEYS

LAST_A = {"urea": 3, "dap": 2, "mop": 0}


def soil_of(name):
    return {k: engine.SAMPLES[name][k] for k in SOIL_KEYS}


@pytest.mark.parametrize("key,value,expected", [
    ("n", 279.9, "Low"), ("n", 280, "Medium"), ("n", 560, "Medium"), ("n", 560.1, "High"),
    ("p", 9.9, "Low"), ("p", 25, "Medium"), ("p", 25.1, "High"),
    ("k", 109, "Low"), ("k", 281, "High"),
    ("oc", 0.49, "Low"), ("oc", 0.75, "Medium"), ("oc", 0.76, "High"),
])
def test_rating_boundaries(key, value, expected):
    assert engine.rate(key, value) == expected


def test_sample_a_paddy_doses():
    plan = engine.make_plan(soil_of("Sample A"), "Paddy", 1, LAST_A, "en")
    # P high -> 60 * 0.75 * 0.4047 ha = 18.2 kg P2O5 -> /0.46 = 39.6 kg DAP
    assert plan["kg"]["dap"] == pytest.approx(39.6, abs=0.1)
    # N low -> 120 * 1.25 * 0.4047 = 60.7 kg N, minus DAP N (7.1) -> /0.46 = 116.5 kg urea
    assert plan["kg"]["urea"] == pytest.approx(116.5, abs=0.2)
    assert plan["kg"]["mop"] == pytest.approx(27.0, abs=0.1)
    assert plan["bags"] == {"urea": 2.5, "dap": 1.0, "mop": 0.5}
    # 3 fertiliser changes + zinc sulphate
    assert plan["headline"] == "This season, change 4 things"
    assert plan["headline_detail"] == "3 fertiliser change(s), plus Zinc sulphate"
    assert plan["old_cost"] == pytest.approx(3 * 266.5 + 2 * 1350)
    assert plan["new_cost"] == pytest.approx(2.5 * 266.5 + 1350 + 0.5 * 1700)


def test_sample_a_change_lines_match_spec_example():
    plan = engine.make_plan(soil_of("Sample A"), "Paddy", 1, LAST_A, "en")
    dap = [c for c in plan["changes"] if c[2].startswith("DAP")][0]
    assert dap[1] == "Reduce"
    assert dap[2] == "DAP: 2 bags → about 1 bag. Your soil already has high phosphorus."


def test_sample_b_groundnut_fixes():
    s = engine.SAMPLES["Sample B"]
    plan = engine.make_plan(soil_of("Sample B"), "Groundnut", 2,
                            {"urea": s["last_urea"], "dap": s["last_dap"], "mop": s["last_mop"]}, "en")
    # urea and MOP change (DAP 2 -> 2 is Keep), plus zinc sulphate, borax and gypsum
    assert plan["fertiliser_changes"] == 2
    assert plan["headline"] == "This season, change 5 things"
    assert plan["headline_detail"] == "2 fertiliser change(s), plus Zinc sulphate, Borax, Gypsum"
    extra = dict(plan["extra_buy"])
    assert extra["Gypsum"] == "400 kg"          # 200 kg/acre x 2 acres
    assert extra["Zinc sulphate"] == "40 kg"    # Zn 0.5 < 0.6
    assert extra["Borax"] == "8 kg"             # B 0.3 < 0.5
    assert any("agricultural lime" in f for f in plan["fixes"])  # pH 6.2 < 6.5
    assert any("fixes its own nitrogen" in f for f in plan["fixes"])


def test_keep_within_ten_percent():
    plan = engine.make_plan(soil_of("Sample A"), "Paddy", 1, {"urea": 2.5, "dap": 1, "mop": 0.5}, "en")
    assert [c[1] for c in plan["changes"]] == ["Keep", "Keep", "Keep"]
    assert plan["headline"] == "This season, change 1 thing"  # only the zinc sulphate
    assert plan["headline_detail"] == "Same fertiliser as last season, plus Zinc sulphate"


def test_nothing_to_change():
    soil = dict(soil_of("Sample A"), zn=1.0, oc=0.8)  # no zinc or manure needed
    plan = engine.make_plan(soil, "Paddy", 1, {"urea": 2.5, "dap": 1, "mop": 0.5}, "en")
    assert plan["headline"] == "This season, keep the same fertiliser"
    assert plan["headline_detail"] is None


@pytest.mark.parametrize("crop", list(engine.BASE_DOSE))
@pytest.mark.parametrize("lang", ["en", "te"])
def test_every_crop_builds_in_both_languages(crop, lang):
    plan = engine.make_plan(soil_of("Sample B"), crop, 1.5, LAST_A, lang)
    assert plan["when"] and all(stage and what for stage, what in plan["when"])
    assert len(plan["buy"]) == 3
    assert engine.speech_text(plan, lang)


def test_text_tables_have_same_keys():
    assert set(engine.TEXT["en"]) == set(engine.TEXT["te"])
    assert set(engine.TEXT["en"]["crops"]) == set(engine.BASE_DOSE) == set(engine.SCHEDULE)


def test_telugu_speech_is_listenable():
    plan = engine.make_plan(soil_of("Sample A"), "Paddy", 1, LAST_A, "te")
    text = engine.speech_text(plan, "te")
    assert "రెండున్నర" in text and "రూపాయలు" in text and "ఆదా" in text
    for symbol in ("½", "⅓", "→", "కిలోలు)"):
        assert symbol not in text
    # changes, extra purchases and money only: no buy list, schedule, soil-fix advice or reasons
    assert "అదనంగా కొనండి: జింక్ సల్ఫేట్ 20 కిలోలు" in text
    for section in ("ఏమి కొనాలి", "ఎప్పుడు వేయాలి", "నేల సవరణలు", "నేలలో", "పశువుల ఎరువు"):
        assert section not in text


def test_english_speech_is_short():
    plan = engine.make_plan(soil_of("Sample A"), "Paddy", 1, LAST_A, "en")
    assert engine.speech_text(plan, "en") == (
        "This season, change 4 things. "
        "Urea: Reduce. Last season 3 bags, now about 2 and a half bags. "
        "DAP: Reduce. Last season 2 bags, now about 1 bag. "
        "MOP: Add (was zero). Last season 0 bags, now about half a bag. "
        "Also buy: Zinc sulphate 20 kg. "
        "Cost. Last season you spent 3500 rupees. This season it is 2866 rupees. "
        "You save 633 rupees.")
