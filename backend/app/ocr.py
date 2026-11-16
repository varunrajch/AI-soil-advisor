"""OCR ingestion: check the upload, read it with the vision model, validate what came back."""
import io
import logging
import time
from typing import Callable, Dict, Optional

from PIL import Image, UnidentifiedImageError

import engine
import extract

from .logging_setup import log
from .schemas import SOIL_RANGES, ExtractResponse, FarmFromCard

logger = logging.getLogger("nela.ocr")

ALLOWED_FORMATS = {"JPEG", "PNG"}


class UploadError(ValueError):
    """The file itself is unusable (wrong type, too big, not an image)."""


def check_image(data: bytes, max_bytes: int) -> str:
    if not data:
        raise UploadError("empty file")
    if len(data) > max_bytes:
        raise UploadError(f"file is larger than {max_bytes // (1024 * 1024)} MB")
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
    except (UnidentifiedImageError, OSError):
        raise UploadError("not a readable image")
    if img.format not in ALLOWED_FORMATS:
        raise UploadError(f"only JPG or PNG accepted, got {img.format}")
    return img.format


def validate_values(raw: Dict[str, Optional[float]]) -> ExtractResponse:
    """Drop impossible readings and report what is missing, so the farmer can fix it by hand."""
    is_card = bool(raw.get("is_shc"))
    values: Dict[str, Optional[float]] = {}
    warnings = []
    for key, (low, high) in SOIL_RANGES.items():
        v = raw.get(key)
        if v is not None and not (low <= v <= high):
            warnings.append(f"{key}={v:g} is outside the plausible range {low:g}-{high:g}; please check it")
            v = None
        values[key] = v
    missing = [k for k, v in values.items() if v is None]
    farm = validate_farm(raw, warnings)
    if not is_card:
        # Never pass numbers from a document we do not understand into the dose rules.
        values = {k: None for k in values}
        missing = list(values)
        farm = FarmFromCard()
        warnings.insert(0, "This does not look like an Indian Soil Health Card; nothing was filled in.")
    return ExtractResponse(is_soil_health_card=is_card, values=values, missing=missing,
                           warnings=warnings, farm=farm)


def validate_farm(raw: dict, warnings: list) -> FarmFromCard:
    crop = raw.get("crop")
    if crop is not None and crop not in engine.BASE_DOSE:
        warnings.append(f"crop {crop!r} on the card is not supported yet; please pick the crop yourself")
        crop = None
    season = raw.get("season") if raw.get("season") in ("Kharif", "Rabi") else None
    acres = raw.get("acres")
    if acres is not None and not (0 < acres <= 100):
        warnings.append(f"area {acres:g} acres looks wrong; please check it")
        acres = None
    return FarmFromCard(crop=crop, season=season, acres=acres)


def read_soil_card(data: bytes, api_key: str, max_bytes: int,
                   reader: Callable[[bytes, str], dict] = extract.read_card) -> ExtractResponse:
    fmt = check_image(data, max_bytes)
    start = time.perf_counter()
    raw = reader(data, api_key)
    result = validate_values(raw)
    log(logger, logging.INFO, "ocr.done", format=fmt, bytes=len(data),
        ms=round((time.perf_counter() - start) * 1000), is_card=result.is_soil_health_card,
        missing=result.missing, warnings=len(result.warnings))
    return result
