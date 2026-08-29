"""Deterministic in-process fake LLM providers for full-stack E2E testing.

Distinct from `backend/tests/fakes.py` (which is pytest-only, pre-configured
per test with a canned result/error) — these implementations live in `app`
so they can be selected by the real running FastAPI process during
Playwright runs, and they derive a schema-valid response directly from
whatever the caller passes in (evidence IDs, run IDs, insight IDs) rather
than requiring a test to pre-configure a canned result. No network access,
no API key, fully deterministic given the same input.

Selected only by `app.llm.factory` when `Settings.E2E_FAKE_AI` is true,
which is itself only ever true when `APP_ENV=test`
(`Settings._validate_e2e_fake_ai_requires_test_env`).

The display content below (persona vignettes, simulation responses, insight
and decision-memo copy) is deliberately test-only fictional content
themed around a "Field Notes Sync" field-data-capture product: unreliable
cellular connectivity, lost or incomplete synchronization, duplicate note
entry, paper backup workflows, end-of-day paperwork, and confidence that a
note is saved locally. It exists purely so screenshots taken against this
fake-provider mode read as a coherent, evidence-grounded product rather
than placeholder text — it has no effect on real (OpenAI-backed) behavior.
"""

import itertools
import re

from app.llm.exceptions import LLMProviderError
from app.models.decision_memo import Recommendation
from app.models.insight import InsightCategory, VariantScope
from app.models.persona import ConfidenceLevel
from app.models.simulation_run import TaskOutcome
from app.schemas.decision_memo import DecisionMemoCandidate, RealUserTestPlan
from app.schemas.insight import InsightGenerationResult
from app.schemas.persona import EvidenceReference, GeneratedPersona, PersonaGenerationResult
from app.schemas.simulation_run import SimulationCallResult, SimulationOutput

# Each entry grounds one generated persona in a distinct facet of the
# fictional Field Notes Sync evidence library (unreliable cellular
# connectivity, duplicate note entry, incomplete sync, confidence that a
# note saved locally, and paper-backup/end-of-day paperwork), cycled by
# position within a single `generate_personas` call.
_PERSONA_VIGNETTES = [
    {
        "segment_label": "Field Technician",
        "summary": (
            "A field technician who captures inspection notes with no reliable cellular "
            "signal for most of a shift, grounded in evidence item #{evidence_id}."
        ),
        "goals": [
            "Capture inspection notes on-site without waiting for a signal.",
            "Trust that a note taken in a dead zone is not silently lost.",
        ],
        "pain_points": [
            "Cellular connectivity drops out for hours at remote job sites.",
            "Can't tell whether a note actually saved when the connection cut out.",
        ],
        "constraints": ["Works in locations with no reliable cell coverage for most of a shift."],
        "behaviors": ["Keeps a paper notebook as a backup in case the app doesn't sync."],
        "claim": "Cellular connectivity is unreliable at many job sites.",
    },
    {
        "segment_label": "Regional Crew Lead",
        "summary": (
            "A regional crew lead who reviews field notes from several technicians each "
            "week, grounded in evidence item #{evidence_id}."
        ),
        "goals": ["Avoid re-entering the same note twice after the app reconnects."],
        "pain_points": ["Duplicate entries appear after the app regains a network connection."],
        "constraints": ["Reviews dozens of field notes at the end of each week."],
        "behaviors": ["Cross-checks synced notes against a paper log before discarding it."],
        "claim": "Notes are sometimes duplicated after the app reconnects.",
    },
    {
        "segment_label": "Field Technician",
        "summary": (
            "A field technician who has had a batch of notes go missing after syncing, "
            "grounded in evidence item #{evidence_id}."
        ),
        "goals": ["Confirm that every note taken in the field actually reaches the office system."],
        "pain_points": ["A batch of notes from a job site never appeared after the app synced."],
        "constraints": ["Has no way to verify sync status once back in coverage."],
        "behaviors": ["Contacts support when notes seem to have gone missing after a sync."],
        "claim": "A full batch of synced notes failed to arrive on the office system.",
    },
    {
        "segment_label": "Regional Crew Lead",
        "summary": (
            "A regional crew lead who wants an unambiguous saved state, grounded in "
            "evidence item #{evidence_id}."
        ),
        "goals": [
            "Feel confident a note is safely stored the moment it's written, connection or not."
        ],
        "pain_points": ["Isn't sure whether 'saved' means saved locally or saved to the server."],
        "constraints": ["Needs an unambiguous saved indicator, not just a loading spinner."],
        "behaviors": ["Screenshots notes as a personal backup until sync is confirmed."],
        "claim": "Users are often unsure whether a note is saved locally or only on the server.",
    },
    {
        "segment_label": "Field Technician",
        "summary": (
            "A field technician who still reconciles a paper backup against the app every "
            "day, grounded in evidence item #{evidence_id}."
        ),
        "goals": ["Eliminate the need to re-transcribe field notes into paper forms at day's end."],
        "pain_points": [
            "Spends twenty or more minutes at end of day reconciling app notes against "
            "paper backups."
        ],
        "constraints": ["Office policy still requires a signed paper copy until sync is trusted."],
        "behaviors": ["Keeps a paper backup workflow running in parallel with the app."],
        "claim": "Crews keep a parallel paper backup and reconcile it at the end of the day.",
    },
]

