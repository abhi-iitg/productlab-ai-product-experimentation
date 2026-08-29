"""HTTP-layer behavior for the HumanFeedback CRUD API.

Seeded entirely through the API (project -> evidence -> personas ->
experiment -> execute), matching the convention in `test_runs_api.py`.
"""

from fastapi.testclient import TestClient

from app.api.routes.experiments import get_simulation_provider
from app.api.routes.personas import get_persona_provider
from tests.experiment_helpers import experiment_create_payload
from tests.fakes import (
    FakePersonaProvider,
    FakeSimulationProvider,
    make_generation_result,
    make_simulation_call_result,
)

_PROJECT_PAYLOAD = {
    "name": "Portfolio Discovery Tool",
    "problem_statement": "Teams decide on intuition alone.",
    "target_user": "Early-stage product managers.",
    "product_hypothesis": "Evidence-grounded personas surface weak assumptions.",
    "success_metric": "Time to a decision memo.",
}

_EVIDENCE_PAYLOAD = {
    "evidence_type": "interview_note",
    "title": "Interview with early adopter",
    "content": "They struggled with onboarding.",
}

_FEEDBACK_PAYLOAD = {
    "participant_label": "Participant 1",
    "variant_key": "A",
    "source_method": "usability_test",
    "task_outcome": "completed",
    "clarity_score": 4,
    "perceived_value_score": 5,
    "adoption_intent_score": 4,
    "feedback_summary": "Completed the task with minimal confusion.",
    "positive_signals": ["Liked the guided steps"],
    "objections": [],
    "confusion_points": [],
    "feature_requests": [],
    "uncertainty_notes": [],
}


def _create_project(client: TestClient) -> int:
    return client.post("/api/v1/projects", json=_PROJECT_PAYLOAD).json()["id"]


def _create_evidence(client: TestClient, project_id: int) -> int:
    return client.post(f"/api/v1/projects/{project_id}/evidence", json=_EVIDENCE_PAYLOAD).json()[
        "id"
    ]


def _create_personas(client: TestClient, project_id: int, evidence_id: int) -> list[int]:
    provider = FakePersonaProvider(result=make_generation_result(evidence_item_id=evidence_id))
    client.app.dependency_overrides[get_persona_provider] = lambda: provider
    response = client.post(
        f"/api/v1/projects/{project_id}/personas/generate", json={"persona_count": 2}
    )
    client.app.dependency_overrides.pop(get_persona_provider, None)
    return [persona["id"] for persona in response.json()["personas"]]


def _create_and_execute_experiment(client: TestClient) -> tuple[int, int]:
    project_id = _create_project(client)
    evidence_id = _create_evidence(client, project_id)
    persona_ids = _create_personas(client, project_id, evidence_id)
    created = client.post(
        f"/api/v1/projects/{project_id}/experiments",
        json=experiment_create_payload([persona_ids[0]], repeat_count=1),
    ).json()

    client.app.dependency_overrides[get_simulation_provider] = lambda: FakeSimulationProvider(
        result=make_simulation_call_result()
    )
    client.post(
        f"/api/v1/projects/{project_id}/experiments/{created['id']}/execute",
        json={"confirm_execution": True},
    )
    client.app.dependency_overrides.pop(get_simulation_provider, None)

    return project_id, created["id"]


def _create_draft_experiment(client: TestClient) -> tuple[int, int]:
    project_id = _create_project(client)
    evidence_id = _create_evidence(client, project_id)
    persona_ids = _create_personas(client, project_id, evidence_id)
    created = client.post(
        f"/api/v1/projects/{project_id}/experiments",
        json=experiment_create_payload([persona_ids[0]], repeat_count=1),
    ).json()
    return project_id, created["id"]


def _feedback_url(project_id: int, experiment_id: int, feedback_id: int | None = None) -> str:
    base = f"/api/v1/projects/{project_id}/experiments/{experiment_id}/human-feedback"
    return f"{base}/{feedback_id}" if feedback_id is not None else base


