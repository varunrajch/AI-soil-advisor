"""OCR ingestion and validation."""
import io

import pytest
from PIL import Image

import extract
from backend.app import ocr
from backend.tests.conftest import fake_reader, png_bytes

MB = 1024 * 1024


def test_accepts_png():
    assert ocr.check_image(png_bytes(), 8 * MB) == "PNG"


@pytest.mark.parametrize("data,msg", [(b"", "empty"), (b"not an image", "not a readable image")])
def test_rejects_bad_files(data, msg):
    with pytest.raises(ocr.UploadError, match=msg):
        ocr.check_image(data, 8 * MB)


def test_rejects_large_file():
    with pytest.raises(ocr.UploadError, match="larger than"):
        ocr.check_image(png_bytes(), 10)


def test_rejects_gif():
    buf = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buf, format="GIF")
    with pytest.raises(ocr.UploadError, match="only JPG or PNG"):
        ocr.check_image(buf.getvalue(), 8 * MB)


def test_implausible_value_is_dropped_with_warning():
    result = ocr.read_soil_card(png_bytes(), "key", 8 * MB, reader=fake_reader({"ph": 45.0}))
    assert result.values["ph"] is None
    assert "ph" in result.missing
    assert any("ph=45" in w for w in result.warnings)
    assert result.values["n"] == 210.0


def test_missing_values_are_reported():
    result = ocr.read_soil_card(png_bytes(), "key", 8 * MB, reader=fake_reader({"zn": None, "b": None}))
    assert result.missing == ["zn", "b"]


def test_non_card_fills_nothing():
    result = ocr.read_soil_card(png_bytes(), "key", 8 * MB, reader=fake_reader(is_shc=False))
    assert not result.is_soil_health_card
    assert all(v is None for v in result.values.values())
    assert "does not look like" in result.warnings[0]


def test_parse_reply_strips_think_tags_and_fences():
    raw = '<think>let me look</think>```json\n{"is_shc": true, "ph": "8.2", "n": null, "k": "abc"}\n```'
    values = extract.parse_reply(raw)
    assert values["ph"] == 8.2 and values["n"] is None and values["k"] is None
    assert values["is_shc"] is True


def test_farm_details_come_back_from_the_card():
    result = ocr.read_soil_card(png_bytes(), "key", 8 * MB,
                                reader=fake_reader({"crop": "Groundnut", "season": "Kharif", "acres": 2.0}))
    assert result.farm.crop == "Groundnut" and result.farm.season == "Kharif" and result.farm.acres == 2.0


def test_unsupported_crop_and_bad_area_are_dropped():
    result = ocr.read_soil_card(png_bytes(), "key", 8 * MB,
                                reader=fake_reader({"crop": "Wheat", "acres": 5000.0}))
    assert result.farm.crop is None and result.farm.acres is None
    assert any("Wheat" in w for w in result.warnings) and any("5000" in w for w in result.warnings)


def test_non_card_returns_no_farm_details():
    result = ocr.read_soil_card(png_bytes(), "key", 8 * MB, reader=fake_reader(is_shc=False))
    assert result.farm.crop is None and result.farm.acres is None


@pytest.mark.parametrize("reply,expected", [
    ({"crop": "Rice (Paddy)", "season": "Rabi 2026", "area": "1", "area_unit": "acre"},
     {"crop": "Paddy", "season": "Rabi", "acres": 1.0}),
    ({"crop": "వేరుశనగ", "season": "kharif", "area": 1, "area_unit": "hectare"},
     {"crop": "Groundnut", "season": "Kharif", "acres": 2.47}),
    ({"crop": "Sugarcane", "season": None, "area": "two", "area_unit": None},
     {"crop": None, "season": None, "acres": None}),
])
def test_parse_farm(reply, expected):
    assert extract.parse_farm(reply) == expected
