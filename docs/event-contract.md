# Event contract v1

Data is synthetic. Every line in `events.jsonl` is a JSON object.

| Field | Meaning |
| --- | --- |
| `schema_version` | Stable schema marker (`1.0`) |
| `event_id` | Logical event identifier; duplicates preserve this ID |
| `booking_id` | Business operation correlation ID |
| `trace_id` | Synthetic trace correlation ID |
| `service` | Emitting conceptual service |
| `event_type` | Domain event kind |
| `occurred_at` | UTC timestamp of the action |
| `observed_at` | UTC timestamp the observer receives it |
| `attributes` | Synthetic metadata |

Messages are sorted by observation time, not necessarily event time. A duplicate delivery may share an event ID with an earlier event but have a different observed timestamp.

The reference truth JSONL contains the booking state, scenario, root-cause service, and modeled affected services. It is provided separately for benchmark design, not intended to be distributed as student input.

The `affected_services` model is illustrative, not verified blast-radius data.
