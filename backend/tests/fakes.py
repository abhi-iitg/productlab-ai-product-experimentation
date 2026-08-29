"""Deterministic fake LLM provider for tests.

Implements the same `PersonaLLMProvider` protocol as `OpenAIPersonaProvider`
without ever touching the network, requiring an API key, or calling
OpenAI. Tests inject it via the `get_persona_provider` FastAPI dependency
override (API tests) or construct `PersonaGenerationService` with it
directly (service tests).
"""

from app.llm.exceptions import LLMConfigurationError, LLMProviderError
from app.models.decision_memo import Recommendation
from app.models.insight import InsightCategory, VariantScope
from app.models.persona import ConfidenceLevel
from app.models.simulation_run import TaskOutcome
from app.schemas.decision_memo import DecisionMemoCandidate, RealUserTestPlan
from app.schemas.insight import InsightCandidate, InsightGenerationResult
from app.schemas.persona import EvidenceReference, GeneratedPersona, PersonaGenerationResult
from app.schemas.simulation_run import SimulationCallResult, SimulationOutput


class FakePersonaProvider:
    """Returns a canned result, or raises a canned error, on every call."""

    def __init__(
        self,
        *,
        result: PersonaGenerationResult | None = None,
        error: Exception | None = None,
        model_name: str = "fake-model-v1",
    ) -> None:
        self._result = result
        self._error = error
        self.model_name = model_name
        self.calls: list[dict[str, object]] = []

    def generate_personas(
        self,
        *,
        persona_count: int,
        context: str,
        focus: str | None,
        allowed_evidence_ids: set[int],
    ) -> PersonaGenerationResult:
        self.calls.append(
            {
                "persona_count": persona_count,
                "context": context,
                "focus": focus,
                "allowed_evidence_ids": allowed_evidence_ids,
            }
        )
        if self._error is not None:
            raise self._error
        if self._result is not None:
            return self._result
        raise LLMProviderError("FakePersonaProvider was called with no result or error set.")


def make_generated_persona(
    *,
    name: str = "Alex the Adopter",
    segment_label: str = "Early Adopter",
    summary: str = "An early adopter evaluating the product.",
    evidence_item_id: int,
    supported_claims: list[str] | None = None,
    confidence_level: ConfidenceLevel = ConfidenceLevel.MEDIUM,
    unsupported_assumptions: list[str] | None = None,
) -> GeneratedPersona:
    """Build one schema-valid `GeneratedPersona` referencing a single evidence item."""
    return GeneratedPersona(
        name=name,
        segment_label=segment_label,
        summary=summary,
        goals=["Understand the product's value quickly."],
        pain_points=["Struggles with unclear onboarding."],
        constraints=["Limited time to evaluate new tools."],
        behaviors=["Reads reviews before adopting new products."],
        evidence_references=[
            EvidenceReference(
                evidence_item_id=evidence_item_id,
                supported_claims=supported_claims or ["Struggled with onboarding."],
            )
        ],
        unsupported_assumptions=unsupported_assumptions or [],
        confidence_level=confidence_level,
    )


def make_generation_result(
    *, evidence_item_id: int, persona_count: int = 2
) -> PersonaGenerationResult:
    """Build a schema-valid `PersonaGenerationResult` with `persona_count` personas."""
    personas = [
        make_generated_persona(name=f"Persona {i + 1}", evidence_item_id=evidence_item_id)
        for i in range(persona_count)
    ]
    return PersonaGenerationResult(personas=personas)


class FakeSimulationProvider:
    """Deterministic stand-in for `OpenAISimulationProvider` in tests.

    Each call to `run_simulation` consumes one entry from a configured
    queue of `SimulationCallResult` / `Exception` values, in order — this
    lets a test control exactly which runs in a matrix succeed and which
    fail (e.g. to exercise a `partially_completed` final experiment
    status). Once the queue is exhausted, falls back to a single default
    result/error if one was configured, otherwise raises.
    """

    def __init__(
        self,
        *,
        responses: list[SimulationCallResult | Exception] | None = None,
        result: SimulationCallResult | None = None,
        error: Exception | None = None,
        model_name: str = "fake-simulation-model-v1",
        configured: bool = True,
    ) -> None:
        self._responses = list(responses) if responses is not None else None
        self._default_result = result
        self._default_error = error
        self._configured = configured
        self.model_name = model_name
        self.calls: list[dict[str, object]] = []

    def ensure_configured(self) -> None:
        if not self._configured:
            raise LLMConfigurationError("FakeSimulationProvider is not configured.")

    def run_simulation(
        self, *, context: str, allowed_evidence_ids: set[int]
    ) -> SimulationCallResult:
        self.calls.append({"context": context, "allowed_evidence_ids": allowed_evidence_ids})

        if self._responses:
            item = self._responses.pop(0)
        elif self._default_error is not None:
            item = self._default_error
        elif self._default_result is not None:
            item = self._default_result
        else:
            raise LLMProviderError("FakeSimulationProvider was called with no result or error set.")

        if isinstance(item, Exception):
            raise item
        return item