_PERSONA_NAMES = [
    "Priya Nakamura",
    "Owen Castillo",
    "Dana Whitfield",
    "Marcus Boyd",
    "Leah Ferreira",
    "Sam Okafor",
    "Jordan Whitaker",
    "Ines Duarte",
]


class E2EFakePersonaProvider:
    """Deterministic `PersonaLLMProvider` used only in E2E test mode.

    Persona names are drawn from a process-wide counter (not reset per
    call) so that names stay unique across multiple generation calls
    against the same running server — a single E2E test run may generate
    personas more than once (e.g. to build a large-enough persona pool to
    exercise the 30-run cap), and a UI that lists personas by name needs
    each one to be a distinct, stable locator target.
    """

    model_name = "e2e-fake-persona-provider"
    _name_counter = itertools.count(1)

    def generate_personas(
        self,
        *,
        persona_count: int,
        context: str,
        focus: str | None,
        allowed_evidence_ids: set[int],
    ) -> PersonaGenerationResult:
        if not allowed_evidence_ids:
            raise LLMProviderError("No evidence available for E2E persona generation.")

        evidence_ids = sorted(allowed_evidence_ids)
        personas: list[GeneratedPersona] = []
        for i in range(persona_count):
            evidence_id = evidence_ids[i % len(evidence_ids)]
            persona_number = next(self._name_counter)
            vignette = _PERSONA_VIGNETTES[i % len(_PERSONA_VIGNETTES)]
            name = _PERSONA_NAMES[(persona_number - 1) % len(_PERSONA_NAMES)]
            personas.append(
                GeneratedPersona(
                    name=name,
                    segment_label=vignette["segment_label"],
                    summary=vignette["summary"].format(evidence_id=evidence_id),
                    goals=list(vignette["goals"]),
                    pain_points=list(vignette["pain_points"]),
                    constraints=list(vignette["constraints"]),
                    behaviors=list(vignette["behaviors"]),
                    evidence_references=[
                        EvidenceReference(
                            evidence_item_id=evidence_id,
                            supported_claims=[vignette["claim"]],
                        )
                    ],
                    unsupported_assumptions=(
                        [
                            "Assumes this technician would trust the app after only one "
                            "successful offline save."
                        ]
                        if i == 0
                        else []
                    ),
                    confidence_level=(
                        ConfidenceLevel.MEDIUM if i % 2 == 0 else ConfidenceLevel.HIGH
                    ),
                )
            )
        return PersonaGenerationResult(personas=personas)


_VARIANT_NAME_PATTERN = re.compile(r"=== VARIANT UNDER EVALUATION ===\nName: (.+)")
_PERSONA_NAME_PATTERN = re.compile(
    r"=== PERSONA \(respond only from this bounded perspective\) ===\nName: (.+)"
)