def test_create_human_feedback_returns_201(client: TestClient) -> None:
    project_id, experiment_id = _create_and_execute_experiment(client)

    response = client.post(_feedback_url(project_id, experiment_id), json=_FEEDBACK_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert body["experiment_id"] == experiment_id
    assert body["participant_label"] == "Participant 1"
    assert body["variant_key"] == "A"


def test_create_human_feedback_response_has_no_pii_fields(client: TestClient) -> None:
    project_id, experiment_id = _create_and_execute_experiment(client)

    response = client.post(_feedback_url(project_id, experiment_id), json=_FEEDBACK_PAYLOAD)

    expected_fields = {
        "id",
        "experiment_id",
        "participant_label",
        "variant_key",
        "task_outcome",
        "clarity_score",
        "perceived_value_score",
        "adoption_intent_score",
        "feedback_summary",
        "positive_signals",
        "objections",
        "confusion_points",
        "feature_requests",
        "uncertainty_notes",
        "source_method",
        "session_date",
        "created_at",
        "updated_at",
    }
    assert set(response.json().keys()) == expected_fields


def test_create_human_feedback_returns_404_for_missing_project(client: TestClient) -> None:
    _project_id, experiment_id = _create_and_execute_experiment(client)

    response = client.post(_feedback_url(999_999, experiment_id), json=_FEEDBACK_PAYLOAD)

    assert response.status_code == 404


def test_create_human_feedback_returns_404_for_missing_experiment(client: TestClient) -> None:
    project_id = _create_project(client)

    response = client.post(_feedback_url(project_id, 999_999), json=_FEEDBACK_PAYLOAD)

    assert response.status_code == 404


def test_create_human_feedback_rejects_blank_participant_label(client: TestClient) -> None:
    project_id, experiment_id = _create_and_execute_experiment(client)

    response = client.post(
        _feedback_url(project_id, experiment_id),
        json={**_FEEDBACK_PAYLOAD, "participant_label": "   "},
    )

    assert response.status_code == 422


def test_create_human_feedback_rejects_invalid_score(client: TestClient) -> None:
    project_id, experiment_id = _create_and_execute_experiment(client)

    response = client.post(
        _feedback_url(project_id, experiment_id), json={**_FEEDBACK_PAYLOAD, "clarity_score": 6}
    )

    assert response.status_code == 422


def test_create_human_feedback_returns_409_for_draft_experiment(client: TestClient) -> None:
    project_id, experiment_id = _create_draft_experiment(client)

    response = client.post(_feedback_url(project_id, experiment_id), json=_FEEDBACK_PAYLOAD)

    assert response.status_code == 409


def test_create_human_feedback_returns_409_for_duplicate_participant_and_variant(
    client: TestClient,
) -> None:
    project_id, experiment_id = _create_and_execute_experiment(client)
    client.post(_feedback_url(project_id, experiment_id), json=_FEEDBACK_PAYLOAD)

    response = client.post(_feedback_url(project_id, experiment_id), json=_FEEDBACK_PAYLOAD)

    assert response.status_code == 409


def test_list_human_feedback_for_experiment(client: TestClient) -> None:
    project_id, experiment_id = _create_and_execute_experiment(client)
    client.post(_feedback_url(project_id, experiment_id), json=_FEEDBACK_PAYLOAD)
    client.post(
        _feedback_url(project_id, experiment_id),
        json={**_FEEDBACK_PAYLOAD, "participant_label": "Participant 2"},
    )

    response = client.get(_feedback_url(project_id, experiment_id))

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_human_feedback_returns_200(client: TestClient) -> None:
    project_id, experiment_id = _create_and_execute_experiment(client)
    created = client.post(_feedback_url(project_id, experiment_id), json=_FEEDBACK_PAYLOAD).json()

    response = client.get(_feedback_url(project_id, experiment_id, created["id"]))

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_human_feedback_returns_404_when_missing(client: TestClient) -> None:
    project_id, experiment_id = _create_and_execute_experiment(client)

    response = client.get(_feedback_url(project_id, experiment_id, 999_999))

    assert response.status_code == 404


def test_update_human_feedback_returns_200(client: TestClient) -> None:
    project_id, experiment_id = _create_and_execute_experiment(client)
    created = client.post(_feedback_url(project_id, experiment_id), json=_FEEDBACK_PAYLOAD).json()

    response = client.patch(
        _feedback_url(project_id, experiment_id, created["id"]),
        json={"feedback_summary": "Updated summary."},
    )

    assert response.status_code == 200
    assert response.json()["feedback_summary"] == "Updated summary."


def test_update_human_feedback_rejects_empty_patch(client: TestClient) -> None:
    project_id, experiment_id = _create_and_execute_experiment(client)
    created = client.post(_feedback_url(project_id, experiment_id), json=_FEEDBACK_PAYLOAD).json()

    response = client.patch(_feedback_url(project_id, experiment_id, created["id"]), json={})

    assert response.status_code == 422


def test_delete_human_feedback_returns_204(client: TestClient) -> None:
    project_id, experiment_id = _create_and_execute_experiment(client)
    created = client.post(_feedback_url(project_id, experiment_id), json=_FEEDBACK_PAYLOAD).json()

    response = client.delete(_feedback_url(project_id, experiment_id, created["id"]))

    assert response.status_code == 204
    assert client.get(_feedback_url(project_id, experiment_id, created["id"])).status_code == 404


def test_delete_human_feedback_returns_404_when_missing(client: TestClient) -> None:
    project_id, experiment_id = _create_and_execute_experiment(client)

    response = client.delete(_feedback_url(project_id, experiment_id, 999_999))

    assert response.status_code == 404


def test_human_feedback_isolated_across_projects(client: TestClient) -> None:
    project_a, experiment_a = _create_and_execute_experiment(client)
    project_b, experiment_b = _create_and_execute_experiment(client)
    feedback = client.post(_feedback_url(project_a, experiment_a), json=_FEEDBACK_PAYLOAD).json()

    get_response = client.get(_feedback_url(project_b, experiment_b, feedback["id"]))
    patch_response = client.patch(
        _feedback_url(project_b, experiment_b, feedback["id"]),
        json={"feedback_summary": "Hijacked"},
    )
    delete_response = client.delete(_feedback_url(project_b, experiment_b, feedback["id"]))

    assert get_response.status_code == 404
    assert patch_response.status_code == 404
    assert delete_response.status_code == 404


# Cascade-delete-on-Experiment-delete behavior is exercised at the model
# layer (`test_human_feedback_models.py`) — an executed experiment can no
# longer be deleted through the API (`ExperimentService` only allows
# deleting `draft` experiments), so it cannot be exercised end-to-end here.
