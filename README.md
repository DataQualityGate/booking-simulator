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

Ingest events, deduplicate, reconstruct booking states, identify pending/failed operations, infer likely causes and impacted services, and submit an implementation as a PR. Evaluation tooling will be developed independently.

## Non-goals

Live Kafka, production services, payment processing, OpenTelemetry collector, UI, external AI APIs, ETG integrations.
