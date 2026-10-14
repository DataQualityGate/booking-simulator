# Incident and impact exercises (suite 1.0)

```bash
python -m booking_simulator --seed 42 --count 1000 --incidents --output build
python -m booking_simulator.incidents --predictions submission.jsonl --truth build/reference/impact-truth.jsonl
```

The optional suite adds six **independent case studies**, not faults injected into the random booking event stream. Each case has its own conceptual observation window with new bookings. `--seed` and `--count` control the original event stream only; every incident case is always included, even at count 1. This ensures coverage without relying on random sampling. No running services are required.

Student inputs:

- `dataset/incidents.jsonl`: case IDs, change/failure description, affected contract where applicable, contextual assumptions and observable service signals.
- `dataset/impact-topology.json`: services and contract dependencies. Each edge points **from consumer to provider**. `required` means normal processing needs that contract; `optional` means a tested fallback exists; `unknown` means behavior is not established.
- `dataset/manifest.json`: includes paths and incident suite version when enabled.

Instructor output: `reference/impact-truth.jsonl`. Share only `dataset/`.
Regenerating the same output directory without `--incidents` removes the three optional suite files.

## Classification semantics

The unit of evaluation is `(case_id, service)` during that case's observation window:

- **affected**: available evidence establishes loss or degradation of the service's expected behavior. Includes a failed provider, blocked booking, or a required notification not triggered. A provider deploying a new API successfully is not itself affected merely because an old consumer breaks.
- **possibly affected**: a relevant dependency exists but evidence and compatibility behavior are insufficient to decide. This is a separate classification, not a weaker synonym for affected.
- **unaffected**: the case establishes normal behavior, a working fallback, or no dependency on the changed capability within this window.

The three sets are disjoint and cover all six services. The audit consumer has no telemetry and its compatibility is unknown. It is possible in upstream booking/contract cases; a notification-only outage does not affect it. Analytics has a tested fallback and remains operational when confirmations are missing. Supplier is unrelated to a payment outage in this window: skipping a reservation request is normal behavior for supplier, whereas sending confirmations is the notification consumer's required business function. This distinction is deliberate and is part of the exercise assumptions.

The impact topology models runtime contract dependencies. The original `topology.json` describes the MVP's conceptual booking flow; it is not an impact propagation graph. Original per-booking `truth.jsonl` labels retain their legacy semantics; use **impact-truth.jsonl** for this service-level task.

## Cases and learning goals

| Case | Learning goal |
| --- | --- |
| payment-outage | Service failure blocks booking and its required notification; unrelated branches must not be flagged |
| supplier-outage | Timeout leaves bookings pending, while required notification remains blocked |
| notification-outage | A downstream failure does not invalidate confirmed bookings |
| payment-api-break | Removal of a used API breaks consumers, even when the provider is healthy |
| confirmation-schema-break | Field removal breaks a strict consumer but not a tolerant one |
| confirmation-schema-add | Compatible additions must not produce blanket impact alerts |

## Submission and scoring

One JSON object per case (JSONL), for example:

```json
{"case_id":"notification-outage","affected_services":["notification"],"possibly_affected_services":[]}
```

Omitted services are predictions of `unaffected`; omitted cases predict all services unaffected and still count in the denominator. Unknown cases/services, duplicate cases/service entries and overlapping sets are rejected. No inference algorithm is supplied: students build their own analysis.

The evaluator reports a confusion matrix (actual labels as rows, predictions as columns), exact correct/total classifications, and:

- `false_positives`: actually unaffected services predicted affected **or possible**;
- `false_negatives`: actually affected **or possible** services predicted unaffected;
- `overconfident`: actually possible services predicted affected;
- `underconfident`: actually affected services predicted possible.

These four error counts partition all incorrect classifications. Predicting every reachable node as affected therefore incurs false positives and overconfidence penalties. The suite is public and useful for engineering practice, not a hidden assessment benchmark. Its version is independent of event schema version 1.0. Breaking changes to cases, classifications or dependency semantics require a suite version bump.
