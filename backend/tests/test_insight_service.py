"""InsightGenerationService: eligibility, atomic persistence, duplicate
prevention, and safe translation of every provider/validation failure mode.

`_RawInsightProvider` mirrors exactly what `OpenAIInsightProvider` does
after `json.loads` — it runs the *real* `InsightGenerationResult.model_validate`
pipeline against the service's real, DB-derived validation context, so the
fabricated-reference/frequency/persona-count scenarios below exercise
production validation logic end-to-end, not a re-description of it.
"""

import pytest
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictError,
    InvalidRequestError,
    NotFoundError,
    ProviderConfigurationError,
    ProviderError,
)
from app.llm.exceptions import (
    LLMConfigurationError,
    LLMEmptyOutputError,
    LLMInvalidSchemaError,
    LLMMalformedJSONError,
    LLMRateLimitError,
    LLMStatusError,
    LLMTimeoutError,
)
from app.llm.insight_context import InsightContextTooLargeError
from app.repositories.insight import InsightRepository
from app.schemas.experiment import ExperimentCreate
from app.schemas.insight import InsightGenerationResult
from app.services import insight_generation as insight_generation_module
from app.services.experiment import ExperimentService
from app.services.insight_generation import InsightGenerationService
from tests.experiment_helpers import (
    experiment_create_payload,
    seed_completed_experiment,
    seed_project_with_personas,
)
from tests.fakes import (
    FakeInsightProvider,
    make_insight_generation_result,
    make_simulation_call_result,
)


class _RawInsightProvider:
    """Runs the real validation pipeline against a caller-supplied raw dict."""

    def __init__(self, raw: dict, *, model_name: str = "fake-raw-insight-model") -> None:
        self._raw = raw
        self.model_name = model_name

    def generate_insights(
        self, *, context: str, allowed_run_ids, run_evidence_ids, run_persona_ids
    ) -> InsightGenerationResult:
        try:
            return InsightGenerationResult.model_validate(
                self._raw,
                context={
                    "allowed_run_ids": allowed_run_ids,
                    "run_evidence_ids": run_evidence_ids,
                    "run_persona_ids": run_persona_ids,
                },
            )
        except PydanticValidationError as exc:
            raise LLMInvalidSchemaError(
                "The AI provider response did not match the required schema."
            ) from exc


def _completed_ids(runs) -> list[int]:
    return sorted(run.id for run in runs if run.status.value == "completed")


def test_successful_generation_persists_insights(db_session: Session) -> None:
    project, experiment, personas, runs = seed_completed_experiment(
        db_session, persona_count=2, repeat_count=1
    )
    completed_ids = _completed_ids(runs)
    provider = FakeInsightProvider(
        result=make_insight_generation_result(supporting_run_ids=completed_ids, persona_count=2)
    )

    insights = InsightGenerationService(db_session, provider).generate(project.id, experiment.id)

    assert len(insights) == 1
    assert insights[0].prompt_version == "insight-v1"
    assert insights[0].model_name == provider.model_name
    assert InsightRepository(db_session).list_for_experiment(experiment.id) == insights


def test_generation_is_fully_atomic_on_one_invalid_candidate(db_session: Session) -> None:
    project, experiment, _personas, runs = seed_completed_experiment(
        db_session, persona_count=2, repeat_count=1
    )
    completed_ids = _completed_ids(runs)
    raw = {
        "insights": [
            {
                "category": "strength",
                "variant_scope": "both",
                "title": "Valid insight",
                "summary": "Grounded in the supplied runs.",
                "frequency": len(completed_ids),
                "persona_count": 2,
                "supporting_run_ids": completed_ids,
                "supporting_evidence_ids": [],
                "confidence_level": "medium",
            },
            {
                "category": "objection",
                "variant_scope": "both",
                "title": "Invalid insight",
                "summary": "Cites a run that does not exist.",
                "frequency": 1,
                "persona_count": 1,
                "supporting_run_ids": [999_999],
                "supporting_evidence_ids": [],
                "confidence_level": "low",
            },
        ]
    }
    provider = _RawInsightProvider(raw)

    with pytest.raises(ProviderError):
        InsightGenerationService(db_session, provider).generate(project.id, experiment.id)

    assert InsightRepository(db_session).list_for_experiment(experiment.id) == []


