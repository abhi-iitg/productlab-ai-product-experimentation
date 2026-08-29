# Frontend

Next.js App Router frontend (TypeScript) — the Product Dashboard described
in `../docs/architecture.md`. Presentation layer only: it renders product
briefs, the evidence library, personas, experiment configuration and
results, deterministic analytics, Insights, the decision memo, and
anonymized real-participant feedback with its real-vs-synthetic
comparison. It talks only to the FastAPI backend over HTTP — no direct
database or LLM access, and no business logic beyond form validation
lives here.

Implements the complete product-manager workflow against the backend,
including anonymized real-feedback entry and the deterministic comparison
view. A Playwright end-to-end suite (`e2e/`) drives the real FastAPI app
and the real Next.js app together — see "End-to-end tests (Playwright)"
below — and GitHub Actions CI (`../.github/workflows/ci.yml`) runs backend
checks, frontend checks, and the E2E suite on every push and pull request
to `main`.

## Setup

Requires Node.js 20+ and the backend running (see `../README.md` for
backend setup).

```bash
npm install

cp ../.env.example .env.local   # then adjust NEXT_PUBLIC_API_BASE_URL if needed
npm run dev                      # http://localhost:3000
```

The root route (`/`) redirects to `/projects`.

## Environment configuration

| Variable                   | Purpose                         | Local default            |
| --------------------------- | -------------------------------- | -------------------------- |
| `NEXT_PUBLIC_API_BASE_URL`  | Base URL of the FastAPI backend  | `http://localhost:8000`    |

`NEXT_PUBLIC_API_BASE_URL` is read at runtime by the browser (it's a
`NEXT_PUBLIC_` variable, so never put secrets in it) and is centralized in
`lib/api/config.ts` — no component constructs a backend URL directly. If
unset, it falls back to `http://localhost:8000` so the app still runs
locally without a `.env.local` file. The production build (`next build`)
does not require a running backend; API calls only happen at runtime in the
browser.

## Commands

```bash
npm run dev              # start the dev server
npm run lint              # eslint
npm run build             # production build (no backend required)
npm run start             # serve the production build
npm audit --omit=dev      # production dependency vulnerability check
npm run test:e2e          # full-stack Playwright suite (see below)
npm run test:e2e:headed   # same, with a visible browser
npm run test:e2e:report   # open the last HTML report
```

## Routes

| Route                                                | Purpose                                                                 |
| ------------------------------------------------------ | -------------------------------------------------------------------------- |
| `/projects`                                             | Project list, create action                                              |
| `/projects/new`                                          | Create a project (product brief)                                         |
| `/projects/[projectId]`                                 | Project overview: brief, status, workflow progress, links                |
| `/projects/[projectId]/evidence`                         | Evidence library: create/edit/delete, filter by type                     |
| `/projects/[projectId]/personas`                          | Evidence-grounded personas: generate, view, delete                       |
| `/projects/[projectId]/experiments`                       | Experiment list, filter by status                                        |
| `/projects/[projectId]/experiments/new`                   | Create a two-variant experiment                                          |
| `/projects/[projectId]/experiments/[experimentId]`        | Experiment workspace: Overview, Runs, Analysis, Insights, Decision Memo, Real Feedback |

## Product workflow

```
Create project brief
  → add text research evidence
  → generate evidence-grounded personas
  → create a two-variant experiment
  → confirm and execute simulations
  → inspect run-level results
  → inspect deterministic analytics
  → generate evidence-linked Insights
  → generate a Proceed / Iterate / Stop decision memo
  → plan the recommended real-user follow-up experiment
  → enter anonymized real-participant feedback (once completed)
  → review the deterministic real-vs-synthetic comparison
```

## Real Feedback tab

The "Real Feedback" tab on the experiment workspace lets a PM manually
enter anonymized feedback gathered from real participants, once the
experiment is `completed` or `partially_completed` — the "Add feedback"
action is disabled with an explanation otherwise. Each record captures a
pseudonymous participant label, variant, source method, optional session
date, task outcome, three 1–5 scores (rendered as a labeled button group,
not a bare number input), a free-text summary, and five qualitative
categories (positive signals, objections, confusion points, feature
requests, uncertainty notes). Records can be edited and deleted regardless
of experiment status, since manually entered research data may need
correction; delete requires confirmation.

Two notices are shown on every visit to the tab:

- A privacy reminder that only anonymized feedback should be entered — no
  names, emails, phone numbers, account identifiers, or demographic data.
- A qualitative-sample-limitation notice: real feedback is more
  decision-relevant than synthetic feedback, but a small manually entered
  sample is never presented as statistically representative.

