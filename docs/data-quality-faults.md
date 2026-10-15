# Data-quality faults v1.0

Opt-in telemetry mutations make ingestion and reconstruction harder without
changing business outcomes. Python standard library only:

```bash
python -m booking_simulator --seed 42 --count 1000 --output build-faults --missing-correlation-rate 0.10 --late-delivery-rate 0.20 --malformed-envelope-rate 0.05 --late-seconds 120
```

| Option | Mutation |
| --- | --- |
| `--missing-correlation-rate` | Remove `trace_id`. `booking_id` is retained so business-level coverage remains observable. |
| `--late-delivery-rate` | Add `--late-seconds` (default 120, integer 1–86400) to `observed_at`; preserve `occurred_at`. Partial delays produce event-time out-of-order delivery. |
| `--malformed-envelope-rate` | Replace the `attributes` object with an array. The envelope violates v1, while the line remains valid JSON. |

Rates must be finite numbers in [0, 1], default 0. Selection is per logical
`event_id` using the seed and fault-specific hashes, independent of the business
RNG and other enabled faults. Rate 1 selects every event; rate 0 selects none.
Fractional rates are probabilities, not exact quotas. Duplicate deliveries of
the same event receive the same faults; their original observation-time gap is
preserved. Faults can combine. Output is sorted again by observation time and
event ID; it is never intentionally unsorted by `observed_at`.

The default v1 dataset remains byte-compatible. All-zero rates are identical to
omitting the flags. Enabled profiles are recorded under `data_quality` in the
student manifest and instructor `generation.json`. They contribute to dataset
identity, including profiles that happen to select zero events. Use the recorded
seed, rates, delay, incident flag and generator revision to reproduce a run.

`reference/data-quality-truth.jsonl` is instructor-only. Each mutated delivery
has its **final physical line number** (1-based) in `dataset/events.jsonl`, its
original event/booking IDs, the applied fault names and a full original envelope.
No originals or per-event fault labels enter `dataset/`. A configured profile
with no selected events writes an empty mutation file. Regenerating without
faults removes that optional reference file.

`reference/truth.jsonl` remains the original booking answer key: data corruption
is not a payment or supplier business failure. Incident exercises remain
independent and may be included with `--incidents`. Normal event-contract
invariants apply to unmutated records only. Students should quarantine malformed
envelopes, retain diagnostic counts and distinguish delivery/quality problems
from business state. A missing trace does not imply a missing booking.

This v1 profile does not remove `booking_id`, emit syntactically invalid JSON,
change timestamps into invalid strings, or require a streaming transport. Those
would require additional explicit exercise and evaluation rules.
