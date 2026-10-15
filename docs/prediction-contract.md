# Booking prediction contract v1.0

This public contract defines **student output**, keyed by `booking_id`, for the
original booking event dataset. Validation uses only public inputs. Grading
belongs to the separate `engineering-evals` project; this module does not score
predictions, reconstruct states, infer causes or read instructor answers.

## Quickstart

Python 3.10+, standard library only:

```bash
python -m booking_simulator.predictions --predictions examples/predictions/submission.jsonl --events examples/predictions/events.jsonl
python -m booking_simulator --seed 42 --count 1000 --output build
# Run your own solution against build/dataset/ to create submission.jsonl, then:
python -m booking_simulator.predictions --predictions submission.jsonl --events build/dataset/events.jsonl
```

`examples/predictions/` contains a three-booking synthetic **format fixture**,
with abbreviated event histories and an illustrative student submission. It is
not an answer key for a generated seed or a reference inference implementation.

## JSONL record schema

UTF-8 JSONL, one object per booking. Order is irrelevant; blank lines are ignored.
All fields are required; extra fields and duplicate JSON object keys are rejected.
NaN and Infinity are not JSON and are rejected.

```json
{"schema_version":"1.0","booking_id":"BOOK-000003","status":"pending","root_cause_service":"supplier","affected_services":["supplier","booking","notification"]}
```

| Field | Allowed values / meaning |
| --- | --- |
| `schema_version` | Exact string `"1.0"` |
| `booking_id` | `BOOK-` followed by at least six ASCII digits; must exactly match an input booking ID when coverage is checked |
| `status` | `confirmed`, `failed`, `pending`: predicted state at the end of the supplied observation window |
| `root_cause_service` | `booking`, `payment`, `supplier`, `notification`, or JSON `null` when no cause is asserted |
| `affected_services` | Array of unique service names from those four services; order has no meaning; empty array is allowed |

Machine-readable record schema: [`schemas/booking-prediction-v1.schema.json`](../schemas/booking-prediction-v1.schema.json)
(JSON Schema draft 2020-12). Cross-record uniqueness, exact input ID coverage,
duplicate JSON keys and JSONL parsing are enforced by the Python validator,
beyond what a single-record JSON Schema can express.

A timeout may be `pending`; it is not automatically `failed`. `null` is not the
string `"null"`. This schema validates vocabulary and shape, not whether a state,
root cause or impact is correct. It deliberately permits an incorrect but
well-formed combination so the evaluator can grade it instead of discarding it.

`affected_services` uses the original **per-booking illustrative impact labels**
in `reference/truth.jsonl`; it is not the newer incident-level classification.
The incident exercises have a separate `case_id` format with
`possibly_affected_services` documented in [incident-impact.md](incident-impact.md).
Do not mix case predictions into booking submissions.

## Validator API and diagnostic report

```python
from booking_simulator.predictions import validate_predictions
report = validate_predictions(jsonl_text, booking_ids={"BOOK-000001"})
```

With no `booking_ids` / no CLI `--events`, checks are structural plus duplicate
booking detection. With `--events`, IDs are collected from the public events file
and the submission must cover them **exactly once**. Event delivery duplicates
are allowed and do not create extra required predictions. The helper only checks
that events are JSON objects with valid booking IDs; it is not an event schema
validator. Invalid or empty event input stops coverage validation.

The report always contains `schema_version`, `valid`, `row_count`, `errors`.
`row_count` counts nonblank input lines, including invalid records. Errors contain
`line` (physical 1-based line number, or `null` for whole-submission errors),
`code`, and a human-readable `message`. Stable error codes:

| Code | Meaning |
| --- | --- |
| `invalid_json` | Invalid JSON, duplicate object keys or nonstandard constants |
| `invalid_prediction` | Wrong record shape, fields, types, version or vocabulary |
| `duplicate_booking` | A booking ID occurs more than once |
| `unknown_booking` | A booking ID is absent from the provided public input |
| `missing_booking` | An input booking has no submission row |
| `empty_submission` | No nonblank prediction records |

Multiple errors may refer to the same row. Missing-ID diagnostics are sorted for
reproducibility. A malformed row never makes a report valid, even if it names an
otherwise required booking. CLI exit codes: **0** valid, **1** invalid submission
(JSON report on stdout), **2** file/encoding/coverage-input or argument error
(diagnostic on stderr). No answer paths or secrets are required in PR CI.

## Versioning and evaluator boundary

The schema version is independent of package and incident-suite versions.
Changes to required fields, accepted vocabulary or field semantics require a
new prediction version; unsupported versions are rejected explicitly. Version
1.0 is strict, so adding optional record fields also requires a separately
supported version. Documentation clarifications and diagnostic message wording
can change without a version bump; consumers should use error codes.

A future `engineering-evals` adapter (Issue #5) should consume:

- the public `dataset/manifest.json` and events to identify the dataset/bookings;
- a validated v1.0 booking prediction JSONL;
- a separately supplied instructor `reference/truth.jsonl`, joined by booking ID.

The relevant grading dimensions are status, root-cause service (including null)
and the unordered affected-service set. Weights, partial credit, aggregate score
format and hidden test execution remain owned by `engineering-evals`; they are
not implemented here. The public generator and format fixtures cannot secure a
hidden assessment by themselves.
