"""HTTP contract of every endpoint."""
from backend.app import main, tts
from backend.app.config import Settings
from backend.tests.conftest import fake_reader, png_bytes, sample_request


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and body["ocr_enabled"] and body["rag_chunks"] == 4


def test_request_id_header(client):
    r = client.get("/api/health", headers={"x-request-id": "abc123"})
    assert r.headers["x-request-id"] == "abc123"


def test_meta_lists_crops_and_both_languages(client):
    body = client.get("/api/meta").json()
    assert "Paddy" in body["crops"] and "Redgram" in body["crops"]
    assert set(body["text"]) == {"en", "te"}
    assert "Sample A" in body["samples"]


def test_plan(client):
    r = client.post("/api/plan", json=sample_request())
    assert r.status_code == 200
    body = r.json()
    assert body["headline"] == "This season, change 4 things"
    assert body["headline_detail"] == "3 fertiliser change(s), plus Zinc sulphate"
    assert body["fertiliser_changes"] == 3
    assert body["bags"] == {"urea": 2.5, "dap": 1.0, "mop": 0.5}
    assert body["changes"][1]["action"] == "Reduce"
    assert "ANGRAU" in body["footer"]


def test_plan_in_telugu(client):
    body = client.post("/api/plan", json=sample_request(lang="te")).json()
    assert "మార్పులు" in body["headline"]


def test_plan_rejects_unknown_crop(client):
    r = client.post("/api/plan", json=sample_request(crop="Wheat"))
    assert r.status_code == 422 and "unknown crop" in r.text


def test_plan_rejects_impossible_soil(client):
    req = sample_request()
    req["soil"]["ph"] = 15
    assert client.post("/api/plan", json=req).status_code == 422


def test_extract(client):
    r = client.post("/api/extract", files={"file": ("card.png", png_bytes(), "image/png")})
    assert r.status_code == 200
    body = r.json()
    assert body["is_soil_health_card"] and body["values"]["ph"] == 8.2 and body["missing"] == []


def test_extract_rejects_non_image(client):
    r = client.post("/api/extract", files={"file": ("x.txt", b"hello", "text/plain")})
    assert r.status_code == 400


def test_extract_without_key_is_503(client):
    main.app.dependency_overrides[main.get_settings] = lambda: Settings(groq_api_key=None)
    r = client.post("/api/extract", files={"file": ("card.png", png_bytes(), "image/png")})
    assert r.status_code == 503


def test_extract_upstream_failure_is_502(client):
    def broken(data, key):
        raise RuntimeError("groq down")
    main.app.dependency_overrides[main.get_card_reader] = lambda: broken
    r = client.post("/api/extract", files={"file": ("card.png", png_bytes(), "image/png")})
    assert r.status_code == 502


def test_extract_rate_limit_is_429(client):
    class RateLimitError(Exception):
        pass

    def limited(data, key):
        raise RateLimitError("429 output tokens per minute")
    main.app.dependency_overrides[main.get_card_reader] = lambda: limited
    r = client.post("/api/extract", files={"file": ("card.png", png_bytes(), "image/png")})
    assert r.status_code == 429 and "wait a minute" in r.json()["detail"]


def test_extract_non_card(client):
    main.app.dependency_overrides[main.get_card_reader] = lambda: fake_reader(is_shc=False)
    body = client.post("/api/extract", files={"file": ("card.png", png_bytes(), "image/png")}).json()
    assert not body["is_soil_health_card"] and all(v is None for v in body["values"].values())


def test_explain_without_llm_uses_rules_and_cites(client):
    body = client.post("/api/explain", json=sample_request()).json()
    assert body["generated_by"] == "rules"
    assert body["points"] and body["citations"]


def test_speak(client, monkeypatch):
    seen = {}

    def fake_synth(text, lang):
        seen.update(text=text, lang=lang)
        return b"ID3fake"
    monkeypatch.setattr(tts, "synthesize", fake_synth)
    r = client.post("/api/speak", json=sample_request(lang="te"))
    assert r.status_code == 200 and r.headers["content-type"] == "audio/mpeg"
    assert seen["lang"] == "te" and "రూపాయలు" in seen["text"]


def test_speak_failure_is_502(client, monkeypatch):
    def broken(text, lang):
        raise RuntimeError("no network")
    monkeypatch.setattr(tts, "synthesize", broken)
    assert client.post("/api/speak", json=sample_request()).status_code == 502
