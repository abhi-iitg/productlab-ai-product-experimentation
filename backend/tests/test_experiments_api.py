"""HTTP-layer behavior for the Experiment CRUD API.

Never touches the database directly: every fixture is built through the
API itself (project -> evidence -> generated personas), matching the
convention in `test_personas_api.py`. `FakePersonaProvider` and
`FakeSimulationProvider` are injected via dependency overrides so no test
here ever calls OpenAI.
"""

from fastapi.testclient import TestClient

from app.api.routes.experiments import get_simulation_provider
from app.api.routes.personas import get_persona_provider
from tests.experiment_helpers import experiment_create_payload
from tests.fakes import FakePersonaProvider, FakeSimulationProvider, make_generation_result

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


def _create_personas(
    client: TestClient, project_id: int, evidence_id: int, count: int = 2
) -> list[int]:
    # PersonaGenerateRequest only allows 2-5 personas per call; generate in
    # batches of up to 5 until at least `count` personas exist, then trim.
    persona_ids: list[int] = []
    remaining = max(count, 2)
    while remaining > 0:
        batch_size = min(max(remaining, 2), 5)
        provider = FakePersonaProvider(
            result=make_generation_result(evidence_item_id=evidence_id, persona_count=batch_size)
        )
        client.app.dependency_overrides[get_persona_provider] = lambda p=provider: p
        response = client.post(
            f"/api/v1/projects/{project_id}/personas/generate",
            json={"persona_count": batch_size},
        )
        client.app.dependency_overrides.pop(get_persona_provider, None)
        persona_ids.extend(persona["id"] for persona in response.json()["personas"])
        remaining -= batch_size
    return persona_ids[:count]


def _seed_project_with_personas(
    client: TestClient, *, persona_count: int = 2
) -> tuple[int, list[int]]:
    project_id = _create_project(client)
    evidence_id = _create_evidence(client, project_id)
    persona_ids = _create_personas(client, project_id, evidence_id, count=persona_count)
    return project_id, persona_ids


def _use_simulation_provider(client: TestClient, provider: FakeSimulationProvider) -> None:
    client.app.dependency_overrides[get_simulation_provider] = lambda: provider


def _run_to_completion(client: TestClient, project_id: int, experiment_id: int) -> None:
    """Drive an experiment to a non-draft status purely through the API."""
    _use_simulation_provider(client, FakeSimulationProvider())
    client.post(
        f"/api/v1/projects/{project_id}/experiments/{experiment_id}/execute",
        json={"confirm_execution": True},
    )
    client.app.dependency_overrides.pop(get_simulation_provider, None)


