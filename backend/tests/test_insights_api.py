"""HTTP-layer behavior for the Insight generation/list API.

Seeded entirely through the API (project -> evidence -> personas ->
experiment -> execute -> insights/generate), matching the convention in
`test_runs_api.py`.
"""

from fastapi.testclient import TestClient

from app.api.routes.analysis import get_insight_provider
from app.api.routes.experiments import get_simulation_provider
from app.api.routes.personas import get_persona_provider
from app.llm.exceptions import LLMConfigurationError, LLMTimeoutError
from tests.experiment_helpers import experiment_create_payload
from tests.fakes import (
    FakeInsightProvider,
    FakePersonaProvider,
    FakeSimulationProvider,
    make_generation_result,
    make_insight_generation_result,
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


def _insights_generate_url(project_id: int, experiment_id: int) -> str:
    return f"/api/v1/projects/{project_id}/experiments/{experiment_id}/insights/generate"


def _insights_url(project_id: int, experiment_id: int) -> str:
    return f"/api/v1/projects/{project_id}/experiments/{experiment_id}/insights"


def _use_insight_provider(client: TestClient, provider: FakeInsightProvider) -> None:
    client.app.dependency_overrides[get_insight_provider] = lambda: provider


def _default_insight_provider(client: TestClient, project_id: int, experiment_id: int) -> None:
    run_ids = [
        run["id"]
        for run in client.get(
            f"/api/v1/projects/{project_id}/experiments/{experiment_id}/runs"
        ).json()
        if run["status"] == "completed"
    ]
    _use_insight_provider(
        client,
        FakeInsightProvider(
            result=make_insight_generation_result(supporting_run_ids=run_ids, persona_count=1)
        ),
    )


def test_generate_insights_returns_201(client: TestClient) -> None:
    project_id, experiment_id = _create_and_execute_experiment(client)
    _default_insight_provider(client, project_id, experiment_id)

    response = client.post(_insights_generate_url(project_id, experiment_id))

    assert response.status_code == 201
    body = response.json()
    assert body["experiment_id"] == experiment_id
    assert body["prompt_version"] == "insight-v1"
    assert body["insight_count"] == 1
    assert len(body["insights"]) == 1
    client.app.dependency_overrides.pop(get_insight_provider, None)


def test_generate_insights_returns_404_for_missing_project(client: TestClient) -> None:
    response = client.post(_insights_generate_url(999, 1))
    assert response.status_code == 404


def test_generate_insights_returns_404_for_missing_experiment(client: TestClient) -> None:
    project_id = _create_project(client)
    response = client.post(_insights_generate_url(project_id, 999))
    assert response.status_code == 404


def test_generate_insights_cross_project_isolation_returns_404(client: TestClient) -> None:
    project_id, experiment_id = _create_and_execute_experiment(client)
    other_project_id = _create_project(client)

    response = client.post(_insights_generate_url(other_project_id, experiment_id))

    assert response.status_code == 404


def test_generate_insights_returns_409_for_ineligible_experiment(client: TestClient) -> None:
    project_id = _create_project(client)
    evidence_id = _create_evidence(client, project_id)
    persona_ids = _create_personas(client, project_id, evidence_id)
    created = client.post(
        f"/api/v1/projects/{project_id}/experiments",
        json=experiment_create_payload([persona_ids[0]], repeat_count=1),
    ).json()

    response = client.post(_insights_generate_url(project_id, created["id"]))

    assert response.status_code == 409


def test_generate_insights_returns_409_for_duplicate_generation(client: TestClient) -> None:
    project_id, experiment_id = _create_and_execute_experiment(client)
    _default_insight_provider(client, project_id, experiment_id)
    client.post(_insights_generate_url(project_id, experiment_id))
    _default_insight_provider(client, project_id, experiment_id)

    response = client.post(_insights_generate_url(project_id, experiment_id))

    assert response.status_code == 409
    client.app.dependency_overrides.pop(get_insight_provider, None)


def test_generate_insights_returns_503_for_missing_provider_configuration(
    client: TestClient,
) -> None:
    project_id, experiment_id = _create_and_execute_experiment(client)
    _use_insight_provider(client, FakeInsightProvider(error=LLMConfigurationError("no key")))

    response = client.post(_insights_generate_url(project_id, experiment_id))

    assert response.status_code == 503
    client.app.dependency_overrides.pop(get_insight_provider, None)


def test_generate_insights_returns_502_for_provider_failure(client: TestClient) -> None:
    project_id, experiment_id = _create_and_execute_experiment(client)
    _use_insight_provider(client, FakeInsightProvider(error=LLMTimeoutError("timed out")))

    response = client.post(_insights_generate_url(project_id, experiment_id))

    assert response.status_code == 502
    client.app.dependency_overrides.pop(get_insight_provider, None)


def test_generate_insights_failure_response_has_no_sensitive_details(client: TestClient) -> None:
    project_id, experiment_id = _create_and_execute_experiment(client)
    _use_insight_provider(
        client,
        FakeInsightProvider(
            error=LLMTimeoutError("connection to api.openai.com timed out, key=sk-secret123")
        ),
    )

    response = client.post(_insights_generate_url(project_id, experiment_id))

    assert response.status_code == 502
    assert "sk-secret123" not in response.text
    assert "api.openai.com" not in response.text
    assert "Traceback" not in response.text
    client.app.dependency_overrides.pop(get_insight_provider, None)


def test_list_insights_returns_200_after_generation(client: TestClient) -> None:
    project_id, experiment_id = _create_and_execute_experiment(client)
    _default_insight_provider(client, project_id, experiment_id)
    client.post(_insights_generate_url(project_id, experiment_id))
    client.app.dependency_overrides.pop(get_insight_provider, None)

    response = client.get(_insights_url(project_id, experiment_id))

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_list_insights_returns_404_before_generation(client: TestClient) -> None:
    project_id, experiment_id = _create_and_execute_experiment(client)

    response = client.get(_insights_url(project_id, experiment_id))

    assert response.status_code == 404
