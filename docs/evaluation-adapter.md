# Local evaluation handoff v1.0

This adapter prepares a **versioned request** for the separate `engineering-evals`
project. It validates and joins data; it does not implement scoring, import a
grader, launch student code or make network calls. No accessible downstream
repository/API is assumed. The JSON boundary can be consumed by that project
without making this simulator depend on its runtime.

## Reproducible public smoke test

Python 3.10+, standard library only, from the repository root:

```bash
python -m booking_simulator.evaluation_adapter --dataset examples/evaluation/dataset --reference examples/evaluation/reference --predictions examples/predictions/submission.jsonl --output build/public-evaluation-request.json
python -m unittest discover -s tests -v
```

Use a new output path on repeated runs: existing files are never overwritten.
All data under `examples/evaluation/`, including its reference and pinned
`request.json`, are deliberately public synthetic fixtures. They are not hidden
assessment data. The output should match `examples/evaluation/request.json`.

For instructor evaluation of a generated dataset, supply `build/dataset`,
`build/reference` and the student's submission. Keep the prepared request
outside `dataset/` and away from student processes and public artifacts.

```python
from booking_simulator.evaluation_adapter import prepare_evaluation
request = prepare_evaluation("build/dataset", "build/reference", "submission.jsonl")
# Instructor-only process: pass request to your trusted evaluator implementation.
```

## Input contract

| Input | Validation |
| --- | --- |
| `dataset/manifest.json` | Event schema `1.0`, nonempty dataset ID, positive integer booking count, relative `events_path` confined to dataset directory (including symlinks) |
| Event JSONL | Valid JSON objects with booking IDs; distinct IDs must equal manifest count; repeated delivery is allowed |
| Student prediction JSONL | [Prediction v1.0](prediction-contract.md); exactly one valid row per event booking ID |
| Instructor `reference/truth.jsonl` | Exactly one row per booking; status, root cause and affected-service values validated using the prediction vocabulary |

Reference `scenario` and other generator metadata are not handed to the grader.
Truth lives outside the public dataset; a symlink to a truth file inside the
dataset is rejected. Quality-fault profiles that retain `booking_id` are
compatible, even if trace IDs or attributes are malformed. The adapter validates
ID coverage, not the complete event schema. Incident `case_id` exercises are
separate and not bundled by this booking adapter.

The instructor is responsible for pairing the right dataset and reference.
Matching ID sets/counts do **not** prove that the seed or answer content matches:
two different generated runs can reuse booking IDs. The request records exact
input hashes for provenance and audit, not authenticity. Store the original
manifest, generation metadata and references together in the trusted workspace.

## Output contract

[`schemas/evaluation-request-v1.schema.json`](../schemas/evaluation-request-v1.schema.json)
is the machine-readable shape. The CLI writes stable sorted JSON with:

| Field | Meaning |
| --- | --- |
| `contract_version` | Exact string `1.0`, version of this handoff |
| `task` | `booking_predictions` |
| `prediction_schema_version` | Exact string `1.0` |
| `dataset` | Dataset ID, event schema version and booking count |
| `input_sha256` | SHA-256 of the exact UTF-8 manifest, events, predictions and truth bytes |
| `records` | One row per booking, sorted by booking ID, containing `booking_id`, `prediction` and `expected` |

`prediction` and `expected` contain `status`, `root_cause_service` and sorted
`affected_services`. Services are sets: ordering has no grading meaning. Raw
paths, seeds and unrelated reference metadata are excluded. Record count must
equal `dataset.booking_count`; booking IDs must be unique. A downstream consumer
must validate these cross-record invariants in addition to JSON Schema and
reject unsupported contract/task/prediction versions. Adding fields or changing
semantics requires an explicitly supported new handoff version.

A downstream grader may compare the three dimensions and emit its own score
report. Weights, partial credit, thresholds and score-report schema are owned by
`engineering-evals`; no scoring rule is implied by this handoff. An empty impact
set or null root cause is structurally valid and may still be wrong.

## Local failures and trust boundary

CLI exit 0 means a validated request was written. Exit 2 means an input, path,
version, validation or filesystem error; the CLI prints a diagnostic without
executing any external code. Input validation finishes before the output is
created. Output inside `dataset/`, existing files and attempts to overwrite
inputs are rejected. Parent directories are created if needed.

**The request contains expected answers.** Run this stage only in a trusted
instructor process after student execution has ended. Never put hidden
references, provider keys or prepared hidden requests into fork PR jobs, logs,
caches or uploaded CI artifacts. Public CI may exercise only the public fixture.
A public generator, seed or fixture is not a secure hidden benchmark.
