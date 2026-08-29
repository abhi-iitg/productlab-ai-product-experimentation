# Testing

## Backend suite (pytest)

668 tests, 94% statement coverage (measured with `pytest-cov`, from the `backend/` directory). Run:

```bash
cd backend
source .venv/bin/activate
ruff check .
ruff format --check .
pytest --cov=app --cov-report=term-missing
```

The suite covers models, Pydantic schemas (including the raw-untrusted-LLM-output validation boundary), repositories, services, the full API surface, and the Alembic migration cycle, all against an isolated temporary SQLite database created per test (see `backend/tests/conftest.py`).

**No live OpenAI calls.** Every LLM-calling service (`PersonaGenerationService`, `ExperimentExecutionService`, `InsightGenerationService`, `DecisionMemoService`) depends on a typed `Protocol`, not the OpenAI SDK directly. Tests inject deterministic fakes from `backend/tests/fakes.py` — canned successful results or canned provider errors, with no network access and no API key required.

### Alembic

```bash
cd backend
alembic check                    # migrations match current models
alembic upgrade head             # apply to a fresh database
```

CI runs both against a dedicated `data/ci-alembic-check.db`, never a developer's local database.

## Frontend end-to-end suite (Playwright)

21 tests across `frontend/e2e/01-golden-path.spec.ts` and `frontend/e2e/02-error-and-responsive.spec.ts`, driving the **real** FastAPI app and the **real** Next.js app together through a real Chromium browser — no mocked HTTP layer, no component-level stubs. Coverage includes the full workflow (project brief → evidence → persona generation → experiment creation and the 30-run cap → execution → run detail → analysis → Insights → Decision Memo → real feedback and its comparison view), a not-found error scenario, and a mobile-viewport smoke test.

```bash
cd frontend
npx playwright install chromium   # one-time
npm run test:e2e
```

**Isolated E2E database.** `playwright.config.ts`'s `webServer` entry runs `backend/scripts/prepare_e2e_db.py` before starting `uvicorn`, which deletes any existing E2E database file and runs `alembic upgrade head` against a dedicated `backend/data/e2e-test.db` — never a developer's own `data/app.db`. Tests create all of their own data through the real UI; nothing is pre-seeded.

**Deterministic fake providers, no live provider guarantee.** The backend is started in a dedicated test mode (`APP_ENV=test`, `E2E_FAKE_AI=true`). `Settings.E2E_FAKE_AI` (`backend/app/core/config.py`) defaults to `False`, and a Pydantic model validator refuses to construct `Settings` at all if `E2E_FAKE_AI=true` is set while `APP_ENV` is anything other than `"test"` — an enforced construction-time guard, not a convention. `app/llm/factory.py` is the single place that selects real-vs-fake providers for all four LLM-calling services; when the guard is satisfied it swaps in `app/llm/e2e_fake_providers.py`'s deterministic, in-process fakes, which derive schema-valid responses from whatever the real UI actually created during that test run. No network access, no OpenAI key, anywhere in the E2E run.

Ports 3100 (frontend) and 8100 (backend) are used for the E2E run — deliberately different from normal dev ports (3000/8000) so the suite can never accidentally attach to an already-running dev server pointed at a real OpenAI key and a real database.

Traces, screenshots, and video are recorded only on failure; `npm run test:e2e:report` opens the last HTML report. `test-results/` and `playwright-report/` are gitignored.

## Frontend static checks

```bash
cd frontend
npm run lint
npm run build              # production build, no backend required
npm audit --omit=dev
```

## Continuous Integration

`.github/workflows/ci.yml` runs on every push and pull request to `main`:

- **backend-quality** — Ruff check, Ruff format check, Alembic check against a fresh database, `pytest`.
- **frontend-quality** — ESLint, production build, `npm audit --omit=dev`.
- **e2e** — the full 21-test Playwright suite, after both quality jobs pass. The Playwright HTML report is uploaded as a build artifact on failure.

CI status is reported by the badge at the top of the root `README.md` rather than a hardcoded claim in this document, since a written claim can go stale the moment a change breaks a build.
