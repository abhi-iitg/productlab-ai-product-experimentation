"""Evidence API routes: /api/v1/projects/{project_id}/evidence."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings

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
    "source_label": "Zoom call, 2026-06-01",
}


def _api_prefix() -> str:
    return get_settings().API_PREFIX


def _create_project(client: TestClient) -> int:
    response = client.post(f"{_api_prefix()}/projects", json=_PROJECT_PAYLOAD)
    return response.json()["id"]


def _evidence_url(project_id: int, evidence_id: int | None = None) -> str:
    base = f"{_api_prefix()}/projects/{project_id}/evidence"
    return f"{base}/{evidence_id}" if evidence_id is not None else base


def test_create_evidence_item_returns_201(client: TestClient) -> None:
    project_id = _create_project(client)

    response = client.post(_evidence_url(project_id), json=_EVIDENCE_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert body["project_id"] == project_id
    assert body["title"] == _EVIDENCE_PAYLOAD["title"]


def test_create_evidence_item_returns_404_for_missing_project(client: TestClient) -> None:
    response = client.post(_evidence_url(999), json=_EVIDENCE_PAYLOAD)

    assert response.status_code == 404


def test_create_evidence_item_rejects_blank_title(client: TestClient) -> None:
    project_id = _create_project(client)

    response = client.post(_evidence_url(project_id), json={**_EVIDENCE_PAYLOAD, "title": "   "})

    assert response.status_code == 422


def test_create_evidence_item_rejects_blank_content(client: TestClient) -> None:
    project_id = _create_project(client)

    response = client.post(_evidence_url(project_id), json={**_EVIDENCE_PAYLOAD, "content": "  "})

    assert response.status_code == 422


def test_create_evidence_item_rejects_invalid_evidence_type(client: TestClient) -> None:
    project_id = _create_project(client)

    response = client.post(
        _evidence_url(project_id), json={**_EVIDENCE_PAYLOAD, "evidence_type": "not-a-type"}
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "evidence_type",
    [
        "interview_note",
        "survey_response",
        "support_ticket",
        "product_review",
        "research_note",
    ],
)
def test_create_evidence_item_supports_every_evidence_type(
    client: TestClient, evidence_type: str
) -> None:
    project_id = _create_project(client)

    response = client.post(
        _evidence_url(project_id), json={**_EVIDENCE_PAYLOAD, "evidence_type": evidence_type}
    )

    assert response.status_code == 201
    assert response.json()["evidence_type"] == evidence_type


def test_list_evidence_items_for_project(client: TestClient) -> None:
    project_id = _create_project(client)
    client.post(_evidence_url(project_id), json=_EVIDENCE_PAYLOAD)
    client.post(_evidence_url(project_id), json={**_EVIDENCE_PAYLOAD, "title": "Second item"})

    response = client.get(_evidence_url(project_id))

    assert response.status_code == 200
    titles = [item["title"] for item in response.json()]
    assert titles == [_EVIDENCE_PAYLOAD["title"], "Second item"]


def test_list_evidence_items_returns_404_for_missing_project(client: TestClient) -> None:
    response = client.get(_evidence_url(999))

    assert response.status_code == 404


def test_get_evidence_item_returns_200(client: TestClient) -> None:
    project_id = _create_project(client)
    created = client.post(_evidence_url(project_id), json=_EVIDENCE_PAYLOAD).json()

    response = client.get(_evidence_url(project_id, created["id"]))

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_evidence_item_returns_404_when_missing(client: TestClient) -> None:
    project_id = _create_project(client)

    response = client.get(_evidence_url(project_id, 999))

    assert response.status_code == 404


def test_update_evidence_item_returns_200(client: TestClient) -> None:
    project_id = _create_project(client)
    created = client.post(_evidence_url(project_id), json=_EVIDENCE_PAYLOAD).json()

    response = client.patch(
        _evidence_url(project_id, created["id"]), json={"title": "Updated title"}
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated title"


def test_update_evidence_item_rejects_empty_patch(client: TestClient) -> None:
    project_id = _create_project(client)
    created = client.post(_evidence_url(project_id), json=_EVIDENCE_PAYLOAD).json()

    response = client.patch(_evidence_url(project_id, created["id"]), json={})

    assert response.status_code == 422


def test_delete_evidence_item_returns_204(client: TestClient) -> None:
    project_id = _create_project(client)
    created = client.post(_evidence_url(project_id), json=_EVIDENCE_PAYLOAD).json()

    response = client.delete(_evidence_url(project_id, created["id"]))

    assert response.status_code == 204
    assert client.get(_evidence_url(project_id, created["id"])).status_code == 404


def test_delete_evidence_item_returns_404_when_missing(client: TestClient) -> None:
    project_id = _create_project(client)

    response = client.delete(_evidence_url(project_id, 999))

    assert response.status_code == 404


def test_evidence_isolated_across_projects(client: TestClient) -> None:
    project_a = _create_project(client)
    project_b = _create_project(client)
    evidence = client.post(_evidence_url(project_a), json=_EVIDENCE_PAYLOAD).json()

    get_response = client.get(_evidence_url(project_b, evidence["id"]))
    patch_response = client.patch(
        _evidence_url(project_b, evidence["id"]), json={"title": "Hijacked"}
    )
    delete_response = client.delete(_evidence_url(project_b, evidence["id"]))

    assert get_response.status_code == 404
    assert patch_response.status_code == 404
    assert delete_response.status_code == 404
    # Still retrievable, unmodified, through its real project.
    real = client.get(_evidence_url(project_a, evidence["id"]))
    assert real.status_code == 200
    assert real.json()["title"] == _EVIDENCE_PAYLOAD["title"]


def test_deleting_project_cascades_to_evidence(client: TestClient) -> None:
    project_id = _create_project(client)
    evidence = client.post(_evidence_url(project_id), json=_EVIDENCE_PAYLOAD).json()

    delete_response = client.delete(f"{_api_prefix()}/projects/{project_id}")

    assert delete_response.status_code == 204
    assert client.get(_evidence_url(project_id, evidence["id"])).status_code == 404
