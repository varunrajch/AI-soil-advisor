"""FastAPI app. Run from the project root:  python3 -m uvicorn backend.app.main:app --reload"""
import logging
from functools import lru_cache

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

import engine

from . import ocr, tts
from .config import Settings, settings
from .explain import explain_plan, groq_llm
from .logging_setup import RequestLogMiddleware, log, setup_logging
from .rag.store import VectorIndex, get_embedder
from .schemas import Change, ExplainResponse, ExtractResponse, Plan, PlanRequest

setup_logging()
logger = logging.getLogger("nela.api")

app = FastAPI(title="Nela Mitra API", version="1.0.0",
              description="Soil Health Card to fertiliser action plan. Rules compute every quantity.")
app.add_middleware(RequestLogMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"],
                   allow_headers=["*"], expose_headers=["x-request-id"])


# ---------- dependencies (overridden in tests) ----------
def get_settings() -> Settings:
    return settings


@lru_cache(maxsize=1)
def get_index():
    return VectorIndex.load(settings.index_dir)


def get_rag():
    index = get_index()
    return index, (get_embedder(settings.embed_model) if index is not None else None)


def get_llm(s: Settings = Depends(get_settings)):
    return groq_llm(s.groq_api_key, s.llm_model) if s.groq_api_key else None


def get_card_reader():
    return ocr.extract.read_card


# ---------- helpers ----------
def build_plan(req: PlanRequest, lang=None) -> dict:
    return engine.make_plan(req.soil.model_dump(), req.crop, req.acres, req.last.model_dump(), lang or req.lang)


def to_plan_model(req: PlanRequest, p: dict) -> Plan:
    return Plan(
        crop=req.crop, headline=p["headline"], headline_detail=p["headline_detail"],
        fertiliser_changes=p["fertiliser_changes"], ratings=p["ratings"], buy=p["buy"], extra_buy=p["extra_buy"],
        when=p["when"], changes=[Change(label=l, action=a, text=t) for l, a, t in p["changes"]],
        fixes=p["fixes"], old_cost=round(p["old_cost"], 2), new_cost=round(p["new_cost"], 2),
        bags=p["bags"], kg={k: round(v, 1) for k, v in p["kg"].items()},
        footer=engine.TEXT[req.lang]["footer"],
    )


# ---------- routes ----------
@app.get("/api/health")
def health(s: Settings = Depends(get_settings), rag=Depends(get_rag)):
    index, _ = rag
    return {"status": "ok", "ocr_enabled": bool(s.groq_api_key), "llm_enabled": bool(s.groq_api_key),
            "rag_chunks": len(index.chunks) if index is not None else 0}


@app.get("/api/meta")
def meta():
    """Crops, samples and every UI string in English and Telugu, so the frontend has one source of truth."""
    return {
        "crops": list(engine.BASE_DOSE),
        "seasons": ["Kharif", "Rabi"],
        "samples": engine.SAMPLES,
        "text": engine.TEXT,
        "prices": engine.PRICE,
        "bag_kg": engine.BAG_KG,
    }


@app.post("/api/extract", response_model=ExtractResponse)
async def extract_card(file: UploadFile = File(...), s: Settings = Depends(get_settings),
                       reader=Depends(get_card_reader)):
    if not s.groq_api_key:
        raise HTTPException(503, "Card reading needs an API key, enter values or load a sample.")
    data = await file.read()
    try:
        return ocr.read_soil_card(data, s.groq_api_key, s.max_upload_mb * 1024 * 1024, reader=reader)
    except ocr.UploadError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        if type(e).__name__ == "RateLimitError":
            log(logger, logging.WARNING, "ocr.rate_limited", error=str(e)[:300])
            raise HTTPException(429, "Too many card reads right now. Please wait a minute and try again.")
        log(logger, logging.ERROR, "ocr.failed", error=str(e)[:300])
        raise HTTPException(502, "Could not read the card right now, please try again.")


@app.post("/api/plan", response_model=Plan)
def plan(req: PlanRequest):
    return to_plan_model(req, build_plan(req))


@app.post("/api/explain", response_model=ExplainResponse)
def explain(req: PlanRequest, rag=Depends(get_rag), llm=Depends(get_llm)):
    index, embedder = rag
    return explain_plan(req.soil.model_dump(), req.crop, req.acres, req.last.model_dump(), req.lang,
                        index, embedder, llm)


@app.post("/api/speak")
def speak(req: PlanRequest):
    text = engine.speech_text(build_plan(req), req.lang)
    try:
        audio = tts.synthesize(text, req.lang)
    except Exception as e:
        log(logger, logging.ERROR, "tts.failed", error=str(e)[:300])
        raise HTTPException(502, "Audio not available right now")
    return Response(content=audio, media_type="audio/mpeg")


# ---------- built React app (production) ----------
if settings.frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=settings.frontend_dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "Not Found")
        file = settings.frontend_dist / path
        return FileResponse(file if path and file.is_file() else settings.frontend_dist / "index.html")