def make_simulation_output(
    *,
    evidence_item_id: int | None = None,
    supported_claims: list[str] | None = None,
    task_outcome: TaskOutcome = TaskOutcome.COMPLETED,
    clarity_score: int = 4,
    perceived_value_score: int = 4,
    adoption_intent_score: int = 4,
    response_summary: str = "The persona understood the variant and reacted positively.",
    positive_signals: list[str] | None = None,
    objections: list[str] | None = None,
    confusion_points: list[str] | None = None,
    feature_requests: list[str] | None = None,
    uncertainty_notes: list[str] | None = None,
) -> SimulationOutput:
    """Build a schema-valid `SimulationOutput`, optionally citing one evidence item."""
    evidence_references = (
        [
            EvidenceReference(
                evidence_item_id=evidence_item_id,
                supported_claims=supported_claims or ["Matches a known pain point."],
            )
        ]
        if evidence_item_id is not None
        else []
    )
    return SimulationOutput(
        task_outcome=task_outcome,
        clarity_score=clarity_score,
        perceived_value_score=perceived_value_score,
        adoption_intent_score=adoption_intent_score,
        response_summary=response_summary,
        positive_signals=(
            positive_signals if positive_signals is not None else ["Liked the streamlined flow."]
        ),
        objections=objections or [],
        confusion_points=confusion_points or [],
        feature_requests=feature_requests or [],
        uncertainty_notes=uncertainty_notes or [],
        evidence_references=evidence_references,
    )


def make_simulation_call_result(
    *,
    evidence_item_id: int | None = None,
    input_tokens: int | None = 120,
    output_tokens: int | None = 80,
    latency_ms: int = 250,
    **output_overrides: object,
) -> SimulationCallResult:
    """Build a schema-valid `SimulationCallResult` wrapping `make_simulation_output`."""
    return SimulationCallResult(
        output=make_simulation_output(evidence_item_id=evidence_item_id, **output_overrides),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
    )


class FakeInsightProvider:
    """Deterministic stand-in for `OpenAIInsightProvider` in tests.

    Implements the same `InsightLLMProvider` protocol without ever touching
    the network. Returns a canned `InsightGenerationResult`, or raises a
    canned error, on every call.
    """

    def __init__(
        self,
        *,
        result: InsightGenerationResult | None = None,
        error: Exception | None = None,
        model_name: str = "fake-insight-model-v1",
    ) -> None:
        self._result = result
        self._error = error
        self.model_name = model_name
        self.calls: list[dict[str, object]] = []

    def generate_insights(
        self,
        *,
        context: str,
        allowed_run_ids: set[int],
        run_evidence_ids: dict[int, set[int]],
        run_persona_ids: dict[int, int],
    ) -> InsightGenerationResult:
        self.calls.append(
            {
                "context": context,
                "allowed_run_ids": allowed_run_ids,
                "run_evidence_ids": run_evidence_ids,
                "run_persona_ids": run_persona_ids,
            }
        )
        if self._error is not None:
            raise self._error
        if self._result is not None:
            return self._result
        raise LLMProviderError("FakeInsightProvider was called with no result or error set.")


def make_insight_candidate(
    *,
    category: InsightCategory = InsightCategory.STRENGTH,
    variant_scope: VariantScope = VariantScope.BOTH,
    title: str = "Clear onboarding value",
    summary: str = "Personas found the onboarding flow easy to understand.",
    supporting_run_ids: list[int],
    supporting_evidence_ids: list[int] | None = None,
    persona_count: int,
    confidence_level: ConfidenceLevel = ConfidenceLevel.MEDIUM,
) -> InsightCandidate:
    """Build a schema-valid `InsightCandidate`.

    Built via direct construction (not `model_validate` with a validation
    `context`), so `frequency` is always kept consistent with
    `supporting_run_ids` (that check is unconditional) but the
    context-gated reference checks are skipped — matching how a
    ready-to-persist provider result is represented in tests elsewhere in
    this module.
    """
    return InsightCandidate(
        category=category,
        variant_scope=variant_scope,
        title=title,
        summary=summary,
        frequency=len(supporting_run_ids),
        persona_count=persona_count,
        supporting_run_ids=supporting_run_ids,
        supporting_evidence_ids=supporting_evidence_ids or [],
        confidence_level=confidence_level,
    )


