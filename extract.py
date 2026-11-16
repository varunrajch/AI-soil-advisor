"""Read a Soil Health Card photo into numbers using a Groq vision model."""
import base64
import io
import json
import os
import re

from PIL import Image

MODEL = "qwen/qwen3.8-27b"  # the spec's qwen/qwen3.6-27b is not available on this Groq account
KEYS = ["ph", "ec", "oc", "n", "p", "k", "zn", "b"]

PROMPT = (
    "Look at this image. Reply with JSON only, using exactly these keys: "
    "is_shc, ph, ec, oc, n, p, k, zn, b, crop, season, area, area_unit. "
    "is_shc = true only if this is an Indian Soil Health Card for one field, reporting values in "
    "these units: ph = pH, ec = EC in dS/m, oc = organic carbon %, n = available nitrogen kg/ha, "
    "p = available phosphorus kg/ha, k = available potassium kg/ha, zn = zinc ppm, b = boron ppm. "
    "Set is_shc = false for any other report, for example soil organic matter (SOM) instead of "
    "organic carbon, mg/L units, or several fields in one table. "
    "Copy numbers exactly as printed, never convert units. "
    "crop = the crop named on the card in English (for example Paddy or Groundnut), "
    "season = Kharif or Rabi as printed, area = the farm area number, "
    "area_unit = acre or hectare as printed. "
    "Use null for any value that is not printed on the card."
)

# Names a card may use for the crops the rule engine knows.
CROP_ALIASES = {
    "paddy": "Paddy", "rice": "Paddy", "వరి": "Paddy",
    "groundnut": "Groundnut", "peanut": "Groundnut", "వేరుశనగ": "Groundnut",
    "maize": "Maize", "corn": "Maize", "మొక్కజొన్న": "Maize",
    "cotton": "Cotton", "పత్తి": "Cotton",
    "chilli": "Chilli", "chili": "Chilli", "mirchi": "Chilli", "మిరప": "Chilli",
    "redgram": "Redgram", "red gram": "Redgram", "pigeonpea": "Redgram", "pigeon pea": "Redgram",
    "tur": "Redgram", "arhar": "Redgram", "కంది": "Redgram",
}
HECTARE_TO_ACRE = 2.471


def get_api_key():
    try:
        import streamlit as st
        key = st.secrets.get("GROQ_API_KEY")
        if key:
            return key
    except Exception:
        pass
    if os.environ.get("GROQ_API_KEY"):
        return os.environ["GROQ_API_KEY"]
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_file):
        for line in open(env_file):
            name, _, value = line.strip().partition("=")
            if name.strip() == "GROQ_API_KEY" and value.strip():
                return value.strip().strip('"').strip("'")
    return None


def to_data_url(file_bytes):
    img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    img.thumbnail((1600, 1600))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def parse_reply(text):
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    text = re.sub(r"```(?:json)?", "", text).strip()
    match = re.search(r"\{.*\}", text, flags=re.S)
    data = json.loads(match.group(0) if match else text)
    values = {}
    for k in KEYS:
        v = data.get(k)
        try:
            values[k] = float(v) if v is not None else None
        except (TypeError, ValueError):
            values[k] = None
    values["is_shc"] = data.get("is_shc") in (True, "true", "True")
    values.update(parse_farm(data))
    return values


def parse_farm(data):
    """Crop, season and acres from the reply; None for anything unknown or unreadable."""
    crop_text = str(data.get("crop") or "").strip().lower()
    crop = next((name for alias, name in CROP_ALIASES.items() if alias in crop_text), None) if crop_text else None
    season_text = str(data.get("season") or "").lower()
    season = "Kharif" if "kharif" in season_text else "Rabi" if "rabi" in season_text else None
    try:
        area = float(data.get("area"))
        if "hect" in str(data.get("area_unit") or "").lower():
            area *= HECTARE_TO_ACRE
        acres = round(area, 2) if area > 0 else None
    except (TypeError, ValueError):
        acres = None
    return {"crop": crop, "season": season, "acres": acres}


def read_card(file_bytes, api_key):
    from groq import Groq

    client = Groq(api_key=api_key)
    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": PROMPT},
            {"type": "image_url", "image_url": {"url": to_data_url(file_bytes)}},
        ],
    }]
    # No "thinking" and a small answer cap: the JSON is ~100 tokens, and the free tier allows
    # 1000 output tokens per minute, so a large reserved budget gets rejected with a 429.
    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0,
        max_completion_tokens=300,
        reasoning_effort="none",
    )
    return parse_reply(resp.choices[0].message.content)
