"""Persona API routes: /api/v1/projects/{project_id}/personas*.

Never calls OpenAI: the `get_persona_provider` FastAPI dependency is
overridden with `FakePersonaProvider` on the shared `client.app`.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.routes.personas import get_persona_provider
from app.core.config import get_settings
from app.llm.exceptions import LLMConfigurationError, LLMTimeoutError
from tests.fakes import FakePersonaProvider, make_generation_result

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


def _api_prefix() -> str:
    return get_settings().API_PREFIX


def _create_project(client: TestClient) -> int:
    response = client.post(f"{_api_prefix()}/projects", json=_PROJECT_PAYLOAD)
    return response.json()["id"]


def _create_evidence(client: TestClient, project_id: int, **overrides: object) -> int:
    payload = {**_EVIDENCE_PAYLOAD, **overrides}
    response = client.post(f"{_api_prefix()}/projects/{project_id}/evidence", json=payload)
    return response.json()["id"]


def _personas_url(project_id: int, persona_id: int | None = None) -> str:
    base = f"{_api_prefix()}/projects/{project_id}/personas"
    return f"{base}/{persona_id}" if persona_id is not None else base


def _generate_url(project_id: int) -> str:
    return f"{_personas_url(project_id)}/generate"


@pytest.fixture
def fake_provider(client: TestClient) -> Iterator[FakePersonaProvider]:
    """Default fake provider override; individual tests may replace it."""
    provider = FakePersonaProvider()
    client.app.dependency_overrides[get_persona_provider] = lambda: provider
    yield provider
    client.app.dependency_overrides.pop(get_persona_provider, None)


def _use_provider(client: TestClient, provider: FakePersonaProvider) -> None:
    client.app.dependency_overrides[get_persona_provider] = lambda: provider


def test_generate_personas_returns_201(
    client: TestClient, fake_provider: FakePersonaProvider
) -> None:
    project_id = _create_project(client)
    evidence_id = _create_evidence(client, project_id)
    fake_provider._result = make_generation_result(evidence_item_id=evidence_id)

    response = client.post(_generate_url(project_id), json={"persona_count": 2})

    assert response.status_code == 201
    body = response.json()
    assert body["project_id"] == project_id
    assert body["prompt_version"] == "persona-v1"
    assert body["persona_count"] == 2
    assert len(body["personas"]) == 2
    assert body["personas"][0]["evidence_references"][0]["evidence_item_id"] == evidence_id


def test_generate_personas_returns_404_for_missing_project(
    client: TestClient, fake_provider: FakePersonaProvider
) -> None:
    response = client.post(_generate_url(999), json={"persona_count": 2})

    assert response.status_code == 404


def test_generate_personas_returns_422_for_no_evidence(
    client: TestClient, fake_provider: FakePersonaProvider
) -> None:
    project_id = _create_project(client)

    response = client.post(_generate_url(project_id), json={"persona_count": 2})

    assert response.status_code == 422


@pytest.mark.parametrize("count", [1, 6])
def test_generate_personas_rejects_invalid_persona_count(
    client: TestClient, fake_provider: FakePersonaProvider, count: int
) -> None:
    project_id = _create_project(client)
    _create_evidence(client, project_id)

    response = client.post(_generate_url(project_id), json={"persona_count": count})

    assert response.status_code == 422


def test_generate_personas_rejects_duplicate_selected_evidence_ids(
    client: TestClient, fake_provider: FakePersonaProvider
) -> None:
    project_id = _create_project(client)
    evidence_id = _create_evidence(client, project_id)

    response = client.post(
        _generate_url(project_id),
        json={"persona_count": 2, "selected_evidence_ids": [evidence_id, evidence_id]},
    )

    assert response.status_code == 422


def test_generate_personas_rejects_empty_selected_evidence_list(
    client: TestClient, fake_provider: FakePersonaProvider
) -> None:
    project_id = _create_project(client)
    _create_evidence(client, project_id)

    response = client.post(
        _generate_url(project_id), json={"persona_count": 2, "selected_evidence_ids": []}
    )

    assert response.status_code == 422


def test_generate_personas_returns_422_for_evidence_not_owned_by_project(
    client: TestClient, fake_provider: FakePersonaProvider
) -> None:
    project_a = _create_project(client)
    project_b = _create_project(client)
    evidence_from_b = _create_evidence(client, project_b)

    response = client.post(
        _generate_url(project_a),
        json={"persona_count": 2, "selected_evidence_ids": [evidence_from_b]},
    )

    assert response.status_code == 422


def test_generate_personas_returns_503_for_missing_provider_configuration(
    client: TestClient,
) -> None:
    project_id = _create_project(client)
    _create_evidence(client, project_id)
    _use_provider(client, FakePersonaProvider(error=LLMConfigurationError("no API key")))

    response = client.post(_generate_url(project_id), json={"persona_count": 2})

    assert response.status_code == 503
    client.app.dependency_overrides.pop(get_persona_provider, None)


def test_generate_personas_returns_502_for_provider_failure(client: TestClient) -> None:
    project_id = _create_project(client)
    _create_evidence(client, project_id)
    _use_provider(client, FakePersonaProvider(error=LLMTimeoutError("timed out")))

    response = client.post(_generate_url(project_id), json={"persona_count": 2})

    assert response.status_code == 502
    client.app.dependency_overrides.pop(get_persona_provider, None)


def test_generate_personas_failure_response_has_no_sensitive_details(client: TestClient) -> None:
    project_id = _create_project(client)
    _create_evidence(client, project_id)
    _use_provider(
        client,
        FakePersonaProvider(
            error=LLMTimeoutError("connection to api.openai.com timed out, key=sk-secret123")
        ),
    )

    response = client.post(_generate_url(project_id), json={"persona_count": 2})

    assert response.status_code == 502
    assert "sk-secret123" not in response.text
    assert "api.openai.com" not in response.text
    assert "Traceback" not in response.text
    client.app.dependency_overrides.pop(get_persona_provider, None)


def test_generate_personas_returns_422_when_context_exceeds_limit(client: TestClient) -> None:
    project_id = _create_project(client)
    _create_evidence(client, project_id, content="x" * 25_000)
    _use_provider(client, FakePersonaProvider())

    response = client.post(_generate_url(project_id), json={"persona_count": 2})

    assert response.status_code == 422
    client.app.dependency_overrides.pop(get_persona_provider, None)


def test_list_personas_for_project(client: TestClient, fake_provider: FakePersonaProvider) -> None:
    project_id = _create_project(client)
    evidence_id = _create_evidence(client, project_id)
    fake_provider._result = make_generation_result(evidence_item_id=evidence_id)
    client.post(_generate_url(project_id), json={"persona_count": 2})

    response = client.get(_personas_url(project_id))

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_personas_returns_404_for_missing_project(client: TestClient) -> None:
    response = client.get(_personas_url(999))

    assert response.status_code == 404


def test_get_persona_returns_200(client: TestClient, fake_provider: FakePersonaProvider) -> None:
    project_id = _create_project(client)
    evidence_id = _create_evidence(client, project_id)
    fake_provider._result = make_generation_result(evidence_item_id=evidence_id)
    created = client.post(_generate_url(project_id), json={"persona_count": 2}).json()
    persona_id = created["personas"][0]["id"]

    response = client.get(_personas_url(project_id, persona_id))

    assert response.status_code == 200
    assert response.json()["id"] == persona_id


def test_get_persona_returns_404_when_missing(client: TestClient) -> None:
    project_id = _create_project(client)

    response = client.get(_personas_url(project_id, 999))

    assert response.status_code == 404


def test_delete_persona_returns_204(client: TestClient, fake_provider: FakePersonaProvider) -> None:
    project_id = _create_project(client)
    evidence_id = _create_evidence(client, project_id)
    fake_provider._result = make_generation_result(evidence_item_id=evidence_id)
    created = client.post(_generate_url(project_id), json={"persona_count": 2}).json()
    persona_id = created["personas"][0]["id"]

    response = client.delete(_personas_url(project_id, persona_id))

    assert response.status_code == 204
    assert client.get(_personas_url(project_id, persona_id)).status_code == 404


def test_delete_persona_returns_404_when_missing(client: TestClient) -> None:
    project_id = _create_project(client)

    response = client.delete(_personas_url(project_id, 999))

    assert response.status_code == 404


def test_persona_isolated_across_projects(
    client: TestClient, fake_provider: FakePersonaProvider
) -> None:
    project_a = _create_project(client)
    project_b = _create_project(client)
    evidence_id = _create_evidence(client, project_a)
    fake_provider._result = make_generation_result(evidence_item_id=evidence_id)
    created = client.post(_generate_url(project_a), json={"persona_count": 2}).json()
    persona_id = created["personas"][0]["id"]

    get_response = client.get(_personas_url(project_b, persona_id))
    delete_response = client.delete(_personas_url(project_b, persona_id))

    assert get_response.status_code == 404
    assert delete_response.status_code == 404
    real = client.get(_personas_url(project_a, persona_id))
    assert real.status_code == 200


def test_deleting_project_cascades_to_personas(
    client: TestClient, fake_provider: FakePersonaProvider
) -> None:
    project_id = _create_project(client)
    evidence_id = _create_evidence(client, project_id)
    fake_provider._result = make_generation_result(evidence_item_id=evidence_id)
    created = client.post(_generate_url(project_id), json={"persona_count": 2}).json()
    persona_id = created["personas"][0]["id"]

    delete_response = client.delete(f"{_api_prefix()}/projects/{project_id}")

    assert delete_response.status_code == 204
    assert client.get(_personas_url(project_id, persona_id)).status_code == 404
