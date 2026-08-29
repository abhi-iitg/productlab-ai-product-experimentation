"""Shared object-graph builders for Stage 5 (Experiment) tests.

Stage 5 tests need a deeper object graph than earlier stages (a persisted
Project, EvidenceItem, and Persona before an Experiment/Variant/
SimulationRun can even be constructed), so — unlike the smaller per-file
`_make_project` helpers in earlier test modules — that graph is centralized
here to keep the many Stage 5 test files focused on what they're actually
asserting.
"""

from sqlalchemy.orm import Session

from app.models.evidence_item import EvidenceItem, EvidenceType
from app.models.experiment import Experiment
from app.models.persona import ConfidenceLevel, Persona
from app.models.project import Project
from app.models.simulation_run import SimulationRun
from app.schemas.experiment import ExperimentCreate, ExperimentExecuteRequest
from app.schemas.simulation_run import SimulationCallResult
from app.services.experiment import ExperimentService
from app.services.experiment_execution import ExperimentExecutionService
from tests.fakes import FakeSimulationProvider, make_simulation_call_result


def make_project(**overrides: object) -> Project:
    defaults: dict[str, object] = {
        "name": "Portfolio Discovery Tool",
        "problem_statement": "Teams decide on intuition alone.",
        "target_user": "Early-stage product managers.",
        "product_hypothesis": "Evidence-grounded personas surface weak assumptions.",
        "success_metric": "Time to a decision memo.",
        "assumptions": ["Users have existing evidence."],
    }
    defaults.update(overrides)
    return Project(**defaults)


def make_evidence_item(project_id: int, **overrides: object) -> EvidenceItem:
    defaults: dict[str, object] = {
        "project_id": project_id,
        "evidence_type": EvidenceType.INTERVIEW_NOTE,
        "title": "Interview notes",
        "content": "Users struggled to understand the value proposition.",
        "source_label": None,
    }
    defaults.update(overrides)
    return EvidenceItem(**defaults)


def make_persona(project_id: int, evidence_item_id: int, **overrides: object) -> Persona:
    defaults: dict[str, object] = {
        "project_id": project_id,
        "name": "Alex the Adopter",
        "segment_label": "Early Adopter",
        "summary": "An early adopter evaluating the product.",
        "goals": ["Understand the value quickly."],
        "pain_points": ["Confusing onboarding."],
        "constraints": ["Limited evaluation time."],
        "behaviors": ["Reads reviews before adopting tools."],
        "evidence_references": [
            {
                "evidence_item_id": evidence_item_id,
                "supported_claims": ["Struggled with onboarding."],
            }
        ],
        "unsupported_assumptions": ["Likely price-sensitive."],
        "confidence_level": ConfidenceLevel.MEDIUM,
        "prompt_version": "persona-v1",
        "model_name": "fake-model-v1",
    }
    defaults.update(overrides)
    return Persona(**defaults)


def seed_project_with_personas(
    db_session: Session, *, persona_count: int = 1
) -> tuple[Project, EvidenceItem, list[Persona]]:
    """Persist a Project, one EvidenceItem, and `persona_count` Personas grounded in it."""
    project = make_project()
    db_session.add(project)
    db_session.commit()

    evidence = make_evidence_item(project.id)
    db_session.add(evidence)
    db_session.commit()

    personas = [
        make_persona(project.id, evidence.id, name=f"Persona {i + 1}") for i in range(persona_count)
    ]
    db_session.add_all(personas)
    db_session.commit()

    return project, evidence, personas


def seed_completed_experiment(
    db_session: Session,
    *,
    persona_count: int = 2,
    repeat_count: int = 1,
    responses: list[SimulationCallResult | Exception] | None = None,
    result: SimulationCallResult | None = None,
    **experiment_overrides: object,
) -> tuple[Project, Experiment, list[Persona], list[SimulationRun]]:
    """Persist and fully execute a two-variant experiment for Stage 6 tests.

    By default every run succeeds identically (citing the seeded evidence
    item). Pass `responses` (a queue consumed in stable run-matrix order —
    Variant A before B, persona ID ascending, repetition ascending) to
    control exactly which runs succeed/fail/disagree, e.g. to build a
    partially_completed experiment or persona-disagreement fixtures.
    """
    project, evidence, personas = seed_project_with_personas(
        db_session, persona_count=persona_count
    )
    experiment_service = ExperimentService(db_session)
    experiment = experiment_service.create(
        project.id,
        ExperimentCreate(
            **experiment_create_payload(
                [p.id for p in personas], repeat_count=repeat_count, **experiment_overrides
            )
        ),
    )

    if responses is not None:
        provider = FakeSimulationProvider(responses=responses)
    else:
        provider = FakeSimulationProvider(
            result=result or make_simulation_call_result(evidence_item_id=evidence.id)
        )

    ExperimentExecutionService(db_session, provider).execute(
        project.id, experiment.id, ExperimentExecuteRequest(confirm_execution=True)
    )

    experiment = experiment_service.get(project.id, experiment.id)
    runs = experiment_service.list_runs(project.id, experiment.id)
    return project, experiment, personas, runs


def experiment_create_payload(persona_ids: list[int], **overrides: object) -> dict:
    payload: dict[str, object] = {
        "name": "Onboarding concept comparison",
        "objective": "Compare two onboarding approaches",
        "hypothesis": "A guided setup will improve clarity",
        "scenario": "Evaluate the onboarding flow and decide whether you could complete setup.",
        "evaluation_criteria": ["Clarity", "Perceived value", "Adoption intent"],
        "repeat_count": 1,
        "persona_ids": persona_ids,
        "variants": [
            {"key": "A", "name": "Self-service onboarding", "description": "No guidance."},
            {"key": "B", "name": "Guided onboarding", "description": "Step-by-step wizard."},
        ],
    }
    payload.update(overrides)
    return payload