def test_project_not_found(db_session: Session) -> None:
    provider = FakeInsightProvider()
    with pytest.raises(NotFoundError):
        InsightGenerationService(db_session, provider).generate(999_999, 1)


def test_experiment_not_found(db_session: Session) -> None:
    project, _experiment, _personas, _runs = seed_completed_experiment(db_session)
    provider = FakeInsightProvider()
    with pytest.raises(NotFoundError):
        InsightGenerationService(db_session, provider).generate(project.id, 999_999)


def test_cross_project_experiment_returns_not_found(db_session: Session) -> None:
    _project_a, experiment_a, _personas_a, _runs_a = seed_completed_experiment(db_session)
    project_b, _experiment_b, _personas_b, _runs_b = seed_completed_experiment(db_session)
    provider = FakeInsightProvider()

    with pytest.raises(NotFoundError):
        InsightGenerationService(db_session, provider).generate(project_b.id, experiment_a.id)


def test_ineligible_experiment_status_rejected(db_session: Session) -> None:
    project, _evidence, personas = seed_project_with_personas(db_session)
    experiment = ExperimentService(db_session).create(
        project.id, ExperimentCreate(**experiment_create_payload([p.id for p in personas]))
    )
    provider = FakeInsightProvider()

    with pytest.raises(ConflictError):
        InsightGenerationService(db_session, provider).generate(project.id, experiment.id)


