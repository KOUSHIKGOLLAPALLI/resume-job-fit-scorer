from pydantic import BaseModel, Field
from typing import Literal

class Criterion(BaseModel):
    name: str
    requirement: str
    weight: float = Field(gt=0, le=1)

class CriterionScore(BaseModel):
    criterion: str
    weight: float
    score: float = Field(ge=0, le=100)
    evidence: str
    reasoning: str

class FitResponse(BaseModel):
    overall_score: float = Field(ge=0, le=100)
    verdict: Literal["strong_fit", "partial_fit", "weak_fit"]
    criteria: list[CriterionScore]
    parser_warning: str | None = None
    llm_used: bool
    latency_ms: float
