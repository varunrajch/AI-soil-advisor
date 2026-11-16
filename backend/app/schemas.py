"""Request and response models. Field limits are the first validation layer."""
from typing import Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field, field_validator

import engine

Lang = Literal["en", "te"]

# Plausible ranges for Soil Health Card values. Anything outside is almost certainly a misread.
SOIL_RANGES: Dict[str, Tuple[float, float]] = {
    "ph": (3.0, 11.0), "ec": (0.0, 20.0), "oc": (0.0, 5.0), "n": (0.0, 1500.0),
    "p": (0.0, 300.0), "k": (0.0, 2000.0), "zn": (0.0, 50.0), "b": (0.0, 20.0),
}


class Soil(BaseModel):
    ph: float = Field(ge=3.0, le=11.0)
    ec: float = Field(ge=0.0, le=20.0, description="dS/m")
    oc: float = Field(ge=0.0, le=5.0, description="organic carbon %")
    n: float = Field(ge=0.0, le=1500.0, description="kg/ha")
    p: float = Field(ge=0.0, le=300.0, description="kg/ha")
    k: float = Field(ge=0.0, le=2000.0, description="kg/ha")
    zn: float = Field(ge=0.0, le=50.0, description="ppm")
    b: float = Field(ge=0.0, le=20.0, description="ppm")


class LastSeason(BaseModel):
    """Bags per acre bought last season."""
    urea: float = Field(0.0, ge=0.0, le=50.0)
    dap: float = Field(0.0, ge=0.0, le=50.0)
    mop: float = Field(0.0, ge=0.0, le=50.0)


class PlanRequest(BaseModel):
    soil: Soil
    crop: str
    acres: float = Field(gt=0.0, le=100.0)
    season: Optional[str] = None
    last: LastSeason = LastSeason()
    lang: Lang = "en"

    @field_validator("crop")
    @classmethod
    def known_crop(cls, v):
        if v not in engine.BASE_DOSE:
            raise ValueError(f"unknown crop {v!r}; expected one of {sorted(engine.BASE_DOSE)}")
        return v


class Change(BaseModel):
    label: str
    action: Literal["Reduce", "Increase", "Add", "Keep"]
    text: str


class Plan(BaseModel):
    crop: str
    headline: str
    headline_detail: Optional[str] = None
    fertiliser_changes: int
    ratings: Dict[str, str]
    buy: List[Tuple[str, str]]
    extra_buy: List[Tuple[str, str]]
    when: List[Tuple[str, str]]
    changes: List[Change]
    fixes: List[str]
    old_cost: float
    new_cost: float
    bags: Dict[str, float]
    kg: Dict[str, float]
    footer: str


class FarmFromCard(BaseModel):
    crop: Optional[str] = None
    season: Optional[str] = None
    acres: Optional[float] = None


class ExtractResponse(BaseModel):
    is_soil_health_card: bool
    values: Dict[str, Optional[float]]
    missing: List[str]
    warnings: List[str]
    farm: FarmFromCard = FarmFromCard()


class Citation(BaseModel):
    id: int
    doc: str
    title: str
    page: int
    url: Optional[str]
    snippet: str


class ExplainPoint(BaseModel):
    text: str
    sources: List[int]


class ExplainResponse(BaseModel):
    points: List[ExplainPoint]
    citations: List[Citation]
    generated_by: Literal["llm", "rules"]
    dropped_points: int = 0
