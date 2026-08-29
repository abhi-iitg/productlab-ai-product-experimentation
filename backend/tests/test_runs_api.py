"""HTTP-layer behavior for the read-only SimulationRun API.

Seeded entirely through the API (project -> evidence -> personas ->
experiment -> execute), matching the convention in `test_personas_api.py`.
"""

from fastapi.testclient import TestClient

from app.api.routes.experiments import get_simulation_provider
from app.api.routes.personas import get_persona_provider
from app.llm.exceptions import LLMTimeoutError
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


def _create_evidence(client: TestClient, project_id: int, **overrides: object) -> int:
    payload = {**_EVIDENCE_PAYLOAD, **overrides}
    return client.post(f"/api/v1/projects/{project_id}/evidence", json=payload).json()["id"]


def _create_personas(client: TestClient, project_id: int, evidence_id: int) -> list[int]:
    provider = FakePersonaProvider(result=make_generation_result(evidence_item_id=evidence_id))
    client.app.dependency_overrides[get_persona_provider] = lambda: provider
    response = client.post(
        f"/api/v1/projects/{project_id}/personas/generate", json={"persona_count": 2}
    )
    client.app.dependency_overrides.pop(get_persona_provider, None)
    return [persona["id"] for persona in response.json()["personas"]]


def _create_and_execute_experiment(
    client: TestClient, *, provider: FakeSimulationProvider | None = None
) -> tuple[int, int]:
    project_id = _create_project(client)
    evidence_id = _create_evidence(client, project_id)
    persona_ids = _create_personas(client, project_id, evidence_id)
    created = client.post(
        f"/api/v1/projects/{project_id}/experiments",
        json=experiment_create_payload([persona_ids[0]], repeat_count=1),
    ).json()

    client.app.dependency_overrides[get_simulation_provider] = lambda: (
        provider or FakeSimulationProvider(result=make_simulation_call_result())
    )
    client.post(
        f"/api/v1/projects/{project_id}/experiments/{created['id']}/execute",
        json={"confirm_execution": True},
    )
    client.app.dependency_overrides.pop(get_simulation_provider, None)

    return project_id, created["id"]


def test_list_runs_returns_200(client: TestClient) -> None:
    project_id, experiment_id = _create_and_execute_experiment(client)

    response = client.get(f"/api/v1/projects/{project_id}/experiments/{experiment_id}/runs")

    assert response.status_code == 200
    assert len(response.json()) == 2  # 1 persona x 2 variants x 1 repeat


def test_get_run_returns_200(client: TestClient) -> None:
    project_id, experiment_id = _create_and_execute_experiment(client)
    runs_url = f"/api/v1/projects/{project_id}/experiments/{experiment_id}/runs"
    run_id = client.get(runs_url).json()[0]["id"]

    response = client.get(f"{runs_url}/{run_id}")

    assert response.status_code == 200
    assert response.json()["id"] == run_id


def test_get_run_not_found_returns_404(client: TestClient) -> None:
    project_id, experiment_id = _create_and_execute_experiment(client)

    response = client.get(f"/api/v1/projects/{project_id}/experiments/{experiment_id}/runs/999")

    assert response.status_code == 404


def test_runs_cross_project_isolation_returns_404(client: TestClient) -> None:
    project_id, experiment_id = _create_and_execute_experiment(client)
    other_project_id = _create_project(client)

    response = client.get(f"/api/v1/projects/{other_project_id}/experiments/{experiment_id}/runs")

    assert response.status_code == 404


def test_completed_run_response_shape(client: TestClient) -> None:
    project_id, experiment_id = _create_and_execute_experiment(client)
    run = client.get(f"/api/v1/projects/{project_id}/experiments/{experiment_id}/runs").json()[0]

    assert run["status"] == "completed"
    assert run["task_outcome"] == "completed"
    assert 1 <= run["clarity_score"] <= 5
    assert run["response_summary"]
    assert run["failure_type"] is None
    assert run["failure_message"] is None
    assert run["prompt_version"] == "simulation-v1"


def test_failed_run_response_shape(client: TestClient) -> None:
    provider = FakeSimulationProvider(error=LLMTimeoutError("timed out"))
    project_id, experiment_id = _create_and_execute_experiment(client, provider=provider)
    run = client.get(f"/api/v1/projects/{project_id}/experiments/{experiment_id}/runs").json()[0]

    assert run["status"] == "failed"
    assert run["failure_type"] == "timeout"
    assert run["failure_message"]
    assert run["task_outcome"] is None
    assert run["clarity_score"] is None


def test_run_response_never_exposes_raw_prompt_or_provider_output(client: TestClient) -> None:
    project_id, experiment_id = _create_and_execute_experiment(client)
    response = client.get(f"/api/v1/projects/{project_id}/experiments/{experiment_id}/runs")

    for run in response.json():
        assert "prompt" not in run
        assert "raw_output" not in run
        assert "system_instructions" not in run
