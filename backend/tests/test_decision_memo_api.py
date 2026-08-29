"""HTTP-layer behavior for the Decision Memo generation/retrieval API.

Seeded entirely through the API (project -> evidence -> personas ->
experiment -> execute -> insights/generate -> decision-memo/generate),
matching the convention in `test_runs_api.py`.
"""

from fastapi.testclient import TestClient

from app.api.routes.analysis import get_decision_memo_provider, get_insight_provider
from app.api.routes.experiments import get_simulation_provider
from app.api.routes.personas import get_persona_provider
from app.llm.exceptions import LLMConfigurationError, LLMTimeoutError
from tests.experiment_helpers import experiment_create_payload
from tests.fakes import (
    FakeDecisionMemoProvider,
    FakeInsightProvider,
    FakePersonaProvider,
    FakeSimulationProvider,
    make_decision_memo_candidate,
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


def _create_experiment_with_insights(client: TestClient) -> tuple[int, int]:
    project_id = _create_project(client)
    evidence_id = _create_evidence(client, project_id)
    persona_ids = _create_personas(client, project_id, evidence_id)
    created = client.post(
        f"/api/v1/projects/{project_id}/experiments",
        json=experiment_create_payload(persona_ids, repeat_count=1),
    ).json()
    experiment_id = created["id"]

    client.app.dependency_overrides[get_simulation_provider] = lambda: FakeSimulationProvider(
        result=make_simulation_call_result(evidence_item_id=evidence_id)
    )
    client.post(
        f"/api/v1/projects/{project_id}/experiments/{experiment_id}/execute",
        json={"confirm_execution": True},
    )
    client.app.dependency_overrides.pop(get_simulation_provider, None)

    run_ids = [
        run["id"]
        for run in client.get(
            f"/api/v1/projects/{project_id}/experiments/{experiment_id}/runs"
        ).json()
        if run["status"] == "completed"
    ]
    client.app.dependency_overrides[get_insight_provider] = lambda: FakeInsightProvider(
        result=make_insight_generation_result(supporting_run_ids=run_ids, persona_count=2)
    )
    client.post(f"/api/v1/projects/{project_id}/experiments/{experiment_id}/insights/generate")
    client.app.dependency_overrides.pop(get_insight_provider, None)

    return project_id, experiment_id


def _insight_ids(client: TestClient, project_id: int, experiment_id: int) -> list[int]:
    response = client.get(f"/api/v1/projects/{project_id}/experiments/{experiment_id}/insights")
    return [insight["id"] for insight in response.json()]


def _memo_generate_url(project_id: int, experiment_id: int) -> str:
    return f"/api/v1/projects/{project_id}/experiments/{experiment_id}/decision-memo/generate"


def _memo_url(project_id: int, experiment_id: int) -> str:
    return f"/api/v1/projects/{project_id}/experiments/{experiment_id}/decision-memo"


def _use_decision_provider(client: TestClient, provider: FakeDecisionMemoProvider) -> None:
    client.app.dependency_overrides[get_decision_memo_provider] = lambda: provider


def test_generate_decision_memo_returns_201(client: TestClient) -> None:
    project_id, experiment_id = _create_experiment_with_insights(client)
    candidate = make_decision_memo_candidate(
        supporting_insight_ids=_insight_ids(client, project_id, experiment_id)
    )
    _use_decision_provider(client, FakeDecisionMemoProvider(result=candidate))

    response = client.post(_memo_generate_url(project_id, experiment_id))

    assert response.status_code == 201
    body = response.json()
    assert body["experiment_id"] == experiment_id
    assert body["recommendation"] == "proceed"
    assert body["prompt_version"] == "decision-v1"
    assert "real-user validation" in body["executive_summary"].lower()
    client.app.dependency_overrides.pop(get_decision_memo_provider, None)


def test_generate_decision_memo_returns_404_for_missing_project(client: TestClient) -> None:
    response = client.post(_memo_generate_url(999, 1))
    assert response.status_code == 404


def test_generate_decision_memo_returns_404_for_missing_experiment(client: TestClient) -> None:
    project_id = _create_project(client)
    response = client.post(_memo_generate_url(project_id, 999))
    assert response.status_code == 404


def test_generate_decision_memo_cross_project_isolation_returns_404(client: TestClient) -> None:
    project_id, experiment_id = _create_experiment_with_insights(client)
    other_project_id = _create_project(client)

    response = client.post(_memo_generate_url(other_project_id, experiment_id))

    assert response.status_code == 404


def test_generate_decision_memo_returns_409_when_insights_missing(client: TestClient) -> None:
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

    response = client.post(_memo_generate_url(project_id, created["id"]))

    assert response.status_code == 409


def test_generate_decision_memo_returns_409_for_duplicate_generation(client: TestClient) -> None:
    project_id, experiment_id = _create_experiment_with_insights(client)
    candidate = make_decision_memo_candidate(
        supporting_insight_ids=_insight_ids(client, project_id, experiment_id)
    )
    _use_decision_provider(client, FakeDecisionMemoProvider(result=candidate))
    client.post(_memo_generate_url(project_id, experiment_id))

    response = client.post(_memo_generate_url(project_id, experiment_id))

    assert response.status_code == 409
    client.app.dependency_overrides.pop(get_decision_memo_provider, None)


def test_generate_decision_memo_returns_503_for_missing_provider_configuration(
    client: TestClient,
) -> None:
    project_id, experiment_id = _create_experiment_with_insights(client)
    _use_decision_provider(client, FakeDecisionMemoProvider(error=LLMConfigurationError("no key")))

    response = client.post(_memo_generate_url(project_id, experiment_id))

    assert response.status_code == 503
    client.app.dependency_overrides.pop(get_decision_memo_provider, None)


def test_generate_decision_memo_returns_502_for_provider_failure(client: TestClient) -> None:
    project_id, experiment_id = _create_experiment_with_insights(client)
    _use_decision_provider(client, FakeDecisionMemoProvider(error=LLMTimeoutError("timed out")))

    response = client.post(_memo_generate_url(project_id, experiment_id))

    assert response.status_code == 502
    client.app.dependency_overrides.pop(get_decision_memo_provider, None)


def test_generate_decision_memo_returns_502_for_unsafe_recommendation(client: TestClient) -> None:
    project_id, experiment_id = _create_experiment_with_insights(client)
    candidate = make_decision_memo_candidate(
        supporting_insight_ids=_insight_ids(client, project_id, experiment_id),
        executive_summary="This proves product-market fit; ready to launch.",
    )
    _use_decision_provider(client, FakeDecisionMemoProvider(result=candidate))

    response = client.post(_memo_generate_url(project_id, experiment_id))

    assert response.status_code == 502
    client.app.dependency_overrides.pop(get_decision_memo_provider, None)


def test_generate_decision_memo_failure_response_has_no_sensitive_details(
    client: TestClient,
) -> None:
    project_id, experiment_id = _create_experiment_with_insights(client)
    _use_decision_provider(
        client,
        FakeDecisionMemoProvider(
            error=LLMTimeoutError("connection to api.openai.com timed out, key=sk-secret123")
        ),
    )

    response = client.post(_memo_generate_url(project_id, experiment_id))

    assert response.status_code == 502
    assert "sk-secret123" not in response.text
    assert "api.openai.com" not in response.text
    assert "Traceback" not in response.text
    client.app.dependency_overrides.pop(get_decision_memo_provider, None)


def test_get_decision_memo_returns_200_after_generation(client: TestClient) -> None:
    project_id, experiment_id = _create_experiment_with_insights(client)
    candidate = make_decision_memo_candidate(
        supporting_insight_ids=_insight_ids(client, project_id, experiment_id)
    )
    _use_decision_provider(client, FakeDecisionMemoProvider(result=candidate))
    client.post(_memo_generate_url(project_id, experiment_id))
    client.app.dependency_overrides.pop(get_decision_memo_provider, None)

    response = client.get(_memo_url(project_id, experiment_id))

    assert response.status_code == 200
    assert response.json()["experiment_id"] == experiment_id


def test_get_decision_memo_returns_404_before_generation(client: TestClient) -> None:
    project_id, experiment_id = _create_experiment_with_insights(client)

    response = client.get(_memo_url(project_id, experiment_id))

    assert response.status_code == 404
