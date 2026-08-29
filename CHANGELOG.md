# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.1.0] - 2026-08-29

Initial public release.

### Added

- Product brief and text-based evidence library management.
- Evidence-grounded synthetic persona generation, with explicit confidence levels and unsupported assumptions.
- Controlled two-variant (A/B) experiment configuration with a shared scenario, configurable repeat count, explicit execution confirmation, and a deterministic 30-run cap.
- Structured, schema-validated simulation runs with safe, categorized failure records.
- Deterministic analytics: coverage, per-variant metrics, theme counts, evidence coverage, failure breakdown, and persona disagreement — no LLM calls.
- Evidence-linked Insight generation, clustering recurring qualitative signal from completed runs.
- Decision Memo workflow producing a Proceed / Iterate / Stop recommendation with enforced decision-safety rules and a recommended real-user follow-up experiment.
- Anonymized real-participant feedback entry, scoped to completed experiments.
- Deterministic synthetic-versus-human comparison: shared, human-only, and synthetic-only themes, score-direction alignment, and task-completion-rate deltas.
- Full-stack Next.js dashboard covering the entire workflow end to end.
- Backend pytest suite (668 tests, 94% coverage) and a 21-test Playwright end-to-end suite, both running with deterministic fake AI providers and no live OpenAI calls.
- GitHub Actions CI running backend quality checks, frontend quality checks, and the full Playwright suite on every push and pull request to `main`.