class E2EFakeSimulationProvider:
    """Deterministic `SimulationLLMProvider` used only in E2E test mode.

    Reads the active variant's name out of the assembled context text
    (`app.llm.simulation_context.build_simulation_context` always includes
    it under "=== VARIANT UNDER EVALUATION ===") to produce two
    deliberately different, but each internally deterministic, response
    shapes — one for a "fully offline" variant (strong reliability trust,
    always a clean completion) and one for a "background sync" variant
    (more convenience but real uncertainty about sync state, split by
    persona so the distribution isn't uniform). Any context that doesn't
    name a recognizable variant (e.g. a unit test calling this provider
    directly with a placeholder context) falls back to a single generic,
    always-completed response, preserving prior behavior.
    """

    model_name = "e2e-fake-simulation-provider"

    def ensure_configured(self) -> None:
        return None

    def run_simulation(
        self, *, context: str, allowed_evidence_ids: set[int]
    ) -> SimulationCallResult:
        evidence_references = (
            [
                EvidenceReference(
                    evidence_item_id=min(allowed_evidence_ids),
                    supported_claims=["Matches a known pain point from the evidence library."],
                )
            ]
            if allowed_evidence_ids
            else []
        )

        variant_match = _VARIANT_NAME_PATTERN.search(context)
        variant_name = variant_match.group(1).casefold() if variant_match else ""

        if "offline" in variant_name:
            output = self._offline_variant_output(evidence_references)
        elif "sync" in variant_name:
            output = self._background_sync_variant_output(context, evidence_references)
        else:
            output = self._generic_output(evidence_references)

        return SimulationCallResult(
            output=output,
            input_tokens=120,
            output_tokens=80,
            latency_ms=250,
        )

    def _offline_variant_output(
        self, evidence_references: list[EvidenceReference]
    ) -> SimulationOutput:
        return SimulationOutput(
            task_outcome=TaskOutcome.COMPLETED,
            clarity_score=5,
            perceived_value_score=5,
            adoption_intent_score=4,
            response_summary=(
                "The persona trusted that the note was safely captured locally the "
                "instant it was written, with no cellular connection required."
            ),
            positive_signals=[
                "Confident the note saved before losing signal.",
                "No longer needed a paper backup for this note.",
            ],
            objections=[],
            confusion_points=[],
            feature_requests=["Wants a visible confirmation when a note saves locally."],
            uncertainty_notes=[],
            evidence_references=evidence_references,
        )

    def _background_sync_variant_output(
        self, context: str, evidence_references: list[EvidenceReference]
    ) -> SimulationOutput:
        persona_match = _PERSONA_NAME_PATTERN.search(context)
        persona_name = persona_match.group(1) if persona_match else ""
        is_confident_half = sum(ord(char) for char in persona_name) % 2 == 0

        if is_confident_half:
            return SimulationOutput(
                task_outcome=TaskOutcome.COMPLETED,
                clarity_score=4,
                perceived_value_score=4,
                adoption_intent_score=4,
                response_summary=(
                    "The persona appreciated not waiting on the sync to keep working, "
                    "and confirmed the note eventually reached the office system."
                ),
                positive_signals=["Could keep working without waiting on the sync."],
                objections=[],
                confusion_points=[],
                feature_requests=["Wants a clear synced-vs-pending indicator."],
                uncertainty_notes=["Not confident the note reached the office yet."],
                evidence_references=evidence_references,
            )

        return SimulationOutput(
            task_outcome=TaskOutcome.UNCERTAIN,
            clarity_score=4,
            perceived_value_score=3,
            adoption_intent_score=3,
            response_summary=(
                "The persona liked not waiting on the sync, but wasn't confident "
                "whether the note had actually synced or was still pending in the "
                "background."
            ),
            positive_signals=["Liked not waiting on the sync to keep working."],
            objections=["Worried the note might duplicate after syncing."],
            confusion_points=["Unclear if the note was synced or still pending."],
            feature_requests=["Wants a clear synced-vs-pending indicator."],
            uncertainty_notes=["Not confident the note reached the office yet."],
            evidence_references=evidence_references,
        )

    def _generic_output(self, evidence_references: list[EvidenceReference]) -> SimulationOutput:
        return SimulationOutput(
            task_outcome=TaskOutcome.COMPLETED,
            clarity_score=4,
            perceived_value_score=4,
            adoption_intent_score=4,
            response_summary="The persona understood the variant and reacted positively.",
            positive_signals=["Liked the streamlined flow."],
            objections=[],
            confusion_points=[],
            feature_requests=["Would like a quicker way to invite teammates."],
            uncertainty_notes=[],
            evidence_references=evidence_references,
        )


_RUN_VARIANT_PATTERN = re.compile(r"run_id=(\d+), variant=(A|B)")


