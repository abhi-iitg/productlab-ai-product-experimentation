"""Typed interface the Insight service layer depends on, not the OpenAI SDK.

`InsightGenerationService` is constructed with any object satisfying this
`Protocol` — the real `OpenAIInsightProvider` in production, a
deterministic fake in tests. Implementations raise the typed errors in
`app.llm.exceptions` on failure and otherwise return a fully parsed and
Pydantic-validated `InsightGenerationResult`.
"""

from typing import Protocol

from app.schemas.insight import InsightGenerationResult


class InsightLLMProvider(Protocol):
    """A provider capable of clustering qualitative signals into Insights."""

    @property
    def model_name(self) -> str:
        """The provider/model identifier to record on each persisted Insight."""
        ...

    def generate_insights(
        self,
        *,
        context: str,
        allowed_run_ids: set[int],
        run_evidence_ids: dict[int, set[int]],
        run_persona_ids: dict[int, int],
    ) -> InsightGenerationResult:
        """Generate Insights and return an already-validated result.

        Implementations must locally `json.loads` the raw provider output
        and validate it against `InsightGenerationResult` (passing
        `allowed_run_ids`, `run_evidence_ids`, and `run_persona_ids` as
        Pydantic validation context) before returning — never return
        unvalidated data. On any failure, raise one of the typed errors in
        `app.llm.exceptions`.
        """
        ...
