"""Pydantic validation for Experiment/Variant request schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.experiment import (
    ExperimentCreate,
    ExperimentExecuteRequest,
    ExperimentUpdate,
    VariantCreate,
)
from tests.experiment_helpers import experiment_create_payload


def test_valid_experiment_create() -> None:
    experiment = ExperimentCreate(**experiment_create_payload([1, 2, 3]))
    assert experiment.repeat_count == 1
    assert len(experiment.variants) == 2


def test_experiment_requires_exactly_two_variants() -> None:
    payload = experiment_create_payload([1])
    payload["variants"] = [{"key": "A", "name": "Variant A", "description": "desc"}]
    with pytest.raises(ValidationError):
        ExperimentCreate(**payload)


def test_experiment_requires_one_a_and_one_b() -> None:
    payload = experiment_create_payload([1])
    payload["variants"] = [
        {"key": "A", "name": "Variant A", "description": "desc"},
        {"key": "A", "name": "Duplicate A", "description": "desc"},
    ]
    with pytest.raises(ValidationError):
        ExperimentCreate(**payload)


@pytest.mark.parametrize("field", ["name", "objective", "hypothesis", "scenario"])
def test_experiment_required_text_fields_cannot_be_blank(field: str) -> None:
    payload = experiment_create_payload([1])
    payload[field] = "   "
    with pytest.raises(ValidationError):
        ExperimentCreate(**payload)


def test_variant_name_and_description_cannot_be_blank() -> None:
    with pytest.raises(ValidationError):
        VariantCreate(key="A", name="  ", description="desc")
    with pytest.raises(ValidationError):
        VariantCreate(key="A", name="Variant A", description="  ")


def test_evaluation_criteria_normalized_and_deduplicated() -> None:
    payload = experiment_create_payload([1])
    payload["evaluation_criteria"] = ["Clarity", " clarity ", "Adoption intent", ""]
    experiment = ExperimentCreate(**payload)
    assert experiment.evaluation_criteria == ["Clarity", "Adoption intent"]


def test_evaluation_criteria_requires_at_least_one_item() -> None:
    payload = experiment_create_payload([1])
    payload["evaluation_criteria"] = ["  ", ""]
    with pytest.raises(ValidationError):
        ExperimentCreate(**payload)


@pytest.mark.parametrize("repeat_count", [0, 4])
def test_repeat_count_must_be_between_one_and_three(repeat_count: int) -> None:
    payload = experiment_create_payload([1], repeat_count=repeat_count)
    with pytest.raises(ValidationError):
        ExperimentCreate(**payload)


@pytest.mark.parametrize("repeat_count", [1, 2, 3])
def test_repeat_count_within_bounds_is_accepted(repeat_count: int) -> None:
    payload = experiment_create_payload([1], repeat_count=repeat_count)
    experiment = ExperimentCreate(**payload)
    assert experiment.repeat_count == repeat_count


def test_persona_ids_must_not_be_empty() -> None:
    payload = experiment_create_payload([])
    with pytest.raises(ValidationError):
        ExperimentCreate(**payload)


def test_persona_ids_must_not_contain_duplicates() -> None:
    payload = experiment_create_payload([1, 1, 2])
    with pytest.raises(ValidationError):
        ExperimentCreate(**payload)


def test_experiment_update_rejects_empty_patch() -> None:
    with pytest.raises(ValidationError):
        ExperimentUpdate()


def test_experiment_update_allows_single_field() -> None:
    update = ExperimentUpdate(name="New name")
    assert update.name == "New name"
    assert update.objective is None


def test_experiment_update_validates_variants_when_provided() -> None:
    with pytest.raises(ValidationError):
        ExperimentUpdate(
            variants=[
                {"key": "A", "name": "Variant A", "description": "desc"},
                {"key": "A", "name": "Duplicate A", "description": "desc"},
            ]
        )


def test_experiment_execute_request_requires_true() -> None:
    with pytest.raises(ValidationError):
        ExperimentExecuteRequest(confirm_execution=False)


def test_experiment_execute_request_requires_field() -> None:
    with pytest.raises(ValidationError):
        ExperimentExecuteRequest.model_validate({})


def test_experiment_execute_request_accepts_true() -> None:
    request = ExperimentExecuteRequest(confirm_execution=True)
    assert request.confirm_execution is True
