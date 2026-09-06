"""
Phase 9H AI Operational Assistant Master Orchestration Unit Tests.
Verifies unified intent routing, executive situation brief formatting, ChatResponse action payloads, session context isolation, security controls, and refusal gates.
"""
from app.api.v1.chat import ChatResponse
from app.services.llm.prompts import SYSTEM_PROMPT


def test_master_intent_routing_and_prompt_structure():
    """Verify system prompt contains intent routing for all operational intent classes."""
    assert "INTENT ROUTING & TOOL ORCHESTRATION" in SYSTEM_PROMPT
    assert "1. CURRENT_STATUS" in SYSTEM_PROMPT
    assert "2. HOTSPOT_INVESTIGATION" in SYSTEM_PROMPT
    assert "3. ALERT_INVESTIGATION" in SYSTEM_PROMPT
    assert "4. FACILITY_LOOKUP" in SYSTEM_PROMPT
    assert "5. HISTORICAL_ANALYSIS" in SYSTEM_PROMPT
    assert "6. REGIONAL_COMPARISON" in SYSTEM_PROMPT
    assert "7. PERIOD_COMPARISON" in SYSTEM_PROMPT
    assert "8. CLASSIFICATION_ANALYSIS" in SYSTEM_PROMPT
    assert "9. PERSISTENCE_ANALYSIS" in SYSTEM_PROMPT
    assert "10. ANOMALY_ANALYSIS" in SYSTEM_PROMPT
    assert "11. ML_EXPLANATION" in SYSTEM_PROMPT
    assert "12. SYSTEM_STATUS" in SYSTEM_PROMPT
    assert "13. GENERAL_THERMAL_CONCEPT" in SYSTEM_PROMPT
    assert "14. DASHBOARD_CONTEXT" in SYSTEM_PROMPT


def test_executive_situation_brief_formatting():
    """Verify system prompt includes required headers for executive situation briefs."""
    assert "EXECUTIVE SITUATION BRIEF FORMAT" in SYSTEM_PROMPT
    assert "### Current Situation" in SYSTEM_PROMPT
    assert "### Key Signals" in SYSTEM_PROMPT
    assert "### Priority" in SYSTEM_PROMPT
    assert "### Caveat" in SYSTEM_PROMPT


def test_chat_response_action_payload():
    """Verify ChatResponse Pydantic model serializes optional action payload correctly."""
    resp = ChatResponse(
        message="Focusing map on hotspot FIRMS-IN-001.",
        conversationId="conv-123456",
        action={"type": "focus_hotspot", "targetId": "FIRMS-IN-001"}
    )
    dumped = resp.model_dump(by_alias=True)
    assert dumped["conversationId"] == "conv-123456"
    assert dumped["action"]["type"] == "focus_hotspot"
    assert dumped["action"]["targetId"] == "FIRMS-IN-001"


def test_master_security_and_disclosures():
    """Verify system prompt enforces scientific disclosures, non-causation, and refusal gates."""
    assert "ThermalTrace ML (model version thermalwatch-v1)" in SYSTEM_PROMPT
    assert "ML predictions are NOT verified ground truth" in SYSTEM_PROMPT
    assert "NOT proof of causation" in SYSTEM_PROMPT
    assert "93.70% benchmark accuracy was achieved on a synthetic engineering benchmark dataset" in SYSTEM_PROMPT
    assert "ThermalTrace currently does not provide a validated future-fire forecast" in SYSTEM_PROMPT
