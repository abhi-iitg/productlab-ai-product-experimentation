"""HTTP-layer behavior for the deterministic analysis API.

Seeded entirely through the API (project -> evidence -> personas ->
experiment -> execute -> analysis), matching the convention in
`test_runs_api.py`.
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
        json=experiment_create_payload(persona_ids, repeat_count=1),
    ).json()

    client.app.dependency_overrides[get_simulation_provider] = lambda: FakeSimulationProvider(
        result=make_simulation_call_result(evidence_item_id=evidence_id)
    )
    client.post(
        f"/api/v1/projects/{project_id}/experiments/{created['id']}/execute",
        json={"confirm_execution": True},
    )
    client.app.dependency_overrides.pop(get_simulation_provider, None)

    return project_id, created["id"]


def _analysis_url(project_id: int, experiment_id: int) -> str:
    return f"/api/v1/projects/{project_id}/experiments/{experiment_id}/analysis"


def test_get_analysis_returns_200(client: TestClient) -> None:
    project_id, experiment_id = _create_and_execute_experiment(client)

    response = client.get(_analysis_url(project_id, experiment_id))

    assert response.status_code == 200
    body = response.json()
    assert body["experiment_id"] == experiment_id
    assert body["experiment_status"] == "completed"
    assert len(body["variant_metrics"]) == 2
    assert body["data_quality_warnings"] == []


def test_get_analysis_returns_404_for_missing_project(client: TestClient) -> None:
    response = client.get(_analysis_url(999, 1))
    assert response.status_code == 404


def test_get_analysis_returns_404_for_missing_experiment(client: TestClient) -> None:
    project_id = _create_project(client)
    response = client.get(_analysis_url(project_id, 999))
    assert response.status_code == 404


def test_get_analysis_cross_project_isolation_returns_404(client: TestClient) -> None:
    project_id, experiment_id = _create_and_execute_experiment(client)
    other_project_id = _create_project(client)

    response = client.get(_analysis_url(other_project_id, experiment_id))

    assert response.status_code == 404


def test_get_analysis_returns_409_for_draft_experiment(client: TestClient) -> None:
    project_id = _create_project(client)
    evidence_id = _create_evidence(client, project_id)
    persona_ids = _create_personas(client, project_id, evidence_id)
    created = client.post(
        f"/api/v1/projects/{project_id}/experiments",
        json=experiment_create_payload([persona_ids[0]], repeat_count=1),
    ).json()

    response = client.get(_analysis_url(project_id, created["id"]))

    assert response.status_code == 409


def test_analysis_response_never_exposes_raw_prompt_or_provider_output(
    client: TestClient,
) -> None:
    project_id, experiment_id = _create_and_execute_experiment(client)

    response = client.get(_analysis_url(project_id, experiment_id))

    text = response.text
    assert "prompt" not in text.lower()
    assert "system_instructions" not in text
