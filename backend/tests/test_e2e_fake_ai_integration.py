"""End-to-end wiring check for E2E fake-provider mode (Stage 9A).

Unlike every other API test in this suite, this file never overrides
`get_*_provider` via `client.app.dependency_overrides`. Instead it sets
`APP_ENV=test` and `E2E_FAKE_AI=true` before the app is built, then drives
the real dependency graph (route -> service -> `app.llm.factory` ->
`E2EFake*Provider`) exactly like Playwright will against the real running
server. This is what actually proves the wiring in `app/llm/factory.py`
and the four `get_*_provider` functions is correct, not just that the fake
providers themselves are schema-valid in isolation.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.database import session as database_session
from app.database.base import Base
from tests.experiment_helpers import experiment_create_payload

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


@pytest.fixture
def e2e_client(temp_database_url: str, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """A TestClient built with APP_ENV=test and E2E_FAKE_AI=true, no dependency overrides."""
    from app.main import create_app

    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("E2E_FAKE_AI", "true")
    get_settings.cache_clear()

    Base.metadata.create_all(bind=database_session.get_engine())

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_settings_report_fake_ai_enabled(e2e_client: TestClient) -> None:
    assert get_settings().E2E_FAKE_AI is True
    assert get_settings().APP_ENV == "test"


def test_full_workflow_uses_fake_providers_end_to_end(e2e_client: TestClient) -> None:
    api = get_settings().API_PREFIX

    project_id = e2e_client.post(f"{api}/projects", json=_PROJECT_PAYLOAD).json()["id"]
    evidence_id = e2e_client.post(
        f"{api}/projects/{project_id}/evidence", json=_EVIDENCE_PAYLOAD
    ).json()["id"]

    persona_response = e2e_client.post(
        f"{api}/projects/{project_id}/personas/generate",
        json={"persona_count": 2},
    )
    assert persona_response.status_code == 201, persona_response.text
    persona_body = persona_response.json()
    assert persona_body["model_name"] == "e2e-fake-persona-provider"
    persona_ids = [p["id"] for p in persona_body["personas"]]
    assert len(persona_ids) == 2
    assert persona_body["personas"][0]["evidence_references"][0]["evidence_item_id"] == evidence_id

    experiment_response = e2e_client.post(
        f"{api}/projects/{project_id}/experiments",
        json=experiment_create_payload(persona_ids),
    )
    assert experiment_response.status_code == 201, experiment_response.text
    experiment_id = experiment_response.json()["id"]

    execute_response = e2e_client.post(
        f"{api}/projects/{project_id}/experiments/{experiment_id}/execute",
        json={"confirm_execution": True},
    )
    assert execute_response.status_code == 200, execute_response.text
    execution = execute_response.json()
    assert execution["failed_runs"] == 0
    assert execution["completed_runs"] > 0

    analysis_response = e2e_client.get(
        f"{api}/projects/{project_id}/experiments/{experiment_id}/analysis"
    )
    assert analysis_response.status_code == 200, analysis_response.text

    insights_response = e2e_client.post(
        f"{api}/projects/{project_id}/experiments/{experiment_id}/insights/generate"
    )
    assert insights_response.status_code == 201, insights_response.text
    insights_body = insights_response.json()
    assert insights_body["model_name"] == "e2e-fake-insight-provider"
    assert insights_body["insight_count"] >= 1

    memo_response = e2e_client.post(
        f"{api}/projects/{project_id}/experiments/{experiment_id}/decision-memo/generate"
    )
    assert memo_response.status_code == 201, memo_response.text
    memo_body = memo_response.json()
    assert memo_body["model_name"] == "e2e-fake-decision-memo-provider"
    assert memo_body["recommendation"] == "proceed"
    assert "real-user validation" in memo_body["executive_summary"].casefold()


def test_e2e_fake_ai_true_outside_test_env_fails_to_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.main import create_app

    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("E2E_FAKE_AI", "true")
    get_settings.cache_clear()

    with pytest.raises(Exception):  # noqa: B017 - pydantic ValidationError from Settings()
        create_app()

    monkeypatch.delenv("E2E_FAKE_AI", raising=False)
    get_settings.cache_clear()
