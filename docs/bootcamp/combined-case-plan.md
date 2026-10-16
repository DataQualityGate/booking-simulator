# Combined bootcamp: AI-native SDLC + Business Process Observability

## Goal
Keep Booking Simulator as a standalone deterministic, fully synthetic engineering playground. Extend the existing observability and impact-analysis exercise with an AI-native software development challenge, focused on **verifiable changes**, not simply generated code.

## Student journey
1. Clone and reproduce baseline scenario / event fixtures.
2. Reconstruct booking states; identify failures, causal dependencies and affected bookings.
3. Receive a versioned change request (business rule, API/schema evolution, timeout/retry behavior) and acceptance tests.
4. Develop with an explicit AI-native SDLC: intent/spec, plan, implementation, automated tests, review, revision and human decision.
5. Submit code/PR, impact predictions and evidence manifest; demonstrate absence of regressions.

## Architecture boundaries
- **booking-simulator** owns synthetic workflows, deterministic scenario and change challenge fixtures, topology, public contracts, and examples.
- **engineering-evals** (separate project) owns evaluation logic, protected held-out scenarios, rubric/reporting and isolation of untrusted submissions.
- **student submission** contains working code/PR, prediction JSONL and versioned SDLC evidence (challenge ID, commit, test results, reviews, decisions, known limitations).
- No ETG systems, production data, accounts, API keys or mandatory paid model access.

## Workstream & acceptance
### A. Preserve existing baseline
Keep issues #2–#6 and their completed implementation; preserve backward compatibility of baseline fixtures and incident taxonomy.

### B. Versioned change challenges
Define at least two deterministic modifications with baseline behavior, expected post-change behavior, dependency/impact expectations and regression tests; include one indirect impact case.

### C. AI-native SDLC evidence contract
Publish a machine-validated `sdlc-evidence.json` schema with successful, missing and invalid examples. Verify references to commit/tests/reviews; do not ask for private prompts, secrets, or token usage. Evidence presence is not proof of correctness.

### D. Evaluation adapter
Separate automated correctness/impact checks from process evidence rubric. Include scenario-specific behavior and regression checks, outcome-level impact precision/recall and explainable grading. Run untrusted code only in hardened disposable isolation. Never expose held-out cases through public PR CI.

### E. Onboarding & rehearsal
Document student workflow, one-command quickstart, example submission and review checklist. Dry run with two approaches, including one without commercial AI subscriptions.

## Proposed grading (to confirm with CU)
- 35% correctness/reliability and regression detection
- 30% observability, root-cause and business impact analysis
- 25% quality and traceability of AI-native SDLC
- 10% reproducibility and presentation

## Definition of Done
A working synthetic challenge is reproducible locally, accepts versioned submissions, tests functional changes and business impact, validates SDLC evidence, includes negative tests, and provides a safe path for independently scored hidden variants.

## Out of scope
Building a full agent orchestration platform, production deployment, ETG-specific integration, requiring one AI vendor, or judging student teams by agent count or tokens.