def test_create_experiment_returns_201(client: TestClient) -> None:
    project_id, persona_ids = _seed_project_with_personas(client, persona_count=1)

    response = client.post(
        f"/api/v1/projects/{project_id}/experiments",
        json=experiment_create_payload(persona_ids),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "draft"
    assert body["persona_ids"] == persona_ids
    assert len(body["variants"]) == 2


def test_create_experiment_project_not_found_returns_404(client: TestClient) -> None:
    response = client.post("/api/v1/projects/999/experiments", json=experiment_create_payload([1]))
    assert response.status_code == 404


def test_create_experiment_invalid_variant_composition_returns_422(client: TestClient) -> None:
    project_id, persona_ids = _seed_project_with_personas(client, persona_count=1)
    payload = experiment_create_payload(persona_ids)
    payload["variants"] = [{"key": "A", "name": "Only A", "description": "desc"}]

    response = client.post(f"/api/v1/projects/{project_id}/experiments", json=payload)

    assert response.status_code == 422


def test_create_experiment_over_run_limit_returns_422(client: TestClient) -> None:
    project_id, persona_ids = _seed_project_with_personas(client, persona_count=6)
    payload = experiment_create_payload(persona_ids, repeat_count=3)

    response = client.post(f"/api/v1/projects/{project_id}/experiments", json=payload)

    assert response.status_code == 422


def test_list_experiments_returns_200(client: TestClient) -> None:
    project_id, persona_ids = _seed_project_with_personas(client, persona_count=1)
    client.post(
        f"/api/v1/projects/{project_id}/experiments", json=experiment_create_payload(persona_ids)
    )

    response = client.get(f"/api/v1/projects/{project_id}/experiments")

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_experiment_returns_200(client: TestClient) -> None:
    project_id, persona_ids = _seed_project_with_personas(client, persona_count=1)
    created = client.post(
        f"/api/v1/projects/{project_id}/experiments", json=experiment_create_payload(persona_ids)
    ).json()

    response = client.get(f"/api/v1/projects/{project_id}/experiments/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_experiment_not_found_returns_404(client: TestClient) -> None:
    project_id = _create_project(client)
    response = client.get(f"/api/v1/projects/{project_id}/experiments/999")
    assert response.status_code == 404


def test_update_experiment_returns_200(client: TestClient) -> None:
    project_id, persona_ids = _seed_project_with_personas(client, persona_count=1)
    created = client.post(
        f"/api/v1/projects/{project_id}/experiments", json=experiment_create_payload(persona_ids)
    ).json()

    response = client.patch(
        f"/api/v1/projects/{project_id}/experiments/{created['id']}",
        json={"name": "Renamed"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"


def test_update_experiment_empty_patch_returns_422(client: TestClient) -> None:
    project_id, persona_ids = _seed_project_with_personas(client, persona_count=1)
    created = client.post(
        f"/api/v1/projects/{project_id}/experiments", json=experiment_create_payload(persona_ids)
    ).json()

    response = client.patch(f"/api/v1/projects/{project_id}/experiments/{created['id']}", json={})

    assert response.status_code == 422


def test_delete_experiment_returns_204(client: TestClient) -> None:
    project_id, persona_ids = _seed_project_with_personas(client, persona_count=1)
    created = client.post(
        f"/api/v1/projects/{project_id}/experiments", json=experiment_create_payload(persona_ids)
    ).json()

    response = client.delete(f"/api/v1/projects/{project_id}/experiments/{created['id']}")

    assert response.status_code == 204
    get_response = client.get(f"/api/v1/projects/{project_id}/experiments/{created['id']}")
    assert get_response.status_code == 404


def test_update_non_draft_experiment_returns_409(client: TestClient) -> None:
    project_id, persona_ids = _seed_project_with_personas(client, persona_count=1)
    created = client.post(
        f"/api/v1/projects/{project_id}/experiments", json=experiment_create_payload(persona_ids)
    ).json()
    _run_to_completion(client, project_id, created["id"])

    response = client.patch(
        f"/api/v1/projects/{project_id}/experiments/{created['id']}",
        json={"name": "Should be rejected"},
    )

    assert response.status_code == 409


def test_delete_non_draft_experiment_returns_409(client: TestClient) -> None:
    project_id, persona_ids = _seed_project_with_personas(client, persona_count=1)
    created = client.post(
        f"/api/v1/projects/{project_id}/experiments", json=experiment_create_payload(persona_ids)
    ).json()
    _run_to_completion(client, project_id, created["id"])

    response = client.delete(f"/api/v1/projects/{project_id}/experiments/{created['id']}")

    assert response.status_code == 409


def test_second_execution_attempt_returns_409(client: TestClient) -> None:
    project_id, persona_ids = _seed_project_with_personas(client, persona_count=1)
    created = client.post(
        f"/api/v1/projects/{project_id}/experiments", json=experiment_create_payload(persona_ids)
    ).json()
    _run_to_completion(client, project_id, created["id"])

    _use_simulation_provider(client, FakeSimulationProvider())
    response = client.post(
        f"/api/v1/projects/{project_id}/experiments/{created['id']}/execute",
        json={"confirm_execution": True},
    )
    client.app.dependency_overrides.pop(get_simulation_provider, None)

    assert response.status_code == 409


def test_cross_project_experiment_access_returns_404(client: TestClient) -> None:
    project_a, personas_a = _seed_project_with_personas(client, persona_count=1)
    project_b = _create_project(client)
    created = client.post(
        f"/api/v1/projects/{project_a}/experiments", json=experiment_create_payload(personas_a)
    ).json()

    response = client.get(f"/api/v1/projects/{project_b}/experiments/{created['id']}")

    assert response.status_code == 404
