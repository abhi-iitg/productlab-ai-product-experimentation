# Contributing

This is a personal portfolio project built to demonstrate product and
applied-AI engineering practices. It is not currently seeking external
contributions, but the guidelines below describe how the project is
developed and are useful context for anyone reviewing or extending it.

## Scope Discipline

The MVP scope is locked in `docs/product-specification.md` and
`docs/architecture.md`. Changes that expand scope — new infrastructure, new
AI providers, authentication, and similar additions — should be proposed as
documented future extensions rather than implemented ad hoc.

## Development Principles

- Keep the frontend (Next.js) and backend (FastAPI) responsibilities
  separate; the frontend never accesses the database or the LLM provider
  directly.
- All LLM output must be parsed and validated locally (Pydantic) before it
  is persisted. Never persist unvalidated model output.
- Automated tests never make live calls to the OpenAI API; the LLM
  abstraction is mocked or stubbed in all test runs — including the
  Playwright end-to-end suite, which uses the backend's deterministic
  `E2E_FAKE_AI` test mode (`docs/architecture.md`) instead of a real
  provider.
- Update `docs/architecture.md` in the same change that alters the
  architecture — not after the fact.

## Before Opening a Change

- Confirm the change fits within the locked MVP scope, or is proposed as a
  documented future extension first.
- Run backend lint/tests (`ruff check`, `ruff format --check`, `pytest`)
  and frontend lint/build (`npm run lint`, `npm run build`) before
  submitting a change; run the Playwright suite (`npm run test:e2e`) for
  changes that touch frontend routes/components or backend API contracts.
  `.github/workflows/ci.yml` runs all of this on every push and pull
  request to `main`.
- Keep commits scoped and descriptive.

## Reporting Issues

As a solo portfolio project, issues and notes are currently tracked
informally within the project's documentation rather than an external
issue tracker.
