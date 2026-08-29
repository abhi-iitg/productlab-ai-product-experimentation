"""Typed interface the execution service depends on, not the OpenAI SDK directly.

`ExperimentExecutionService` is constructed with any object satisfying this
`Protocol` — the real `OpenAISimulationProvider` in production, a
deterministic fake in tests. Implementations raise the typed errors in
`app.llm.exceptions` on failure and otherwise return a fully parsed and
Pydantic-validated `SimulationCallResult`.
"""

from typing import Protocol

from app.schemas.simulation_run import SimulationCallResult


class SimulationLLMProvider(Protocol):
    """A provider capable of running one structured persona/variant simulation."""

    @property
    def model_name(self) -> str:
        """The provider/model identifier to record on each persisted run."""
        ...

    def ensure_configured(self) -> None:
        """Raise `LLMConfigurationError` if the provider cannot be used right now.

        Called once before an experiment's status is flipped to `running`,
        so a missing API key is caught before any run is dispatched rather
        than surfacing as 30 individual per-run failures.
        """
        ...

    def run_simulation(
        self,
        *,
        context: str,
        allowed_evidence_ids: set[int],
    ) -> SimulationCallResult:
        """Run one simulation and return an already-validated result.

        Implementations must locally `json.loads` the raw provider output
        and validate it against `SimulationOutput` (passing
        `allowed_evidence_ids` as Pydantic validation context) before
        returning — never return unvalidated data. On any failure, raise
        one of the typed errors in `app.llm.exceptions`.
        """
        ...