def make_insight_generation_result(
    *,
    supporting_run_ids: list[int],
    persona_count: int,
    supporting_evidence_ids: list[int] | None = None,
    insight_count: int = 1,
) -> InsightGenerationResult:
    """Build a schema-valid `InsightGenerationResult` with `insight_count` insights."""
    categories = [
        InsightCategory.STRENGTH,
        InsightCategory.OBJECTION,
        InsightCategory.CONFUSION,
        InsightCategory.FEATURE_REQUEST,
        InsightCategory.UNCERTAINTY,
        InsightCategory.DISAGREEMENT,
    ]
    insights = [
        make_insight_candidate(
            category=categories[i % len(categories)],
            title=f"Insight {i + 1}",
            supporting_run_ids=supporting_run_ids,
            persona_count=persona_count,
            supporting_evidence_ids=supporting_evidence_ids,
        )
        for i in range(insight_count)
    ]
    return InsightGenerationResult(insights=insights)


class FakeDecisionMemoProvider:
    """Deterministic stand-in for `OpenAIDecisionMemoProvider` in tests.

    Implements the same `DecisionMemoLLMProvider` protocol without ever
    touching the network. Returns a canned `DecisionMemoCandidate`, or
    raises a canned error, on every call.
    """

    def __init__(
        self,
        *,
        result: DecisionMemoCandidate | None = None,
        error: Exception | None = None,
        model_name: str = "fake-decision-model-v1",
    ) -> None:
        self._result = result
        self._error = error
        self.model_name = model_name
        self.calls: list[dict[str, object]] = []

    def generate_decision_memo(
        self, *, context: str, allowed_insight_ids: set[int]
    ) -> DecisionMemoCandidate:
        self.calls.append({"context": context, "allowed_insight_ids": allowed_insight_ids})
        if self._error is not None:
            raise self._error
        if self._result is not None:
            return self._result
        raise LLMProviderError("FakeDecisionMemoProvider was called with no result or error set.")


def make_real_user_test_plan(**overrides: object) -> RealUserTestPlan:
    defaults: dict[str, object] = {
        "objective": "Validate whether real users complete setup unaided.",
        "target_participants": ["5-8 early-stage product managers matching the persona segment."],
        "method": "Moderated usability test of the guided setup flow.",
        "sample_size_rationale": (
            "A small qualitative sample is sufficient to surface major usability "
            "blockers before investing in a larger quantitative test."
        ),
        "tasks_or_questions": ["Complete setup without assistance and narrate your reasoning."],
        "success_metrics": ["Task completion rate", "Time to first value"],
        "stopping_rule": "Stop after 5 sessions if the same blocker recurs in at least 4.",
    }
    defaults.update(overrides)
    return RealUserTestPlan(**defaults)


def make_decision_memo_candidate(
    *,
    recommendation: Recommendation = Recommendation.PROCEED,
    executive_summary: str = ("Signal is strong; recommend real-user validation next, not launch."),
    supporting_insight_ids: list[int],
    uncertain_conclusions: list[str] | None = None,
    **overrides: object,
) -> DecisionMemoCandidate:
    """Build a schema-valid `DecisionMemoCandidate`.

    Built via direct construction, so the context-gated
    `supporting_insight_ids` reference check is skipped — matching
    `make_insight_candidate`.
    """
    data: dict[str, object] = {
        "recommendation": recommendation,
        "executive_summary": executive_summary,
        "supporting_findings": ["Personas consistently understood the value proposition."],
        "weakest_assumptions": ["Assumes users will discover the guided flow unaided."],
        "recommended_product_changes": ["Add an inline hint for the guided setup entry point."],
        "risks": ["Evidence library is thin for the enterprise segment."],
        "uncertain_conclusions": (
            uncertain_conclusions
            if uncertain_conclusions is not None
            else ["Model confidence on adoption intent is moderate."]
        ),
        "recommended_success_metrics": ["Setup completion rate among real users."],
        "real_user_test": make_real_user_test_plan(),
        "supporting_insight_ids": supporting_insight_ids,
    }
    data.update(overrides)
    return DecisionMemoCandidate(**data)