class E2EFakeInsightProvider:
    """Deterministic `InsightLLMProvider` used only in E2E test mode.

    Builds a raw dict and validates it through `InsightGenerationResult.
    model_validate(..., context=...)`, exactly like `OpenAIInsightProvider`
    does with the real provider's raw JSON — `InsightCandidate`'s
    evidence-citation check runs even on direct construction (it is only
    a no-op when `run_evidence_ids` is empty), so citing evidence here
    requires going through the same validation context the real provider
    uses rather than constructing `InsightCandidate` directly.

    When the assembled context names each run's variant (as
    `app.llm.insight_context.build_insight_context` always does), this
    also emits two variant-scoped insights alongside the shared ones, so
    the generated set demonstrates an actual per-variant contrast rather
    than only combined findings. A context without recognizable
    per-run variant tags (e.g. a unit test calling this provider directly)
    falls back to the original two combined-scope insights.
    """

    model_name = "e2e-fake-insight-provider"

    def generate_insights(
        self,
        *,
        context: str,
        allowed_run_ids: set[int],
        run_evidence_ids: dict[int, set[int]],
        run_persona_ids: dict[int, int],
    ) -> InsightGenerationResult:
        if not allowed_run_ids:
            raise LLMProviderError("No insights available for E2E insight generation.")

        run_ids = sorted(allowed_run_ids)
        evidence_ids = sorted(
            {eid for run_id in run_ids for eid in run_evidence_ids.get(run_id, set())}
        )

        variant_by_run_id = {
            int(run_id): variant
            for run_id, variant in _RUN_VARIANT_PATTERN.findall(context)
            if int(run_id) in allowed_run_ids
        }
        variant_a_run_ids = sorted(
            run_id for run_id, variant in variant_by_run_id.items() if variant == "A"
        )
        variant_b_run_ids = sorted(
            run_id for run_id, variant in variant_by_run_id.items() if variant == "B"
        )

        insights = [
            self._shared_strength_insight(run_ids, evidence_ids, run_persona_ids),
        ]

        if variant_a_run_ids and variant_b_run_ids:
            insights.append(
                self._variant_a_insight(variant_a_run_ids, run_evidence_ids, run_persona_ids)
            )
            insights.append(
                self._variant_b_insight(variant_b_run_ids, run_evidence_ids, run_persona_ids)
            )

        insights.append(self._shared_uncertainty_insight(run_ids, evidence_ids, run_persona_ids))

        raw = {"insights": insights}
        return InsightGenerationResult.model_validate(
            raw,
            context={
                "allowed_run_ids": allowed_run_ids,
                "run_evidence_ids": run_evidence_ids,
                "run_persona_ids": run_persona_ids,
            },
        )

    def _persona_count(self, run_ids: list[int], run_persona_ids: dict[int, int]) -> int:
        return len({run_persona_ids[run_id] for run_id in run_ids if run_id in run_persona_ids})

    def _shared_strength_insight(
        self,
        run_ids: list[int],
        evidence_ids: list[int],
        run_persona_ids: dict[int, int],
    ) -> dict:
        return {
            "category": InsightCategory.STRENGTH.value,
            "variant_scope": VariantScope.BOTH.value,
            "title": "Personas trust that a note is safely captured without a live connection",
            "summary": (
                "Across both variants, completed runs consistently reported confidence "
                "that a field note was captured even with unreliable cellular connectivity."
            ),
            "frequency": len(run_ids),
            "persona_count": self._persona_count(run_ids, run_persona_ids),
            "supporting_run_ids": run_ids,
            "supporting_evidence_ids": evidence_ids,
            "confidence_level": ConfidenceLevel.MEDIUM.value,
        }

    def _variant_a_insight(
        self,
        run_ids: list[int],
        run_evidence_ids: dict[int, set[int]],
        run_persona_ids: dict[int, int],
    ) -> dict:
        evidence_ids = sorted(
            {eid for run_id in run_ids for eid in run_evidence_ids.get(run_id, set())}
        )
        return {
            "category": InsightCategory.STRENGTH.value,
            "variant_scope": VariantScope.A.value,
            "title": "Fully offline capture builds stronger reliability trust",
            "summary": (
                "Runs on the fully offline variant consistently completed cleanly, with "
                "personas reporting no objections or uncertainty about whether a note "
                "was saved."
            ),
            "frequency": len(run_ids),
            "persona_count": self._persona_count(run_ids, run_persona_ids),
            "supporting_run_ids": run_ids,
            "supporting_evidence_ids": evidence_ids,
            "confidence_level": ConfidenceLevel.MEDIUM.value,
        }

    def _variant_b_insight(
        self,
        run_ids: list[int],
        run_evidence_ids: dict[int, set[int]],
        run_persona_ids: dict[int, int],
    ) -> dict:
        evidence_ids = sorted(
            {eid for run_id in run_ids for eid in run_evidence_ids.get(run_id, set())}
        )
        return {
            "category": InsightCategory.UNCERTAINTY.value,
            "variant_scope": VariantScope.B.value,
            "title": "Background partial sync leaves confidence in sync state uncertain",
            "summary": (
                "Runs on the background partial sync variant valued not waiting on the "
                "sync, but several personas were unsure whether a note had actually "
                "synced or risked being duplicated."
            ),
            "frequency": len(run_ids),
            "persona_count": self._persona_count(run_ids, run_persona_ids),
            "supporting_run_ids": run_ids,
            "supporting_evidence_ids": evidence_ids,
            "confidence_level": ConfidenceLevel.LOW.value,
        }

    def _shared_uncertainty_insight(
        self,
        run_ids: list[int],
        evidence_ids: list[int],
        run_persona_ids: dict[int, int],
    ) -> dict:
        return {
            "category": InsightCategory.UNCERTAINTY.value,
            "variant_scope": VariantScope.BOTH.value,
            "title": "Synthetic sample size remains small for a confident read",
            "summary": (
                "Only a limited set of synthetic runs support this comparison; treat the "
                "variant contrast as directional, not conclusive."
            ),
            "frequency": len(run_ids),
            "persona_count": self._persona_count(run_ids, run_persona_ids),
            "supporting_run_ids": run_ids,
            "supporting_evidence_ids": evidence_ids,
            "confidence_level": ConfidenceLevel.LOW.value,
        }


