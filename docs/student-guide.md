# Bootcamp: Business Process Observability

## Your assignment

Build a small engineering tool that reconstructs synthetic hotel-booking states
from distributed events. Explain what happened, where a process stalled or
failed, and which services might be involved. We evaluate your reasoning,
software behavior and evidence, not the use of any particular AI framework.

One booking requests payment, reserves with a supplier, then confirms and sends
a notification. A supplier timeout can leave a booking **pending**, not failed.
Delivery timestamps differ from occurrence timestamps; repeated event IDs are
deliveries of the same logical event. All inputs are synthetic.

## First local run (10–15 minutes)

Requires Git and Python 3.10+; no pip packages, keys, Kafka or ETG access are needed.
Run from the repository root after cloning your fork:

```bash
python -m booking_simulator --seed 42 --count 25 --output build/student-demo
python -m booking_simulator.predictions --predictions examples/predictions/submission.jsonl --events examples/predictions/events.jsonl
```

The second command validates a separate three-booking **format example**, not a
solution to your generated 25 bookings. Expected report: `valid: true`,
`row_count: 3`, `errors: []`. Generated student input is in
`build/student-demo/dataset/`. The sibling `reference/` is an instructor answer
key: do not use it in your solution or submission. For the actual exercise,
use the dataset supplied by your instructor, not a fixed development seed.

Read the [event contract](event-contract.md),
[prediction contract](prediction-contract.md) and
[incident exercise contract](incident-impact.md).

## Build your solution

1. Read only the assigned `dataset/` input. Deduplicate deliveries and preserve
   both occurrence and observation times.
2. Reconstruct one final state per booking at the end of the supplied window.
   Distinguish incomplete evidence from definitive business failure.
3. Produce a prediction JSONL matching v1.0: `schema_version`, `booking_id`,
   `status`, `root_cause_service`, `affected_services`.
4. Provide diagnostics for unusable or contradictory events. If the instructor
   enables quality faults, missing traces, delayed deliveries and malformed
   envelopes are input problems, not automatic booking failures.
5. Validate your own output against the assigned events:

```bash
python -m booking_simulator.predictions --predictions submission.jsonl --events build/student-demo/dataset/events.jsonl
python -m unittest discover -s tests -v
```

`submission.jsonl` must be created by **your** solution. There is no reference
student solver in this repository. Validation checks shape and exact ID coverage;
it does not prove that the predictions are correct. For a supplied dataset,
replace the demo event path with its actual path.

For the optional incident track, consume `incidents.jsonl` and
`impact-topology.json`, and submit a separate file keyed by `case_id` with
`affected_services` and `possibly_affected_services`. Do not mix it into booking
predictions. Explain uncertain dependencies and avoid flagging every reachable
service as definitely affected.

## Deliverables

- Source code and a short README with the exact command to run your tool,
  Python/runtime requirements and expected output locations.
- `submission.jsonl` for the assigned booking dataset; a separate incident
  prediction file if that track is assigned. Share only synthetic public
  exercise results in a public PR.
- Automated tests for success, declined payment, pending timeout,
  delayed/duplicate delivery and any assigned quality faults.
- A short explanation of assumptions, ambiguous cases, quarantine behavior,
  known limitations and impact-analysis reasoning.
- A PR with reproducible validation commands and actual results. Include a
  brief demo script so the instructor can repeat your run.

Keep generated datasets and answer keys out of commits. Use `build/` for local
runs; it is ignored. For a hidden assessment, send only code and the agreed
public sample results through the PR. The instructor controls private datasets,
execution and submission transfer separately.

## Fork and pull-request workflow

1. Fork `DataQualityGate/booking-simulator` in GitHub, then clone **your fork**.
2. Configure `upstream` as `https://github.com/DataQualityGate/booking-simulator.git`.
   Fetch upstream and branch from its current `main`, for example
   `student/booking-observability`. Do not work directly on `main`.
3. Keep the task focused. Add your tool in an agreed student directory rather
   than changing the generator or answer semantics to fit your result.
4. Run tests and the prediction validator. Inspect `git diff` and `git status`
   before committing; exclude `reference/`, generated outputs and credentials.
5. Push the task branch to your fork. Open a PR targeting the upstream `main`,
   link the assigned task, and describe behavior, assumptions and validation.
6. Address review comments. A green format check or bot review is not an
   assessment score, and PR code is not automatically trusted.

Use [CONTRIBUTING.md](../CONTRIBUTING.md) for repository conventions and
[sandbox-security.md](sandbox-security.md) for the execution boundary.
