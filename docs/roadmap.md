# Roadmap

## Implemented

- Deterministic synthetic booking events: success, declined payment, supplier
  timeout, delayed/duplicate delivery, topology and separated instructor truth.
- Public booking prediction contract v1.0, JSON Schema and local validation
  without answer keys (Issue #2).
- Opt-in deterministic data-quality faults with reproducible per-delivery
  reference mutations and byte-compatible defaults (Issue #3).
- Six independent service/API/schema incident exercises, dependency semantics
  and explicit affected/possible/unaffected classifications (Issue #4).
- Versioned local instructor handoff for engineering-evals, public fixtures and
  smoke test; downstream scoring remains separate (Issue #5).
- Student assignment, fork/PR workflow, executable quickstart and sandbox/hidden
  assessment trust boundaries (Issue #6).
- Standard-library automated tests and public GitHub CI with read-only token
  permissions and no persisted checkout credentials.

- Two versioned public SDLC change challenges, including indirect business impact,
  composed options and multi-booking regression fixtures (Issue #14).
- Versioned SDLC evidence schema, synthetic examples, strict validation and
  optional offline pinned Git artifact inspection (Issue #15).
- Combined submission/evaluator handoff and public offline rehearsal, with
  correctness and process assessment explicitly kept separate (Issue #16).

## Before a scored cohort

- Confirm the proposed rubric and assignment/runtime interfaces with CU.
- Run and record the full student journey with manual/free tooling and AI assistance;
  the public contract smoke is not proof of completed student pilots.
- Provision the protected execution and grading boundary in `engineering-evals`.

## Potential next extensions

- Optional HTTP/event-stream transport without a cloud dependency.
- Additional versioned event schemas, business processes and impact graphs.
- OpenTelemetry and local observability integration.
- A separately implemented isolation runtime and trusted grading service;
  onboarding documents their required boundaries but does not provision them.

Avoid coupling the simulator to a specific AI framework, LLM provider, ETG
platform or grading vendor. Public scenarios and seeds are practice material,
not a hidden benchmark security mechanism.