class E2EFakeDecisionMemoProvider:
    """Deterministic `DecisionMemoLLMProvider` used only in E2E test mode."""

    model_name = "e2e-fake-decision-memo-provider"

    def generate_decision_memo(
        self, *, context: str, allowed_insight_ids: set[int]
    ) -> DecisionMemoCandidate:
        if not allowed_insight_ids:
            raise LLMProviderError("No insights available for E2E decision memo generation.")

        real_user_test = RealUserTestPlan(
            objective=(
                "Validate whether real field crews trust that a note is saved before "
                "losing cellular connectivity, comparing fully offline capture against "
                "background partial sync."
            ),
            target_participants=[
                "5-8 field technicians and crew leads who currently keep a paper backup workflow."
            ],
            method=(
                "Moderated field-conditions usability test comparing the fully offline "
                "and background-sync variants."
            ),
            sample_size_rationale=(
                "A small qualitative sample is sufficient to surface major trust and "
                "sync-confidence blockers before a larger rollout."
            ),
            tasks_or_questions=[
                "Capture a field note with no cellular connection, then confirm "
                "afterward whether you trust it was saved.",
                "Reconnect and check whether the note appears once or is duplicated.",
            ],
            success_metrics=[
                "Reported confidence that a note was saved locally.",
                "Duplicate-entry rate after reconnecting.",
            ],
            stopping_rule=(
                "Stop after 5 sessions if the same sync-confidence blocker recurs in at least 4."
            ),
        )
        return DecisionMemoCandidate(
            recommendation=Recommendation.PROCEED,
            executive_summary=(
                "Synthetic signal favors the fully offline variant on trust and "
                "reliability; recommend real-user validation next, not launch."
            ),
            supporting_findings=[
                "Personas across both variants trusted that a note taken without "
                "connectivity was still safely captured.",
                "The fully offline variant produced stronger confidence and fewer "
                "objections about sync status than the background-sync variant.",
            ],
            weakest_assumptions=[
                "Assumes field crews will trust a 'saved' indicator without an explicit "
                "sync confirmation.",
                "Assumes duplicate note entry after reconnecting is rare enough not to "
                "erode trust.",
            ],
            recommended_product_changes=[
                "Add an explicit 'saved locally, not yet synced' state distinct from a "
                "generic loading spinner.",
                "Add a duplicate-detection prompt when a note appears to have been "
                "entered twice after reconnecting.",
            ],
            risks=[
                "The evidence library backing this run centers on a small number of "
                "field crews and support tickets.",
                "Background partial sync introduces ambiguity about note state that a "
                "real-user study should probe directly.",
            ],
            uncertain_conclusions=[
                "Confidence in the background-sync variant's real-world reliability "
                "remains uncertain given the limited evidence gathered so far."
            ],
            recommended_success_metrics=[
                "Rate at which real field users report confidence that a note was saved "
                "before losing connectivity."
            ],
            real_user_test=real_user_test,
            supporting_insight_ids=sorted(allowed_insight_ids),
        )
