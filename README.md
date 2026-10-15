# Booking Simulator

A **fully synthetic, deterministic** educational dataset generator for distributed hotel-booking observability and impact analysis. No ETG services, private data, keys, external APIs, or third-party Python dependencies.

## Quickstart

Requires Python 3.10+.

```bash
python -m booking_simulator --seed 42 --count 1000 --output build
python -m unittest discover -s tests -v
```

Outputs:

- `build/dataset/events.jsonl`: timestamped service events ordered by observation time
- `build/dataset/topology.json`: conceptual service dependency topology
- `build/dataset/manifest.json`: reproducible dataset metadata
- `build/reference/generation.json`: instructor-only seed and booking count for reproduction
- `build/reference/truth.jsonl`: **answer key** with known status, cause, and affected services

For student datasets, omit `--seed` to choose a random seed. Explicit seeds (such as 42 above) are intended for development and reproduction. The student manifest has a content-based dataset ID and no seed; trace IDs do not directly encode the seed.

**Share only `build/dataset/` with student teams** for exercises. `reference/` is an instructor artifact. The generator is publicly available; an undisclosed seed by itself is *not* sufficient to secure scored assessments.

## Business model

One hotel reservation requests payment authorization, supplier reservation, then confirmation and notification. Four conceptual services: `booking`, `payment`, `supplier`, `notification`. MVP is an **event simulator, not live microservices**.

Four scenarios: `success`, `payment_failed`, `supplier_timeout`, and `message_delay` (with a duplicate event delivery). Timeout currently means `pending`, not definitive failure. Event occurrence and observation timestamps differ.

## Event contract

JSONL records contain `schema_version`, `event_id`, `booking_id`, `trace_id`, `service`, `event_type`, `occurred_at`, `observed_at`, and `attributes`. A repeated `event_id` is a delivery duplicate.

## Student task

Ingest events, deduplicate, reconstruct booking states, identify pending/failed operations, infer likely causes and impacted services, and submit an implementation as a PR. Booking submissions follow the [public prediction contract](docs/prediction-contract.md). Local format validation is available now; grading is developed independently in `engineering-evals`.

## Non-goals

Live Kafka, production services, payment processing, OpenTelemetry collector, UI, external AI APIs, ETG integrations.

## Incident modeling and Impact Analysis

Add `--incidents` to generate six independent exercises covering payment,
supplier and notification outages, a removed API, and breaking/compatible event
schema changes. Includes a contract dependency graph, observable signals and
separate instructor classifications for affected, possibly affected and
unaffected services. A stdlib evaluator counts false positives and uncertainty
errors. See [the exercise contract and scoring guide](docs/incident-impact.md).

```bash
python -m booking_simulator --seed 42 --count 1000 --incidents --output build
python -m booking_simulator.incidents --predictions submission.jsonl --truth build/reference/impact-truth.jsonl
```

## Validate booking predictions

```bash
python -m booking_simulator.predictions --predictions examples/predictions/submission.jsonl --events examples/predictions/events.jsonl
```

Use your generated `dataset/events.jsonl` with your own submission to check exact
booking coverage. The command checks JSONL format and IDs without reading answer
keys or grading the result. See the [versioned contract](docs/prediction-contract.md)
and [record schema](schemas/booking-prediction-v1.schema.json).

## Local evaluator handoff

The [evaluation adapter](docs/evaluation-adapter.md) exports a versioned,
instructor-only request for `engineering-evals`. It validates and joins booking
predictions with separate references without executing student code or grading.
A complete public fixture and smoke command are included.

## Inject data-quality faults

Use `--missing-correlation-rate 0.1 --late-delivery-rate 0.2
--malformed-envelope-rate 0.05` to opt into deterministic telemetry corruption.
Default output is unchanged. See [fault options and instructor ground truth](docs/data-quality-faults.md).
