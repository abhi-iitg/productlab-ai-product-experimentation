"""Business logic for controlled two-variant experiment execution (Stage 5).

Owns the full execution workflow: verify the experiment is a draft with
explicit confirmation, validate the selected personas/variants still exist,
enforce the deterministic 30-run limit, verify provider configuration,
flip the experiment to `running`, then execute the run matrix synchronously
in stable order (Variant A before B, persona ID ascending, repetition index
ascending) — one context build + one provider call per run.

Transaction strategy intentionally differs from `PersonaGenerationService`,
which persists an entire generation batch atomically (all-or-nothing).
Here, each run result (completed or failed) is committed independently as
soon as it is known, so:

- a provider failure on run N does not erase runs 1..N-1 that already
  succeeded, and
- the failure explorer can inspect exactly which runs failed and why, while
  the experiment is still executing.

The experiment's `running` status is also committed before any run is
dispatched (not batched with the final status), specifically so a second,
concurrent `execute()` call on the same experiment sees `running` rather
than `draft` and is rejected — preventing duplicate execution.
"""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    ConflictError,
    InvalidRequestError,
    NotFoundError,
    ProviderConfigurationError,
)
from app.llm.exceptions import (
    LLMConfigurationError,
    LLMEmptyOutputError,
    LLMInvalidEvidenceReferenceError,
    LLMInvalidSchemaError,
    LLMMalformedJSONError,
    LLMProviderError,
    LLMRateLimitError,
    LLMStatusError,
    LLMTimeoutError,
)
from app.llm.simulation_context import SimulationContextTooLargeError, build_simulation_context
from app.llm.simulation_prompts import SIMULATION_PROMPT_VERSION
from app.llm.simulation_provider import SimulationLLMProvider
from app.models.experiment import Experiment, ExperimentStatus
from app.models.persona import Persona
from app.models.project import Project
from app.models.simulation_run import FailureType
from app.models.variant import Variant, VariantKey
from app.repositories.evidence import EvidenceRepository
from app.repositories.experiment import ExperimentRepository
from app.repositories.persona import PersonaRepository
from app.repositories.project import ProjectRepository
from app.repositories.simulation_run import SimulationRunRepository
from app.schemas.experiment import ExperimentExecuteRequest, ExperimentExecutionSummary
from app.schemas.simulation_run import SimulationCallResult
from app.services.experiment import MAX_SIMULATION_RUNS

_VARIANT_COUNT = 2


