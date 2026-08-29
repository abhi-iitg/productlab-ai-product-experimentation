"""Pydantic schema validation for EvidenceItem."""

import pytest
from pydantic import ValidationError

from app.models.evidence_item import EvidenceType
from app.schemas.evidence import EvidenceItemCreate, EvidenceItemUpdate


def test_evidence_item_create_trims_title_and_content() -> None:
    item = EvidenceItemCreate(
        evidence_type=EvidenceType.INTERVIEW_NOTE,
        title="  Interview with early adopter  ",
        content="  They struggled with onboarding.  ",
    )
    assert item.title == "Interview with early adopter"
    assert item.content == "They struggled with onboarding."


def test_evidence_item_create_rejects_blank_title() -> None:
    with pytest.raises(ValidationError):
        EvidenceItemCreate(evidence_type=EvidenceType.RESEARCH_NOTE, title="  ", content="content")


def test_evidence_item_create_rejects_blank_content() -> None:
    with pytest.raises(ValidationError):
        EvidenceItemCreate(evidence_type=EvidenceType.RESEARCH_NOTE, title="title", content="   ")


def test_evidence_item_create_source_label_is_optional() -> None:
    item = EvidenceItemCreate(
        evidence_type=EvidenceType.SURVEY_RESPONSE, title="title", content="content"
    )
    assert item.source_label is None


def test_evidence_item_create_rejects_invalid_evidence_type() -> None:
    with pytest.raises(ValidationError):
        EvidenceItemCreate(evidence_type="not-a-type", title="title", content="content")


@pytest.mark.parametrize(
    "evidence_type",
    [
        "interview_note",
        "survey_response",
        "support_ticket",
        "product_review",
        "research_note",
    ],
)
def test_evidence_item_create_accepts_every_supported_type(evidence_type: str) -> None:
    item = EvidenceItemCreate(evidence_type=evidence_type, title="title", content="content")
    assert item.evidence_type == EvidenceType(evidence_type)


def test_evidence_item_update_rejects_empty_patch() -> None:
    with pytest.raises(ValidationError):
        EvidenceItemUpdate()


def test_evidence_item_update_allows_single_field() -> None:
    update = EvidenceItemUpdate(title="New Title")
    assert update.title == "New Title"
    assert update.content is None


def test_evidence_item_update_rejects_blank_provided_title() -> None:
    with pytest.raises(ValidationError):
        EvidenceItemUpdate(title="   ")


def test_evidence_item_update_allows_explicit_none_for_other_fields() -> None:
    update = EvidenceItemUpdate(title="New Title", content=None, source_label=None)
    assert update.title == "New Title"
    assert update.content is None
    assert update.source_label is None


def test_evidence_item_create_normalizes_blank_source_label_to_none() -> None:
    item = EvidenceItemCreate(
        evidence_type=EvidenceType.RESEARCH_NOTE,
        title="title",
        content="content",
        source_label="   ",
    )
    assert item.source_label is None
