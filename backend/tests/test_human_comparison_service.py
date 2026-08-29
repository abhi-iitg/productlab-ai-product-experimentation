"""HumanComparisonService: deterministic synthetic/human aggregation,
exact theme matching, metric-direction alignment, task-outcome deltas, and
data-quality warnings.

No LLM provider is imported or mocked anywhere in this file — the service
under test makes no provider calls.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.llm.exceptions import LLMTimeoutError
from app.models.experiment import ExperimentStatus
from app.models.human_feedback import HumanFeedback, HumanFeedbackSourceMethod
from app.models.variant import VariantKey
from app.repositories.human_feedback import HumanFeedbackRepository
from app.schemas.experiment import ExperimentCreate
from app.services.experiment import ExperimentService
from app.services.human_comparison import HumanComparisonService
from tests.experiment_helpers import (
    experiment_create_payload,
    seed_completed_experiment,
    seed_project_with_personas,
)
from tests.fakes import make_simulation_call_result


def _add_feedback(db_session: Session, experiment_id: int, **overrides: object) -> HumanFeedback:
    defaults: dict[str, object] = {
        "participant_label": "Participant 1",
        "variant_key": VariantKey.A,
        "task_outcome": "completed",
        "clarity_score": 4,
        "perceived_value_score": 4,
        "adoption_intent_score": 4,
        "feedback_summary": "Completed the task with minimal confusion.",
        "positive_signals": [],
        "objections": [],
        "confusion_points": [],
        "feature_requests": [],
        "uncertainty_notes": [],
        "source_method": HumanFeedbackSourceMethod.USABILITY_TEST,
        "session_date": None,
    }
    defaults.update(overrides)
    feedback = HumanFeedbackRepository(db_session).create_for_experiment(experiment_id, defaults)
    db_session.commit()
    return feedback


def _by_variant(items: list, variant_key: VariantKey):
    return next(item for item in items if item.variant_key == variant_key)


def test_project_not_found(db_session: Session) -> None:
    with pytest.raises(NotFoundError):
        HumanComparisonService(db_session).compare(999_999, 1)


def test_experiment_not_found(db_session: Session) -> None:
    project, _evidence, _personas = seed_project_with_personas(db_session)
    with pytest.raises(NotFoundError):
        HumanComparisonService(db_session).compare(project.id, 999_999)


def test_cross_project_experiment_returns_not_found(db_session: Session) -> None:
    _project_a, experiment_a, _p_a, _r_a = seed_completed_experiment(db_session)
    project_b, _experiment_b, _p_b, _r_b = seed_completed_experiment(db_session)

    with pytest.raises(NotFoundError):
        HumanComparisonService(db_session).compare(project_b.id, experiment_a.id)


@pytest.mark.parametrize(
    "status", [ExperimentStatus.DRAFT, ExperimentStatus.RUNNING, ExperimentStatus.FAILED]
)
def test_ineligible_status_rejected(db_session: Session, status: ExperimentStatus) -> None:
    project, _evidence, personas = seed_project_with_personas(db_session)
    experiment = ExperimentService(db_session).create(
        project.id, ExperimentCreate(**experiment_create_payload([p.id for p in personas]))
    )
    experiment.status = status
    db_session.commit()

    with pytest.raises(ConflictError):
        HumanComparisonService(db_session).compare(project.id, experiment.id)


def test_zero_completed_synthetic_runs_rejected(db_session: Session) -> None:
    project, _evidence, personas = seed_project_with_personas(db_session)
    experiment = ExperimentService(db_session).create(
        project.id, ExperimentCreate(**experiment_create_payload([p.id for p in personas]))
    )
    experiment.status = ExperimentStatus.COMPLETED
    db_session.commit()

    with pytest.raises(ConflictError):
        HumanComparisonService(db_session).compare(project.id, experiment.id)


def test_empty_human_feedback_comparison_is_still_200_shaped(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(db_session)

    result = HumanComparisonService(db_session).compare(project.id, experiment.id)

    assert result.human_summary[0].feedback_record_count == 0
    assert result.human_summary[1].feedback_record_count == 0
    assert result.variant_comparisons[0].human.unique_participant_count == 0
    assert any("No real-participant feedback" in w for w in result.data_quality_warnings)


def test_synthetic_aggregation_correctness(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(
        db_session,
        persona_count=2,
        repeat_count=1,
        responses=[
            make_simulation_call_result(
                clarity_score=4,
                perceived_value_score=4,
                adoption_intent_score=4,
                task_outcome="completed",
                positive_signals=["Clear layout"],
            ),
            make_simulation_call_result(
                clarity_score=2,
                perceived_value_score=2,
                adoption_intent_score=2,
                task_outcome="partially_completed",
                positive_signals=[],
                objections=["Confusing labels"],
            ),
            make_simulation_call_result(
                clarity_score=5,
                perceived_value_score=5,
                adoption_intent_score=5,
                task_outcome="completed",
                positive_signals=["Clear layout"],
                feature_requests=["Add tooltips"],
            ),
            make_simulation_call_result(
                clarity_score=5,
                perceived_value_score=5,
                adoption_intent_score=5,
                task_outcome="completed",
                positive_signals=["Fast checkout"],
            ),
        ],
    )

    result = HumanComparisonService(db_session).compare(project.id, experiment.id)

    syn_a = _by_variant(result.synthetic_summary, VariantKey.A)
    syn_b = _by_variant(result.synthetic_summary, VariantKey.B)
    assert syn_a.completed_run_count == 2
    assert syn_a.represented_persona_count == 2
    assert syn_a.average_clarity_score == 3.0
    assert syn_a.task_outcome_distribution.completed == 1
    assert syn_a.task_outcome_distribution.partially_completed == 1
    assert syn_a.positive_signals == ["Clear layout"]

    assert syn_b.completed_run_count == 2
    assert syn_b.average_clarity_score == 5.0
    assert syn_b.task_outcome_distribution.completed == 2
    assert sorted(syn_b.positive_signals) == ["Clear layout", "Fast checkout"]
    assert syn_b.feature_requests == ["Add tooltips"]


def test_human_aggregation_correctness(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    _add_feedback(
        db_session,
        experiment.id,
        participant_label="Participant 1",
        variant_key=VariantKey.A,
        clarity_score=4,
        perceived_value_score=4,
        adoption_intent_score=4,
        task_outcome="completed",
        positive_signals=["clear layout"],
    )
    _add_feedback(
        db_session,
        experiment.id,
        participant_label="Participant 2",
        variant_key=VariantKey.A,
        clarity_score=2,
        perceived_value_score=2,
        adoption_intent_score=2,
        task_outcome="failed",
        objections=["Confusing labels"],
    )

    result = HumanComparisonService(db_session).compare(project.id, experiment.id)

    hum_a = _by_variant(result.human_summary, VariantKey.A)
    assert hum_a.feedback_record_count == 2
    assert hum_a.unique_participant_count == 2
    assert hum_a.average_clarity_score == 3.0
    assert hum_a.task_outcome_distribution.completed == 1
    assert hum_a.task_outcome_distribution.failed == 1
    assert hum_a.positive_signals == ["clear layout"]


def test_theme_comparison_shared_synthetic_only_and_human_only(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(
        db_session,
        persona_count=1,
        repeat_count=1,
        responses=[
            make_simulation_call_result(positive_signals=["Clear layout", "Fast checkout"]),
            make_simulation_call_result(),
        ],
    )
    # Case- and whitespace-only difference from the synthetic entry -> shared.
    _add_feedback(
        db_session,
        experiment.id,
        variant_key=VariantKey.A,
        positive_signals=["  clear   layout  ", "Great support"],
    )

    result = HumanComparisonService(db_session).compare(project.id, experiment.id)

    theme = next(
        t
        for t in result.theme_comparisons
        if t.variant_key == VariantKey.A and t.category == "positive_signals"
    )
    assert theme.shared_themes == ["Clear layout"]
    assert theme.synthetic_only_themes == ["Fast checkout"]
    assert theme.human_only_themes == ["Great support"]


def test_metric_direction_aligned(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(
        db_session,
        persona_count=1,
        repeat_count=1,
        responses=[
            make_simulation_call_result(clarity_score=5),
            make_simulation_call_result(clarity_score=2),
        ],
    )
    _add_feedback(db_session, experiment.id, variant_key=VariantKey.A, clarity_score=5)
    _add_feedback(
        db_session,
        experiment.id,
        participant_label="Participant 2",
        variant_key=VariantKey.B,
        clarity_score=2,
    )

    result = HumanComparisonService(db_session).compare(project.id, experiment.id)

    clarity = next(m for m in result.metric_direction_comparisons if m.metric == "clarity")
    assert clarity.synthetic_direction == "A_higher"
    assert clarity.human_direction == "A_higher"
    assert clarity.alignment == "aligned"


def test_metric_direction_not_aligned(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(
        db_session,
        persona_count=1,
        repeat_count=1,
        responses=[
            make_simulation_call_result(clarity_score=5),
            make_simulation_call_result(clarity_score=2),
        ],
    )
    _add_feedback(db_session, experiment.id, variant_key=VariantKey.A, clarity_score=2)
    _add_feedback(
        db_session,
        experiment.id,
        participant_label="Participant 2",
        variant_key=VariantKey.B,
        clarity_score=5,
    )

    result = HumanComparisonService(db_session).compare(project.id, experiment.id)

    clarity = next(m for m in result.metric_direction_comparisons if m.metric == "clarity")
    assert clarity.synthetic_direction == "A_higher"
    assert clarity.human_direction == "B_higher"
    assert clarity.alignment == "not_aligned"


def test_metric_direction_equal(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(
        db_session,
        persona_count=1,
        repeat_count=1,
        responses=[
            make_simulation_call_result(clarity_score=3),
            make_simulation_call_result(clarity_score=3),
        ],
    )

    result = HumanComparisonService(db_session).compare(project.id, experiment.id)

    clarity = next(m for m in result.metric_direction_comparisons if m.metric == "clarity")
    assert clarity.synthetic_direction == "equal"


def test_metric_direction_insufficient_data_when_human_side_missing(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    _add_feedback(db_session, experiment.id, variant_key=VariantKey.A)
    # No feedback at all for Variant B.

    result = HumanComparisonService(db_session).compare(project.id, experiment.id)

    clarity = next(m for m in result.metric_direction_comparisons if m.metric == "clarity")
    assert clarity.human_direction == "insufficient_data"
    assert clarity.alignment == "insufficient_data"


def test_task_outcome_completion_rate_difference(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(
        db_session,
        persona_count=2,
        repeat_count=1,
        responses=[
            make_simulation_call_result(task_outcome="completed"),
            make_simulation_call_result(task_outcome="completed"),
            make_simulation_call_result(task_outcome="completed"),
            make_simulation_call_result(task_outcome="completed"),
        ],
    )
    _add_feedback(db_session, experiment.id, variant_key=VariantKey.A, task_outcome="failed")

    result = HumanComparisonService(db_session).compare(project.id, experiment.id)

    outcome_a = _by_variant(result.task_outcome_comparisons, VariantKey.A)
    assert outcome_a.synthetic_completion_rate == 1.0
    assert outcome_a.human_completion_rate == 0.0
    assert outcome_a.absolute_difference == 1.0

    outcome_b = _by_variant(result.task_outcome_comparisons, VariantKey.B)
    assert outcome_b.human_completion_rate is None
    assert outcome_b.absolute_difference is None


def test_warning_one_real_participant(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    _add_feedback(db_session, experiment.id)

    result = HumanComparisonService(db_session).compare(project.id, experiment.id)

    assert any("Only one real participant" in w for w in result.data_quality_warnings)
    assert not any("Fewer than three" in w for w in result.data_quality_warnings)


def test_warning_fewer_than_three_real_participants(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    _add_feedback(db_session, experiment.id, participant_label="Participant 1")
    _add_feedback(
        db_session, experiment.id, participant_label="Participant 2", variant_key=VariantKey.B
    )

    result = HumanComparisonService(db_session).compare(project.id, experiment.id)

    assert any("Fewer than three" in w for w in result.data_quality_warnings)
    assert not any("Only one real participant" in w for w in result.data_quality_warnings)


def test_warning_missing_variant_feedback(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    _add_feedback(db_session, experiment.id, variant_key=VariantKey.A)

    result = HumanComparisonService(db_session).compare(project.id, experiment.id)

    assert any(
        "Variant B has no real-participant feedback" in w for w in result.data_quality_warnings
    )


def test_warning_severe_sample_imbalance(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    for i in range(6):
        _add_feedback(
            db_session,
            experiment.id,
            participant_label=f"Participant A{i}",
            variant_key=VariantKey.A,
        )
    _add_feedback(
        db_session, experiment.id, participant_label="Participant B1", variant_key=VariantKey.B
    )

    result = HumanComparisonService(db_session).compare(project.id, experiment.id)

    assert any("severely imbalanced" in w for w in result.data_quality_warnings)


def test_warning_variant_with_zero_completed_synthetic_runs(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(
        db_session,
        persona_count=1,
        repeat_count=1,
        responses=[make_simulation_call_result(), LLMTimeoutError("timed out")],
    )

    result = HumanComparisonService(db_session).compare(project.id, experiment.id)

    syn_b = _by_variant(result.synthetic_summary, VariantKey.B)
    assert syn_b.completed_run_count == 0
    assert any(
        "Variant B has zero completed synthetic runs" in w for w in result.data_quality_warnings
    )


def test_warning_no_shared_themes(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(
        db_session,
        persona_count=1,
        repeat_count=1,
        responses=[
            make_simulation_call_result(positive_signals=["Clear layout"]),
            make_simulation_call_result(),
        ],
    )
    _add_feedback(
        db_session, experiment.id, variant_key=VariantKey.A, positive_signals=["Totally different"]
    )

    result = HumanComparisonService(db_session).compare(project.id, experiment.id)

    assert result.shared_theme_count == 0
    assert any("No exactly matching themes" in w for w in result.data_quality_warnings)


def test_exact_match_limitation_warning_always_present(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(db_session)

    result = HumanComparisonService(db_session).compare(project.id, experiment.id)

    assert any("intentionally conservative" in w for w in result.data_quality_warnings)


def test_pii_reminder_only_present_when_feedback_exists(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(db_session)

    empty_result = HumanComparisonService(db_session).compare(project.id, experiment.id)
    assert not any("personally identifiable" in w for w in empty_result.data_quality_warnings)

    _add_feedback(db_session, experiment.id)
    result = HumanComparisonService(db_session).compare(project.id, experiment.id)
    assert any("personally identifiable" in w for w in result.data_quality_warnings)


def test_warning_decision_memo_predates_real_feedback(db_session: Session) -> None:
    from app.repositories.decision_memo import DecisionMemoRepository

    project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    DecisionMemoRepository(db_session).create_for_experiment(
        experiment.id,
        {
            "recommendation": "iterate",
            "executive_summary": "Iterate based on synthetic findings.",
            "supporting_findings": [],
            "weakest_assumptions": [],
            "recommended_product_changes": [],
            "risks": [],
            "uncertain_conclusions": [],
            "recommended_success_metrics": [],
            "real_user_test": {
                "objective": "Validate with real users.",
                "method": "Moderated usability test.",
                "target_participants": ["Early adopters"],
                "sample_size_rationale": "Small qualitative sample is sufficient.",
                "tasks_or_questions": ["Complete onboarding."],
                "success_metrics": ["Task completion"],
                "stopping_rule": "Stop after 5 sessions.",
            },
            "supporting_insight_ids": [],
            "prompt_version": "decision-memo-v1",
            "model_name": "fake-decision-memo-model",
        },
    )
    db_session.commit()

    # The feedback record's created_at (set by the model default at flush
    # time) will be later than the memo's, since it's created afterward.
    _add_feedback(db_session, experiment.id)

    result = HumanComparisonService(db_session).compare(project.id, experiment.id)

    assert any("predates" in w for w in result.data_quality_warnings)


def test_interpretation_notice_is_fixed_text(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(db_session)

    result = HumanComparisonService(db_session).compare(project.id, experiment.id)

    assert "does not establish statistical significance" in result.interpretation_notice


def test_stable_ordering_across_repeated_calls(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    _add_feedback(db_session, experiment.id, positive_signals=["Zebra", "Apple"])

    first = HumanComparisonService(db_session).compare(project.id, experiment.id)
    second = HumanComparisonService(db_session).compare(project.id, experiment.id)

    assert first == second


def test_compare_makes_no_database_writes(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    _add_feedback(db_session, experiment.id)

    before = db_session.execute(select(HumanFeedback)).scalars().all()
    HumanComparisonService(db_session).compare(project.id, experiment.id)
    after = db_session.execute(select(HumanFeedback)).scalars().all()

    assert len(before) == len(after)
    assert not db_session.dirty
    assert not db_session.new
