"""Typed interface the Decision Memo service layer depends on, not the
OpenAI SDK directly.

`DecisionMemoService` is constructed with any object satisfying this
`Protocol` — the real `OpenAIDecisionMemoProvider` in production, a
deterministic fake in tests. Implementations raise the typed errors in
`app.llm.exceptions` on failure and otherwise return a fully parsed and
Pydantic-validated `DecisionMemoCandidate`.
"""

from typing import Protocol

from app.schemas.decision_memo import DecisionMemoCandidate


class DecisionMemoLLMProvider(Protocol):
    """A provider capable of producing a structured Proceed/Iterate/Stop memo."""

    @property
    def model_name(self) -> str:
        """The provider/model identifier to record on the persisted memo."""
        ...

    def generate_decision_memo(
        self,
        *,
        context: str,
        allowed_insight_ids: set[int],
    ) -> DecisionMemoCandidate:
        """Generate a Decision Memo and return an already-validated result.

        Implementations must locally `json.loads` the raw provider output
        and validate it against `DecisionMemoCandidate` (passing
        `allowed_insight_ids` as Pydantic validation context) before
        returning — never return unvalidated data. On any failure, raise
        one of the typed errors in `app.llm.exceptions`.
        """
        ...
