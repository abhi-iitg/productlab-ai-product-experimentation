"""Persona prompt template: version constant and instruction assembly."""

from app.llm.prompts import PERSONA_PROMPT_VERSION, build_system_instructions, build_user_prompt


def test_prompt_version_is_stable_constant() -> None:
    assert PERSONA_PROMPT_VERSION == "persona-v1"


def test_build_system_instructions_includes_persona_count() -> None:
    instructions = build_system_instructions(3)
    assert "exactly 3 distinct personas" in instructions


def test_build_system_instructions_covers_required_rules() -> None:
    instructions = build_system_instructions(2)
    assert "unsupported_assumptions" in instructions
    assert "evidence_item_id" in instructions
    assert "does not replace real-user research or predict market success" in instructions


def test_build_user_prompt_includes_context_and_focus() -> None:
    prompt = build_user_prompt("=== PROJECT ===\nsome context", "B2B SaaS teams")
    assert "some context" in prompt
    assert "B2B SaaS teams" in prompt
    assert "OPTIONAL FOCUS" in prompt


def test_build_user_prompt_uses_placeholder_when_focus_missing() -> None:
    prompt = build_user_prompt("context", None)
    assert "(none provided)" in prompt