Below the feedback list, the comparison view (`HumanComparisonView`)
renders the backend's deterministic `GET .../human-feedback/comparison`
response: real-vs-synthetic sample sizes per variant, side-by-side average
scores (reusing the existing `MetricBar` primitive from the Analysis tab),
task-completion rates, a score-direction agreement table, a shared/
real-only/synthetic-only theme table per qualitative category, the
backend's data-quality warnings, and the fixed interpretation notice —
all rendered as cards, tables, and CSS bars, with **no** chart library, no
statistical-significance claims, no confidence intervals, no
predictive-accuracy claims, and no overall "validation score." When zero
completed synthetic runs exist, the comparison section shows the
backend's `409 Conflict` message instead (there is no synthetic baseline
to compare against); zero human feedback still renders a normal
comparison with an actionable warning, never an error state.

## API dependency

The frontend calls the FastAPI backend exclusively through a centralized,
typed client in `lib/api/` (one module per resource: projects, evidence,
personas, experiments, analysis, human-feedback). `lib/api/client.ts` is the single fetch
wrapper used everywhere — it builds URLs from `NEXT_PUBLIC_API_BASE_URL`,
parses JSON safely (including 204 No Content responses), and maps backend
error responses (404, 409, 422 — both FastAPI's field-validation shape and
the backend's custom `{"detail": "..."}` shape, 502, 503, network failures)
into a single typed `ApiError` with a safe, user-facing message. No
component calls `fetch` directly, and no raw provider or stack-trace detail
from the backend is ever rendered.

Data fetching and caching use TanStack Query (`hooks/`), with mutations
invalidating the specific query keys they affect (see `lib/query-keys.ts`).
Forms use React Hook Form with Zod schemas (`lib/validation/`) for
client-side validation, and surface backend-returned field errors alongside
client-side ones.

## Responsible-AI notice

Every experiment and decision-memo surface displays:

> "Synthetic feedback supports hypothesis generation and experiment
> planning. It does not replace real-user research or predict market
> success."

A `proceed` recommendation is always labeled **"Proceed to real-user
validation"** — never presented as launch approval. The Real Feedback tab
additionally displays:

> "Real-participant feedback entered into this platform may represent a
> small qualitative sample. The comparison supports learning; it does not
> establish statistical significance or market validation."

## End-to-end tests (Playwright)

`e2e/` contains a 21-test Playwright suite (`playwright.config.ts`) that
drives the **real** FastAPI app and the **real** Next.js app together
through a real Chromium browser — no mocked HTTP layer, no component-level
stubs. It covers the full workflow: project brief, evidence, persona
generation, experiment creation (including the 30-run cap), execution,
run detail, analysis, insights, the decision memo, real feedback and its
comparison view, plus a not-found error scenario and a mobile-viewport
smoke test. See `01-golden-path.spec.ts` and `02-error-and-responsive.spec.ts`.

**No live AI provider is ever called.** The backend is started in a
dedicated test mode (`APP_ENV=test`, `E2E_FAKE_AI=true`) that swaps in
deterministic fake providers for persona generation, simulations, Insight
generation, and Decision Memo generation — see
`../docs/architecture.md`#"E2E Fake-Provider Architecture" for
how that mode is wired and guarded. Playwright's `webServer` config starts
both apps itself and tears them down after the run; there is no manual
setup step and no OpenAI key anywhere in the process.

**Database isolation.** The backend webServer entry runs
`backend/scripts/prepare_e2e_db.py` before starting `uvicorn` — it deletes
any existing E2E database file and runs `alembic upgrade head` against a
dedicated `backend/data/e2e-test.db`, never the developer's own
`data/app.db`. Tests create all of their own data through the real UI; no
data is pre-seeded.

### Running locally

```bash
# one-time: install Playwright's Chromium build
npx playwright install chromium

# the backend virtualenv must exist first (playwright.config.ts starts
# uvicorn via backend/.venv/bin/python3, matching backend/README.md setup)
cd ../backend && python -m venv .venv && .venv/bin/pip install -e ".[dev]"
cd ../frontend

npm run test:e2e
```

Ports 3100 (frontend) and 8100 (backend) are used for the E2E run —
deliberately different from the normal dev ports (3000/8000) so the suite
can never accidentally attach to an already-running dev server (which
would silently point it at a real OpenAI key and the real dev database
instead of the fakes above). Traces, screenshots, and video are recorded
only on failure (`npm run test:e2e:report` opens the last HTML report);
`test-results/` and `playwright-report/` are gitignored.

## Current limitations

- No authentication.
- No automatic PII detection on entered feedback — a standing reminder is
  shown instead, matching the backend's deliberate decision not to
  classify free text.
