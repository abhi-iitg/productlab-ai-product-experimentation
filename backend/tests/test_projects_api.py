"""Project API routes: /api/v1/projects."""

from fastapi.testclient import TestClient

from app.core.config import get_settings

_CREATE_PAYLOAD = {
    "name": "Portfolio Discovery Tool",
    "problem_statement": "Teams decide on intuition alone.",
    "target_user": "Early-stage product managers.",
    "product_hypothesis": "Evidence-grounded personas surface weak assumptions.",
    "success_metric": "Time to a decision memo.",
    "assumptions": ["Users have existing evidence."],
}


def _prefix() -> str:
    return f"{get_settings().API_PREFIX}/projects"


def test_create_project_returns_201(client: TestClient) -> None:
    response = client.post(_prefix(), json=_CREATE_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == _CREATE_PAYLOAD["name"]
    assert body["status"] == "draft"
    assert body["id"] is not None


def test_create_project_rejects_blank_name(client: TestClient) -> None:
    response = client.post(_prefix(), json={**_CREATE_PAYLOAD, "name": "   "})

    assert response.status_code == 422


def test_create_project_deduplicates_assumptions(client: TestClient) -> None:
    payload = {**_CREATE_PAYLOAD, "assumptions": ["Same", "same", " Same "]}

    response = client.post(_prefix(), json=payload)

    assert response.status_code == 201
    assert response.json()["assumptions"] == ["Same"]


def test_list_projects_returns_created_projects(client: TestClient) -> None:
    client.post(_prefix(), json=_CREATE_PAYLOAD)
    client.post(_prefix(), json={**_CREATE_PAYLOAD, "name": "Second Project"})

    response = client.get(_prefix())

    assert response.status_code == 200
    names = [item["name"] for item in response.json()]
    assert names == ["Portfolio Discovery Tool", "Second Project"]


def test_get_project_returns_200(client: TestClient) -> None:
    created = client.post(_prefix(), json=_CREATE_PAYLOAD).json()

    response = client.get(f"{_prefix()}/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_project_returns_404_when_missing(client: TestClient) -> None:
    response = client.get(f"{_prefix()}/999")

    assert response.status_code == 404
    assert "detail" in response.json()


def test_update_project_returns_200(client: TestClient) -> None:
    created = client.post(_prefix(), json=_CREATE_PAYLOAD).json()

    response = client.patch(f"{_prefix()}/{created['id']}", json={"name": "Renamed"})

    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"


def test_update_project_updated_at_advances(client: TestClient) -> None:
    created = client.post(_prefix(), json=_CREATE_PAYLOAD).json()

    response = client.patch(f"{_prefix()}/{created['id']}", json={"name": "Renamed Again"})

    assert response.status_code == 200
    assert response.json()["updated_at"] >= created["updated_at"]


def test_update_project_rejects_empty_patch(client: TestClient) -> None:
    created = client.post(_prefix(), json=_CREATE_PAYLOAD).json()

    response = client.patch(f"{_prefix()}/{created['id']}", json={})

    assert response.status_code == 422


def test_update_project_returns_404_when_missing(client: TestClient) -> None:
    response = client.patch(f"{_prefix()}/999", json={"name": "New Name"})

    assert response.status_code == 404


def test_delete_project_returns_204(client: TestClient) -> None:
    created = client.post(_prefix(), json=_CREATE_PAYLOAD).json()

    response = client.delete(f"{_prefix()}/{created['id']}")

    assert response.status_code == 204
    assert client.get(f"{_prefix()}/{created['id']}").status_code == 404


def test_delete_project_returns_404_when_missing(client: TestClient) -> None:
    response = client.delete(f"{_prefix()}/999")

    assert response.status_code == 404
