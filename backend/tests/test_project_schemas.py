"""Pydantic schema validation for Project (product brief)."""

import pytest
from pydantic import ValidationError

from app.models.project import ProjectStatus
from app.schemas.project import ProjectCreate, ProjectUpdate

_VALID_CREATE_KWARGS = {
    "name": "  Portfolio Discovery Tool  ",
    "problem_statement": "Teams decide on intuition alone.",
    "target_user": "Early-stage product managers.",
    "product_hypothesis": "Evidence-grounded personas surface weak assumptions.",
    "success_metric": "Time to a decision memo.",
}


def test_project_create_trims_string_fields() -> None:
    project = ProjectCreate(**_VALID_CREATE_KWARGS)
    assert project.name == "Portfolio Discovery Tool"


def test_project_create_defaults_status_to_draft() -> None:
    project = ProjectCreate(**_VALID_CREATE_KWARGS)
    assert project.status == ProjectStatus.DRAFT


def test_project_create_defaults_assumptions_to_empty_list() -> None:
    project = ProjectCreate(**_VALID_CREATE_KWARGS)
    assert project.assumptions == []


@pytest.mark.parametrize(
    "field",
    ["name", "problem_statement", "target_user", "product_hypothesis", "success_metric"],
)
def test_project_create_rejects_blank_required_fields(field: str) -> None:
    kwargs = {**_VALID_CREATE_KWARGS, field: "   "}
    with pytest.raises(ValidationError):
        ProjectCreate(**kwargs)


def test_project_create_normalizes_assumptions() -> None:
    project = ProjectCreate(
        **_VALID_CREATE_KWARGS,
        assumptions=["  Users want this  ", "", "   ", "Another one"],
    )
    assert project.assumptions == ["Users want this", "Another one"]


def test_project_create_deduplicates_assumptions_case_insensitively() -> None:
    project = ProjectCreate(
        **_VALID_CREATE_KWARGS,
        assumptions=["Users want this", "users want this", "USERS WANT THIS", "Distinct"],
    )
    assert project.assumptions == ["Users want this", "Distinct"]


def test_project_update_rejects_empty_patch() -> None:
    with pytest.raises(ValidationError):
        ProjectUpdate()


def test_project_update_allows_single_field() -> None:
    update = ProjectUpdate(name="New Name")
    assert update.name == "New Name"
    assert update.problem_statement is None


def test_project_update_rejects_blank_provided_field() -> None:
    with pytest.raises(ValidationError):
        ProjectUpdate(name="   ")


def test_project_update_normalizes_assumptions_when_provided() -> None:
    update = ProjectUpdate(assumptions=["  A  ", "a", "B"])
    assert update.assumptions == ["A", "B"]


def test_project_update_accepts_status_change() -> None:
    update = ProjectUpdate(status=ProjectStatus.ACTIVE)
    assert update.status == ProjectStatus.ACTIVE


def test_project_create_rejects_invalid_status() -> None:
    with pytest.raises(ValidationError):
        ProjectCreate(**_VALID_CREATE_KWARGS, status="not-a-status")


def test_project_update_allows_explicit_none_for_other_fields() -> None:
    update = ProjectUpdate(name="New Name", problem_statement=None, assumptions=None)
    assert update.name == "New Name"
    assert update.problem_statement is None
    assert update.assumptions is None