class ExperimentExecutionService:
    def __init__(
        self, db: Session, provider: SimulationLLMProvider, settings: Settings | None = None
    ) -> None:
        self.db = db
        self.provider = provider
        self._settings = settings or get_settings()
        self.projects = ProjectRepository(db)
        self.personas = PersonaRepository(db)
        self.evidence = EvidenceRepository(db)
        self.experiments = ExperimentRepository(db)
        self.runs = SimulationRunRepository(db)

    def execute(
        self, project_id: int, experiment_id: int, request: ExperimentExecuteRequest
    ) -> ExperimentExecutionSummary:
        project = self._get_project_or_404(project_id)
        experiment = self._get_experiment_or_404(project_id, experiment_id)

        if experiment.status != ExperimentStatus.DRAFT:
            raise ConflictError(
                f"Experiment {experiment_id} has already started or completed execution."
            )

        personas = self._validate_personas_still_valid(project_id, experiment)
        variant_a, variant_b = self._validate_variants(experiment)

        total_runs = len(personas) * _VARIANT_COUNT * experiment.repeat_count
        if total_runs > MAX_SIMULATION_RUNS:
            raise InvalidRequestError(
                f"Calculated {total_runs} simulation runs (personas x 2 variants x "
                f"repeat_count) exceeds the maximum of {MAX_SIMULATION_RUNS}."
            )

        try:
            self.provider.ensure_configured()
        except LLMConfigurationError as exc:
            raise ProviderConfigurationError("The AI provider is not configured.") from exc

        started_at = datetime.now(UTC)
        self.experiments.update_status(experiment, ExperimentStatus.RUNNING, started_at=started_at)
        self._commit()

        completed_count = 0
        failed_count = 0
        for variant in (variant_a, variant_b):
            for persona in personas:
                for repetition_index in range(experiment.repeat_count):
                    succeeded = self._execute_single_run(
                        project, experiment, variant, persona, repetition_index
                    )
                    if succeeded:
                        completed_count += 1
                    else:
                        failed_count += 1

        final_status = self._determine_final_status(completed_count, failed_count)
        completed_at = datetime.now(UTC)
        self.experiments.update_status(experiment, final_status, completed_at=completed_at)
        self._commit()

        return ExperimentExecutionSummary(
            project_id=project_id,
            experiment_id=experiment_id,
            status=final_status,
            total_runs=total_runs,
            completed_runs=completed_count,
            failed_runs=failed_count,
            prompt_version=SIMULATION_PROMPT_VERSION,
            model_name=self.provider.model_name,
            started_at=started_at,
            completed_at=completed_at,
        )

    def _execute_single_run(
        self,
        project: Project,
        experiment: Experiment,
        variant: Variant,
        persona: Persona,
        repetition_index: int,
    ) -> bool:
        allowed_evidence_ids = {ref["evidence_item_id"] for ref in persona.evidence_references}
        project_evidence = self.evidence.list_for_project(project.id)
        persona_evidence = [item for item in project_evidence if item.id in allowed_evidence_ids]

        try:
            context = build_simulation_context(
                project=project,
                experiment=experiment,
                variant=variant,
                persona=persona,
                evidence_items=persona_evidence,
            )
        except SimulationContextTooLargeError as exc:
            self._persist_failed_run(
                experiment, variant, persona, repetition_index, FailureType.CONTEXT_LIMIT, str(exc)
            )
            return False

        try:
            result = self.provider.run_simulation(
                context=context, allowed_evidence_ids=allowed_evidence_ids
            )
        except LLMConfigurationError:
            self._persist_failed_run(
                experiment,
                variant,
                persona,
                repetition_index,
                FailureType.CONFIGURATION_ERROR,
                "The AI provider is not configured.",
            )
            return False
        except LLMTimeoutError:
            self._persist_failed_run(
                experiment,
                variant,
                persona,
                repetition_index,
                FailureType.TIMEOUT,
                "The AI provider request timed out.",
            )
            return False
        except LLMRateLimitError:
            self._persist_failed_run(
                experiment,
                variant,
                persona,
                repetition_index,
                FailureType.RATE_LIMIT,
                "The AI provider rate limit was exceeded.",
            )
            return False
        except LLMEmptyOutputError:
            self._persist_failed_run(
                experiment,
                variant,
                persona,
                repetition_index,
                FailureType.EMPTY_OUTPUT,
                "The AI provider returned an empty response.",
            )
            return False
        except LLMMalformedJSONError:
            self._persist_failed_run(
                experiment,
                variant,
                persona,
                repetition_index,
                FailureType.MALFORMED_JSON,
                "The AI provider returned malformed JSON.",
            )
            return False
        except LLMInvalidEvidenceReferenceError:
            self._persist_failed_run(
                experiment,
                variant,
                persona,
                repetition_index,
                FailureType.INVALID_EVIDENCE_REFERENCE,
                "The AI provider response cited evidence not available to this persona.",
            )
            return False
        except LLMInvalidSchemaError:
            self._persist_failed_run(
                experiment,
                variant,
                persona,
                repetition_index,
                FailureType.INVALID_SCHEMA,
                "The AI provider response did not match the required schema.",
            )
            return False
        except (LLMStatusError, LLMProviderError):
            self._persist_failed_run(
                experiment,
                variant,
                persona,
                repetition_index,
                FailureType.PROVIDER_ERROR,
                "The AI provider was unable to complete the request.",
            )
            return False
        except Exception:
            self._persist_failed_run(
                experiment,
                variant,
                persona,
                repetition_index,
                FailureType.UNEXPECTED_ERROR,
                "An unexpected error occurred while running the simulation.",
            )
            return False

        self._persist_completed_run(experiment, variant, persona, repetition_index, result)
        return True

    def _persist_failed_run(
        self,
        experiment: Experiment,
        variant: Variant,
        persona: Persona,
        repetition_index: int,
        failure_type: FailureType,
        failure_message: str,
    ) -> None:
        data = {
            "prompt_version": SIMULATION_PROMPT_VERSION,
            "model_name": self.provider.model_name,
            "failure_type": failure_type,
            "failure_message": failure_message,
            "completed_at": datetime.now(UTC),
        }
        self.runs.create_failed(
            experiment_id=experiment.id,
            variant_id=variant.id,
            persona_id=persona.id,
            repetition_index=repetition_index,
            data=data,
        )
        self._commit()

    def _persist_completed_run(
        self,
        experiment: Experiment,
        variant: Variant,
        persona: Persona,
        repetition_index: int,
        result: SimulationCallResult,
    ) -> None:
        output = result.output
        data = {
            "task_outcome": output.task_outcome,
            "clarity_score": output.clarity_score,
            "perceived_value_score": output.perceived_value_score,
            "adoption_intent_score": output.adoption_intent_score,
            "response_summary": output.response_summary,
            "positive_signals": output.positive_signals,
            "objections": output.objections,
            "confusion_points": output.confusion_points,
            "feature_requests": output.feature_requests,
            "uncertainty_notes": output.uncertainty_notes,
            "evidence_references": [ref.model_dump() for ref in output.evidence_references],
            "prompt_version": SIMULATION_PROMPT_VERSION,
            "model_name": self.provider.model_name,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "latency_ms": result.latency_ms,
            "estimated_cost_usd": self._estimate_cost(result.input_tokens, result.output_tokens),
            "completed_at": datetime.now(UTC),
        }
        self.runs.create_completed(
            experiment_id=experiment.id,
            variant_id=variant.id,
            persona_id=persona.id,
            repetition_index=repetition_index,
            data=data,
        )
        self._commit()

    def _estimate_cost(self, input_tokens: int | None, output_tokens: int | None) -> Decimal | None:
        """Estimate cost from user-configured per-1M-token pricing.

        Null whenever pricing isn't configured or token counts aren't
        available — never a hardcoded, potentially stale provider price,
        and never presented as an exact figure.
        """
        input_rate = self._settings.OPENAI_INPUT_COST_PER_1M
        output_rate = self._settings.OPENAI_OUTPUT_COST_PER_1M
        if input_tokens is None or output_tokens is None:
            return None
        if input_rate is None or output_rate is None:
            return None
        million = Decimal(1_000_000)
        input_cost = (Decimal(input_tokens) / million) * input_rate
        output_cost = (Decimal(output_tokens) / million) * output_rate
        return input_cost + output_cost

    def _determine_final_status(self, completed: int, failed: int) -> ExperimentStatus:
        if failed == 0:
            return ExperimentStatus.COMPLETED
        if completed == 0:
            return ExperimentStatus.FAILED
        return ExperimentStatus.PARTIALLY_COMPLETED

    def _validate_variants(self, experiment: Experiment) -> tuple[Variant, Variant]:
        variants_by_key = {variant.key: variant for variant in experiment.variants}
        if set(variants_by_key.keys()) != {VariantKey.A, VariantKey.B}:
            raise InvalidRequestError(
                "Experiment must have exactly one Variant A and one Variant B."
            )
        return variants_by_key[VariantKey.A], variants_by_key[VariantKey.B]

    def _validate_personas_still_valid(
        self, project_id: int, experiment: Experiment
    ) -> list[Persona]:
        persona_ids = self.experiments.get_persona_ids(experiment.id)
        if not persona_ids:
            raise InvalidRequestError(f"Experiment {experiment.id} has no selected personas.")

        personas = []
        for persona_id in persona_ids:
            persona = self.personas.get_by_id(persona_id)
            if persona is None or persona.project_id != project_id:
                raise InvalidRequestError(
                    f"Persona {persona_id} no longer exists in project {project_id}."
                )
            personas.append(persona)
        return personas

    def _get_project_or_404(self, project_id: int) -> Project:
        project = self.projects.get_by_id(project_id)
        if project is None:
            raise NotFoundError(f"Project {project_id} not found.")
        return project

    def _get_experiment_or_404(self, project_id: int, experiment_id: int) -> Experiment:
        experiment = self.experiments.get_by_project_and_id(project_id, experiment_id)
        if experiment is None:
            raise NotFoundError(f"Experiment {experiment_id} not found.")
        return experiment

    def _commit(self) -> None:
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
