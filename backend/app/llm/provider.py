"""Typed interface the service layer depends on, not the OpenAI SDK directly.

`PersonaGenerationService` is constructed with any object satisfying this
`Protocol` — the real `OpenAIPersonaProvider` in production, a deterministic
fake in tests. Implementations raise the typed errors in
`app.llm.exceptions` on failure and otherwise return a fully parsed and
Pydantic-validated `PersonaGenerationResult`.
"""

from typing import Protocol

from app.schemas.persona import PersonaGenerationResult


class PersonaLLMProvider(Protocol):
    """A provider capable of generating evidence-grounded personas."""

    @property
    def model_name(self) -> str:
        """The provider/model identifier to record on each persisted persona."""
        ...

    def generate_personas(
        self,
        *,
        persona_count: int,
        context: str,
        focus: str | None,
        allowed_evidence_ids: set[int],
    ) -> PersonaGenerationResult:
        """Generate personas and return an already-validated result.

        Implementations must locally `json.loads` the raw provider output
        and validate it against `PersonaGenerationResult` (passing
        `allowed_evidence_ids` as Pydantic validation context) before
        returning — never return unvalidated data. On any failure, raise
        one of the typed errors in `app.llm.exceptions`.
        """
        ...
