# Demo Walkthrough

## What this demonstrates

This walkthrough shows the full product workflow on one representative scenario — **Field Notes Sync**, a fictional offline-first field-data capture concept for mobile HVAC technicians. You will move from a product brief and qualitative evidence through evidence-grounded synthetic personas, a controlled two-variant experiment, deterministic analytics, a Proceed / Iterate / Stop decision memo, manually entered real-participant feedback, and a synthetic-vs-human comparison — ending with explicit limitations and a recommended next real-user study. Synthetic personas and simulation results are **decision-support artifacts**, not substitutes for real customers or market validation.

Screenshots in [`docs/screenshots/`](screenshots/) were captured from this same scenario.

## Setup

Requires Python 3.13+, Node.js 20+, and the standard local setup in [`README.md`](../README.md).

### Option A — Deterministic demo (no OpenAI key)

Uses the same test-only fake AI providers as the Playwright suite. No network calls, no API key, reproducible results every time.

```bash
# One-time backend setup
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head   # against backend/data/app.db, or use a fresh DB below

# Terminal 1 — backend with fake providers
cd backend
source .venv/bin/activate
APP_ENV=test E2E_FAKE_AI=true \
  DATABASE_URL=sqlite:///./data/demo.db \
  CORS_ORIGINS=http://localhost:3000 \
  uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
cp ../.env.example .env.local   # NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm install
npm run dev                     # http://localhost:3000
```

`E2E_FAKE_AI=true` is only permitted when `APP_ENV=test` (enforced at startup). Delete `backend/data/demo.db` and re-run `alembic upgrade head` before a clean re-demo.

### Option B — Live OpenAI generation

Use normal development mode and set a real `OPENAI_API_KEY` in `backend/.env`. Results will vary by model output; the workflow and deterministic analytics are the same, but persona text, simulation responses, insights, and decision memo copy will not match screenshots exactly.

```bash
# backend/.env — APP_ENV=development, OPENAI_API_KEY=<your key>
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload
cd frontend && npm run dev
```

### Automated verification of the same flow

The golden-path Playwright spec exercises this scenario end-to-end with fake providers and an isolated database:

```bash
cd frontend
npx playwright install chromium   # one-time
npm run test:e2e                  # 21 tests, no API key
```

See [`docs/testing.md`](testing.md) for full detail.

## Demo flow

Follow these steps in order (~45–90 seconds of narration if the project already exists; ~5–8 minutes if creating from scratch).

### 1. Open or create the product concept

Go to **Projects → New project** and create **Field Notes Sync**:

| Field | Value |
|---|---|
| Name | Field Notes Sync |
| Problem statement | Field technicians re-enter the same job notes twice: once on a paper checklist at the job site, and again into the reporting app once they are back in cell range, because the app has no offline mode. |
| Target user | Independent HVAC and appliance repair technicians who visit six to ten sites a day. |
| Product hypothesis | An offline-first checklist that syncs automatically once a technician is back in range will cut end-of-day paperwork time roughly in half. |
| Success metric | Average minutes spent on end-of-day paperwork per technician per day. |

Or open an existing project that already contains this brief.

### 2. Show the evidence / research context

Open **Evidence** and add at least one item grounded in prior qualitative research:

- **Title:** Interview with a mobile HVAC technician  
- **Content:** The technician described re-entering the same job notes twice — once on a paper checklist at the site, and again into the reporting app back at the truck, because the app has no offline mode. They estimated this costs 20 to 30 minutes per day.  
- **Source label:** Interview #4  

Point out that personas can only cite evidence items that exist in this library.

### 3. Show evidence-grounded personas

Open **Personas → Generate personas** (select 2). Each card should show goals, pain points, evidence references (e.g. `Evidence #1`), confidence level, and any **unsupported assumptions** flagged separately from evidence-backed claims.

Emphasize: these are **synthetic personas derived from supplied evidence**, not real users.

### 4. Configure the two controlled experiment variants

Open **Experiments → New experiment** and create **Offline checklist concept comparison**:

| Field | Value |
|---|---|
| Objective | Compare a fully offline checklist against a lightweight background-sync checklist. |
| Hypothesis | A fully offline-first checklist will feel more trustworthy than partial background sync. |
| Scenario | You are a technician finishing a job site visit with no cell signal. Walk through how you would record your notes and what you'd expect once you're back in range. |
| Personas | Select the 2 generated personas |
| Repeat count | 1 (4 planned runs: 2 personas × 2 variants × 1 repeat) |
| **Variant A** | Fully offline checklist — works entirely offline, queues changes locally, syncs when connection returns |
| **Variant B** | Background partial sync — syncs each completed section whenever a brief connection window appears |

Note the planned-run banner and the responsible-AI notice on the experiments page.

### 5. Run the synthetic experiment

On the experiment **Overview** tab, click **Execute experiment**. Confirm the dialog (4 simulations, settings become immutable, synthetic results do not replace real-user testing).

Wait for execution to finish. Open the **Runs** tab and inspect one run: structured fields (task outcome, scores, objections, evidence references) — no raw prompts.

### 6. Show deterministic analytics

Open the **Analysis** tab. Walk through per-variant metrics (task completion rate, clarity, perceived value, adoption intent), theme counts, evidence coverage, failure breakdown, and persona disagreement.

These numbers are computed **deterministically from persisted run rows** — no LLM involved.

### 7. Show the generated decision memo

Open **Insights → Generate insights**, then **Decision Memo → Generate decision memo**.

Highlight:

- Recommendation labeled **Proceed to real-user validation** (not launch approval)
- Supporting findings, weakest assumptions, risks
- **Recommended real-user test plan** with objective, participants, method, and stopping rule

In deterministic fake-provider mode, the memo favors Variant A (fully offline) on trust and recommends a small moderated field-conditions usability study.

### 8. Enter or inspect real-user feedback

Open **Real Feedback → Add feedback** (after the experiment is completed):

- Participant label: `Participant 1` (pseudonymous — no PII)
- Variant: A
- Summary: preferred knowing notes were saved locally; trusted the fully offline approach on jobs with unreliable signal
- Scores and at least one positive signal

Note the privacy and small-sample limitation notices on this tab.

### 9. Show synthetic-vs-human comparison

Scroll to **Real vs. synthetic comparison** on the Real Feedback tab. Point out:

- Shared themes, synthetic-only themes, real-only themes (exact normalized string matching)
- Score-direction alignment and task-completion deltas
- The interpretation notice: comparison supports learning, not statistical significance or predictive validity

### 10. End with limitation / next decision

Close with what this evidence **does and does not** support:

- **Reasonable judgment:** Synthetic signal and the small real feedback sample suggest prioritizing explicit local-save indicators and probing sync-trust in a real field study — not launching the product.
- **Still requires validation:** Whether real field crews trust offline capture under actual job-site conditions, duplicate-entry rates after reconnect, and whether the concept reduces end-of-day paperwork.
- **Next step:** Run the decision memo's recommended real-user test (5–8 technicians and crew leads, moderated field-conditions comparison of both variants, stop after 5 sessions if the same sync-confidence blocker recurs in at least 4).

The platform helps structure that next experiment; it does not prove market demand.