def test_zero_completed_runs_for_one_variant_rejected(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(
        db_session,
        persona_count=1,
        repeat_count=1,
        responses=[make_simulation_call_result(), LLMTimeoutError("timed out")],
    )
    provider = FakeInsightProvider()

    with pytest.raises(ConflictError):
        InsightGenerationService(db_session, provider).generate(project.id, experiment.id)


def test_duplicate_generation_rejected(db_session: Session) -> None:
    project, experiment, _personas, runs = seed_completed_experiment(
        db_session, persona_count=2, repeat_count=1
    )
    completed_ids = _completed_ids(runs)
    provider = FakeInsightProvider(
        result=make_insight_generation_result(supporting_run_ids=completed_ids, persona_count=2)
    )
    InsightGenerationService(db_session, provider).generate(project.id, experiment.id)

    with pytest.raises(ConflictError):
        InsightGenerationService(db_session, provider).generate(project.id, experiment.id)


@pytest.mark.parametrize(
    "error",
    [
        LLMMalformedJSONError("bad json"),
        LLMEmptyOutputError("empty"),
        LLMInvalidSchemaError("bad schema"),
        LLMTimeoutError("timed out"),
        LLMRateLimitError("rate limited"),
        LLMStatusError("status error"),
    ],
)
def test_provider_failures_are_translated_and_nothing_persists(
    db_session: Session, error: Exception
) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(
        db_session, persona_count=2, repeat_count=1
    )
    provider = FakeInsightProvider(error=error)

    with pytest.raises(ProviderError):
        InsightGenerationService(db_session, provider).generate(project.id, experiment.id)

    assert InsightRepository(db_session).list_for_experiment(experiment.id) == []


def test_missing_configuration_returns_service_error(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    provider = FakeInsightProvider(error=LLMConfigurationError("no key"))

    with pytest.raises(ProviderConfigurationError):
        InsightGenerationService(db_session, provider).generate(project.id, experiment.id)


def test_context_limit_exceeded_returns_invalid_request(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(db_session)

    def _raise(*args: object, **kwargs: object) -> str:
        raise InsightContextTooLargeError(999_999, 30_000)

    monkeypatch.setattr(insight_generation_module, "build_insight_context", _raise)
    provider = FakeInsightProvider()

    with pytest.raises(InvalidRequestError):
        InsightGenerationService(db_session, provider).generate(project.id, experiment.id)


def test_fabricated_run_id_rejected(db_session: Session) -> None:
    project, experiment, _personas, runs = seed_completed_experiment(
        db_session, persona_count=1, repeat_count=1
    )
    completed_ids = _completed_ids(runs)
    raw = {
        "insights": [
            {
                "category": "strength",
                "variant_scope": "both",
                "title": "Fabricated run",
                "summary": "Cites a run ID that was never supplied.",
                "frequency": 1,
                "persona_count": 1,
                "supporting_run_ids": [max(completed_ids) + 1000],
                "supporting_evidence_ids": [],
                "confidence_level": "low",
            }
        ]
    }
    with pytest.raises(ProviderError):
        InsightGenerationService(db_session, _RawInsightProvider(raw)).generate(
            project.id, experiment.id
        )
    assert InsightRepository(db_session).list_for_experiment(experiment.id) == []


def test_cross_experiment_run_id_rejected(db_session: Session) -> None:
    project_a, experiment_a, _p_a, runs_a = seed_completed_experiment(
        db_session, persona_count=1, repeat_count=1
    )
    _project_b, experiment_b, _p_b, runs_b = seed_completed_experiment(
        db_session, persona_count=1, repeat_count=1
    )
    other_experiment_run_id = _completed_ids(runs_b)[0]
    raw = {
        "insights": [
            {
                "category": "strength",
                "variant_scope": "both",
                "title": "Cross experiment run",
                "summary": "Cites a run belonging to a different experiment.",
                "frequency": 1,
                "persona_count": 1,
                "supporting_run_ids": [other_experiment_run_id],
                "supporting_evidence_ids": [],
                "confidence_level": "low",
            }
        ]
    }
    with pytest.raises(ProviderError):
        InsightGenerationService(db_session, _RawInsightProvider(raw)).generate(
            project_a.id, experiment_a.id
        )
    assert InsightRepository(db_session).list_for_experiment(experiment_a.id) == []


def test_failed_run_reference_rejected(db_session: Session) -> None:
    # persona 1 completes both variants; persona 2 fails on Variant A only,
    # so both variants still have >=1 completed run (eligibility passes)
    # while a real failed run exists in the experiment to reference.
    project, experiment, _personas, runs = seed_completed_experiment(
        db_session,
        persona_count=2,
        repeat_count=1,
        responses=[
            make_simulation_call_result(),
            LLMTimeoutError("timed out"),
            make_simulation_call_result(),
            make_simulation_call_result(),
        ],
    )
    failed_run_id = next(run.id for run in runs if run.status.value == "failed")
    raw = {
        "insights": [
            {
                "category": "strength",
                "variant_scope": "both",
                "title": "References a failed run",
                "summary": "Cites a run ID that never completed.",
                "frequency": 1,
                "persona_count": 1,
                "supporting_run_ids": [failed_run_id],
                "supporting_evidence_ids": [],
                "confidence_level": "low",
            }
        ]
    }
    with pytest.raises(ProviderError):
        InsightGenerationService(db_session, _RawInsightProvider(raw)).generate(
            project.id, experiment.id
        )
    assert InsightRepository(db_session).list_for_experiment(experiment.id) == []


def test_fabricated_evidence_id_rejected(db_session: Session) -> None:
    project, experiment, _personas, runs = seed_completed_experiment(
        db_session, persona_count=1, repeat_count=1
    )
    completed_ids = _completed_ids(runs)
    raw = {
        "insights": [
            {
                "category": "strength",
                "variant_scope": "both",
                "title": "Fabricated evidence",
                "summary": "Cites an evidence ID never supplied.",
                "frequency": len(completed_ids),
                "persona_count": 1,
                "supporting_run_ids": completed_ids,
                "supporting_evidence_ids": [999_999],
                "confidence_level": "low",
            }
        ]
    }
    with pytest.raises(ProviderError):
        InsightGenerationService(db_session, _RawInsightProvider(raw)).generate(
            project.id, experiment.id
        )
    assert InsightRepository(db_session).list_for_experiment(experiment.id) == []


def test_unsupported_evidence_reference_rejected(db_session: Session) -> None:
    # Evidence item 1 exists and is cited by variant A's run, but not by
    # variant B's run in this fixture; citing it via variant B's run ID
    # only is rejected as "unsupported" for that specific supporting run.
    project, experiment, _personas, runs = seed_completed_experiment(
        db_session,
        persona_count=1,
        repeat_count=1,
        responses=[
            make_simulation_call_result(evidence_item_id=1),
            make_simulation_call_result(evidence_item_id=None),
        ],
    )
    variant_b_run_id = _completed_ids(runs)[1]
    raw = {
        "insights": [
            {
                "category": "strength",
                "variant_scope": "B",
                "title": "Unsupported evidence",
                "summary": "Cites evidence not referenced by this run.",
                "frequency": 1,
                "persona_count": 1,
                "supporting_run_ids": [variant_b_run_id],
                "supporting_evidence_ids": [1],
                "confidence_level": "low",
            }
        ]
    }
    with pytest.raises(ProviderError):
        InsightGenerationService(db_session, _RawInsightProvider(raw)).generate(
            project.id, experiment.id
        )
    assert InsightRepository(db_session).list_for_experiment(experiment.id) == []


def test_incorrect_frequency_rejected(db_session: Session) -> None:
    project, experiment, _personas, runs = seed_completed_experiment(
        db_session, persona_count=1, repeat_count=1
    )
    completed_ids = _completed_ids(runs)
    raw = {
        "insights": [
            {
                "category": "strength",
                "variant_scope": "both",
                "title": "Wrong frequency",
                "summary": "Frequency does not match supporting run count.",
                "frequency": len(completed_ids) + 5,
                "persona_count": 1,
                "supporting_run_ids": completed_ids,
                "supporting_evidence_ids": [],
                "confidence_level": "low",
            }
        ]
    }
    with pytest.raises(ProviderError):
        InsightGenerationService(db_session, _RawInsightProvider(raw)).generate(
            project.id, experiment.id
        )
    assert InsightRepository(db_session).list_for_experiment(experiment.id) == []


def test_incorrect_persona_count_rejected(db_session: Session) -> None:
    project, experiment, _personas, runs = seed_completed_experiment(
        db_session, persona_count=2, repeat_count=1
    )
    completed_ids = _completed_ids(runs)
    raw = {
        "insights": [
            {
                "category": "strength",
                "variant_scope": "both",
                "title": "Wrong persona count",
                "summary": "Persona count does not match distinct personas.",
                "frequency": len(completed_ids),
                "persona_count": 99,
                "supporting_run_ids": completed_ids,
                "supporting_evidence_ids": [],
                "confidence_level": "low",
            }
        ]
    }
    with pytest.raises(ProviderError):
        InsightGenerationService(db_session, _RawInsightProvider(raw)).generate(
            project.id, experiment.id
        )
    assert InsightRepository(db_session).list_for_experiment(experiment.id) == []


def test_list_for_experiment_after_generation(db_session: Session) -> None:
    project, experiment, _personas, runs = seed_completed_experiment(
        db_session, persona_count=2, repeat_count=1
    )
    completed_ids = _completed_ids(runs)
    provider = FakeInsightProvider(
        result=make_insight_generation_result(supporting_run_ids=completed_ids, persona_count=2)
    )
    service = InsightGenerationService(db_session, provider)
    service.generate(project.id, experiment.id)

    listed = service.list_for_experiment(project.id, experiment.id)
    assert len(listed) == 1


def test_list_for_experiment_returns_404_when_none_generated(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    service = InsightGenerationService(db_session, FakeInsightProvider())

    with pytest.raises(NotFoundError):
        service.list_for_experiment(project.id, experiment.id)
