"""Shared fixtures. Everything here is offline: fake OCR, fake LLM, fake embedder."""
import hashlib
import io
import json
import re

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

import engine
from backend.app import main
from backend.app.config import Settings
from backend.app.rag.chunking import Chunk
from backend.app.rag.store import VectorIndex

SOIL_KEYS = ["ph", "ec", "oc", "n", "p", "k", "zn", "b"]


class FakeEmbedder:
    """Hashed bag-of-words vectors: deterministic, shares words -> similar vectors."""

    dim = 128

    def embed(self, texts):
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, text in enumerate(texts):
            for word in re.findall(r"[a-z]+", text.lower()):
                out[i, int(hashlib.md5(word.encode()).hexdigest(), 16) % self.dim] += 1.0
        return out


@pytest.fixture
def embedder():
    return FakeEmbedder()


@pytest.fixture
def small_index(embedder):
    chunks = [
        Chunk("rice_zinc.pdf", "Rice zinc", 2, "https://example.org/zinc",
              "zinc deficiency in rice soil is corrected with zinc sulphate application at transplanting"),
        Chunk("gypsum.pdf", "Groundnut gypsum", 3, None,
              "gypsum application at flowering improves groundnut pod filling through calcium"),
        Chunk("ap.pdf", "AP soil test study", 54, None,
              "soil test based fertiliser recommendation nitrogen phosphorus potassium dose for rice paddy"),
        Chunk("ap.pdf", "AP soil test study", 23, None,
              "high soil phosphorus means DAP phosphate fertiliser overuse should be reduced"),
    ]
    return VectorIndex.build(chunks, embedder)


def sample_request(name="Sample A", lang="en", **overrides):
    s = engine.SAMPLES[name]
    req = {"soil": {k: s[k] for k in SOIL_KEYS}, "crop": s["crop"], "acres": s["acres"],
           "season": s["season"], "lang": lang,
           "last": {"urea": s["last_urea"], "dap": s["last_dap"], "mop": s["last_mop"]}}
    req.update(overrides)
    return req


def png_bytes(size=(40, 30)):
    buf = io.BytesIO()
    Image.new("RGB", size, "white").save(buf, format="PNG")
    return buf.getvalue()


def fake_reader(values=None, is_shc=True):
    def read(data, api_key):
        base = {k: engine.SAMPLES["Sample A"][k] for k in SOIL_KEYS}
        base.update(values or {})
        base["is_shc"] = is_shc
        base.setdefault("crop", "Paddy")
        base.setdefault("season", "Rabi")
        base.setdefault("acres", 1.0)
        return base
    return read


def fake_llm(points):
    def call(messages):
        call.messages = messages
        return json.dumps({"points": points})
    return call


@pytest.fixture
def client(small_index, embedder):
    main.app.dependency_overrides = {
        main.get_settings: lambda: Settings(groq_api_key="test-key"),
        main.get_card_reader: lambda: fake_reader(),
        main.get_rag: lambda: (small_index, embedder),
        main.get_llm: lambda: None,
    }
    yield TestClient(main.app)
    main.app.dependency_overrides = {}
