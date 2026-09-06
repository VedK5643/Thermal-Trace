"""
Phase 9C Domain Reasoning & Adversarial Safety Unit Tests.
Verifies domain concept coverage, multi-signal reasoning, feature interpretations, and adversarial safety protections.
"""
import pytest
from app.services.llm.prompts import SYSTEM_PROMPT


def test_system_prompt_domain_features():
    """Verify system prompt includes explicit feature interpretation guidelines."""
    assert "bright_ti4" in SYSTEM_PROMPT
    assert "bright_ti5" in SYSTEM_PROMPT
    assert "temp_diff" in SYSTEM_PROMPT
    assert "frp" in SYSTEM_PROMPT
    assert "persistence_count" in SYSTEM_PROMPT
    assert "facility_dist_km" in SYSTEM_PROMPT
    assert "ml_explanation" in SYSTEM_PROMPT


def test_system_prompt_wildfire_near_facility_rule():
    """Verify system prompt forbids overriding Wildfire classification based solely on facility proximity."""
    assert "WILDFIRE NEAR FACILITY: Respect the ML model's prediction" in SYSTEM_PROMPT
    assert "Proximity to a factory alone does NOT override a Wildfire classification" in SYSTEM_PROMPT


def test_system_prompt_causation_rejection_rule():
    """Verify system prompt forbids claiming an industrial facility caused a fire."""
    assert "NOT proof of causation" in SYSTEM_PROMPT
    assert "Never claim a facility caused a fire solely because it is nearby" in SYSTEM_PROMPT


def test_system_prompt_synthetic_benchmark_wording():
    """Verify system prompt enforces correct wording for 93.70% synthetic engineering benchmark."""
    assert "93.70% benchmark accuracy" in SYSTEM_PROMPT
    assert "synthetic engineering benchmark dataset" in SYSTEM_PROMPT
    assert "does NOT establish real-world ground-truth accuracy" in SYSTEM_PROMPT


def test_system_prompt_abstention_handling():
    """Verify system prompt instructs model to respect ml_type = 'unknown' without forcing class labels."""
    assert "UNKNOWN / ABSTENTION: If ml_type = \"unknown\", respect model uncertainty" in SYSTEM_PROMPT
    assert "Do not force a class label" in SYSTEM_PROMPT
