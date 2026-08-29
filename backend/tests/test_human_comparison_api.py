"""HTTP-layer behavior for the deterministic human-vs-synthetic comparison
route: GET .../human-feedback/comparison.
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


def _comparison_url(project_id: int, experiment_id: int) -> str:
    return f"/api/v1/projects/{project_id}/experiments/{experiment_id}/human-feedback/comparison"


def _feedback_url(project_id: int, experiment_id: int) -> str:
    return f"/api/v1/projects/{project_id}/experiments/{experiment_id}/human-feedback"


def test_comparison_returns_200_with_no_feedback(client: TestClient) -> None:
    project_id, experiment_id = _create_and_execute_experiment(client)

    response = client.get(_comparison_url(project_id, experiment_id))

    assert response.status_code == 200
    body = response.json()
    assert body["human_summary"][0]["feedback_record_count"] == 0
    assert any("No real-participant feedback" in w for w in body["data_quality_warnings"])
    assert "interpretation_notice" in body


def test_comparison_reflects_created_feedback(client: TestClient) -> None:
    project_id, experiment_id = _create_and_execute_experiment(client)
    client.post(
        _feedback_url(project_id, experiment_id),
        json={
            "participant_label": "Participant 1",
            "variant_key": "A",
            "source_method": "usability_test",
            "task_outcome": "completed",
            "clarity_score": 4,
            "perceived_value_score": 4,
            "adoption_intent_score": 4,
            "feedback_summary": "Completed the task with minimal confusion.",
        },
    )

    response = client.get(_comparison_url(project_id, experiment_id))

    assert response.status_code == 200
    body = response.json()
    variant_a_human = next(v for v in body["human_summary"] if v["variant_key"] == "A")
    assert variant_a_human["feedback_record_count"] == 1


def test_comparison_returns_409_with_no_completed_synthetic_runs(client: TestClient) -> None:
    project_id, experiment_id = _create_draft_experiment(client)

    response = client.get(_comparison_url(project_id, experiment_id))

    assert response.status_code == 409


def test_comparison_returns_404_for_missing_project(client: TestClient) -> None:
    _project_id, experiment_id = _create_and_execute_experiment(client)

    response = client.get(_comparison_url(999_999, experiment_id))

    assert response.status_code == 404


def test_comparison_returns_404_for_missing_experiment(client: TestClient) -> None:
    project_id = _create_project(client)

    response = client.get(_comparison_url(project_id, 999_999))

    assert response.status_code == 404


def test_comparison_isolated_across_projects(client: TestClient) -> None:
    project_a, experiment_a = _create_and_execute_experiment(client)
    project_b, _experiment_b = _create_and_execute_experiment(client)

    response = client.get(_comparison_url(project_b, experiment_a))

    assert response.status_code == 404


def test_comparison_route_is_not_shadowed_by_feedback_id_route(client: TestClient) -> None:
    project_id, experiment_id = _create_and_execute_experiment(client)

    # If the router registered `/{feedback_id}` before `/comparison`, this
    # request would 422 (feedback_id="comparison" fails int parsing)
    # instead of resolving to the comparison handler.
    response = client.get(_comparison_url(project_id, experiment_id))

    assert response.status_code == 200
