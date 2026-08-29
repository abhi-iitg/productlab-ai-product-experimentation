# From Product Hypothesis to Evidence-Informed Decision

## Product question

Should **Field Notes Sync** — an offline-first field checklist for independent HVAC technicians — prioritize **fully offline capture** (Variant A) or **background partial sync** (Variant B)?

The underlying question is narrow and testable: which approach gives field technicians enough confidence that job notes are safely captured when cellular connectivity is unreliable, without forcing end-of-day re-entry from paper backups?

This is a fictional portfolio scenario. The evidence, personas, simulation runs, and sample real feedback match the deterministic content used in the repository's end-to-end tests and screenshots — no real company, customer, or proprietary research is involved.

## Why this workflow exists

Product teams often choose between concept directions using unstructured intuition or only after building a full prototype. Qualitative evidence is collected but rarely used to stress-test a hypothesis before recruiting real users.

This platform adds a lightweight step between "idea on a whiteboard" and "live experiment with real participants." It organizes evidence, runs a controlled comparison, surfaces weak assumptions, and produces a decision-support memo that always recommends a specific real-user follow-up. It does not automate product judgment.

## Evidence grounding

The project owner adds text evidence before generating personas. Here, one interview note describes a mobile HVAC technician who re-enters job notes twice daily because the reporting app lacks offline mode, costing an estimated 20–30 minutes per day.

Persona generation is constrained to that evidence: each persona cites evidence item IDs and supported claims; unsupported attributes are flagged separately; output referencing unknown evidence IDs is rejected.

Generated personas are **synthetic constructs grounded in supplied text**, not profiles of real people. They structure a thought experiment — they do not represent a researched sample of the target market.

## Controlled experiment

Two variants are tested against the **same two personas** and **same scenario** — a technician finishing a site visit with no cell signal:

| | Variant A: Fully offline checklist | Variant B: Background partial sync |
|---|---|---|
| Behavior | Works offline; queues changes locally; syncs when connection returns | Syncs each section whenever a brief connection window appears |
| Held constant | Personas, scenario, evaluation criteria, repeat count (1), evidence library |

The owner confirms before execution; settings become immutable afterward. Each simulation run sees only its own variant — never the competing one. A 30-run cap per experiment bounds cost.

## Synthetic feedback

Execution produces one structured run per persona × variant × repeat: task outcome, scores, objections, confusion, feature requests, uncertainty notes, and evidence references — all schema-validated before persistence.

In deterministic test mode, Variant A consistently completes with high trust and no objections. Variant B splits by persona: some runs complete with residual sync uncertainty; others flag confusion about duplicate entry after reconnecting.

Synthetic feedback helps surface directional signal and weak assumptions before real-user recruitment. It **cannot** prove real technicians will behave the same way, establish market demand, replace field testing, or guarantee unbiased LLM output.

## Deterministic analytics

The Analytics Service aggregates persisted run rows with **no LLM calls**: per-variant completion rates and average scores, theme counts, evidence coverage, failure breakdown, persona disagreement, and data-quality flags.

Insight generation (a separate LLM step) clusters signal into evidence-linked findings. Decision memo generation then applies **deterministic safety rules** — blocking unsafe `proceed` recommendations and scanning free-text for forbidden market-validation language.

## Decision memo

The memo produces Proceed / Iterate / Stop (Proceed always means *proceed to real-user validation*, not launch approval), supporting findings, weakest assumptions, risks, and a fully specified real-user test plan.

In deterministic mode for this scenario, the memo recommends **Proceed to real-user validation**, favoring Variant A on trust while naming Variant B's sync-state ambiguity as an uncertainty to probe with real field crews.

## Real-user feedback

After completed runs, a PM manually enters **anonymized** feedback: pseudonymous label, variant, scores, summary, and theme lists — no names or emails. One sample entry on Variant A reports preferring local-save confidence on jobs with unreliable signal.

This reflects feedback gathered **outside the platform** and entered afterward. The repository does not recruit participants or run live user tests.

## Synthetic vs human comparison

`HumanComparisonService` deterministically compares real feedback against synthetic runs: per-variant scores, task-completion deltas, score-direction alignment, and shared / human-only / synthetic-only themes (exact normalized string matching).

Agreement can highlight where synthetic and real feedback overlap. **Similarity is not proof of predictive validity** — the comparison view carries a standing small-sample warning on every response.

## Product judgment

A reasonable judgment from this evidence:

- **Directionally prioritize Variant A** for a real field study — synthetic runs and the single real entry both suggest stronger trust when capture does not depend on connectivity.
- **Treat Variant B's sync ambiguity as a hypothesis**, not a resolved finding.
- **Do not commit to a full build** on four synthetic runs and one real feedback entry.

The memo's recommended study — 5–8 technicians and crew leads, moderated field-conditions test, stop after 5 sessions if the same sync-confidence blocker recurs in at least 4 — is an appropriately scoped next step.

## Limitations

- Synthetic personas are not customers.
- Synthetic feedback does not prove demand.
- Small feedback samples do not establish generalizability.
- LLM outputs may contain bias or inconsistency despite schema validation.
- Product decisions still require human judgment.
- This is an MVP experimentation tool — not automated market validation or evidence of customer adoption.

## Next validation step

Run the memo's recommended real-user test: recruit 5–8 field technicians and crew leads with paper backup workflows; compare both variants in realistic field conditions; task participants to capture a note offline and check for duplicates after reconnect; measure local-save confidence and duplicate-entry rate; stop after 5 sessions if the same sync-confidence blocker appears in at least 4.

Only after that study should the team decide whether to iterate on sync indicators, invest in offline-first engineering, or stop the concept in its current form.
