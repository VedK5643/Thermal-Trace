"""
ML Pydantic schemas.
"""
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

HotspotMLType = Literal[
    "industrial_thermal_source", "mining_thermal_source", "natural_fire", "unknown"
]


class FeatureExplanationItem(BaseModel):
    feature: str
    impact: float
    description: str


class MLPredictionOutput(BaseModel):
    """Output from ML inference engine."""

    ml_type: HotspotMLType = Field(..., alias="mlType", serialization_alias="mlType")
    ml_confidence: float = Field(..., alias="mlConfidence", serialization_alias="mlConfidence")
    model_version: str = Field("thermalwatch-v1", alias="modelVersion", serialization_alias="modelVersion")
    ml_explanation: Optional[Dict[str, Any]] = Field(
        None, alias="mlExplanation", serialization_alias="mlExplanation"
    )

    model_config = ConfigDict(populate_by_name=True)
