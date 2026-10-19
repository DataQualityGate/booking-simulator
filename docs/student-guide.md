# Bootcamp: AI-native SDLC and Business Process Observability

## Your assignment

Build a small engineering tool that reconstructs synthetic hotel-booking states
from distributed events. Explain what happened, where a process stalled or
failed, and which services might be involved. We evaluate your reasoning,
software behavior and evidence, not the use of any particular AI framework.

The combined case also asks you to implement an assigned behavior/API change,
predict its direct and indirect business impact, and submit tests, review and
human decisions tied to the implementation commit. See the
[combined plan](bootcamp/combined-case-plan.md).

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

## Rehearse the combined contracts

Run these public examples from the repository root:

```bash
python -m booking_simulator.smoke
python -m booking_simulator.challenges --challenge supplier-recovery-v1
python -m booking_simulator.evidence --evidence examples/evidence/valid.json --repository .
```

The smoke report says `valid: true` and `student_correctness_demonstrated: false`.
It rehearses public contract compatibility without running a student solution.
The evidence example uses `not_run` and a baseline commit: it demonstrates format
and pinned file existence, not a completed challenge. Optional pinned checks
require Git supporting `--no-lazy-fetch`; see the [evidence guide](sdlc-evidence.md).

Your instructor assigns one immutable [change challenge](change-challenges.md),
a dataset, the code/runtime interface and the submission location. The public
catalog contains the requested behavior and acceptance examples, not its solution.
The [combined submission contract](combined-submission.md) is authoritative for
file names, identity, coverage and evaluator handoff.

## Build your observability tool

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

If working only on an assigned observability exercise, the incident track can be
optional. In the combined case it is required: consume `incidents.jsonl` and
`impact-topology.json`, and submit a separate file keyed by `case_id` with
`affected_services` and `possibly_affected_services`. Do not mix it into booking
predictions. Explain uncertain dependencies and avoid flagging every reachable
service as definitely affected.

## Implement the assigned change

1. Reproduce the challenge baseline and record intent, spec, assumptions and a plan.
2. Implement only the requested opt-in behavior/API change in the specified target.
   For this track, editing the generator is expected; preserve default behavior and
   all unrelated scenarios. Do not change answer semantics to improve your score.
3. Add tests for post-change behavior, unchanged defaults, pending versus failed,
   delayed/duplicate delivery, full replay, multiple bookings and both options
   together where assigned. Keep logical booking/notification effects idempotent.
4. Predict direct and indirect business outcome changes, including justified
   uncertainty. The combined impact file covers all six public incident IDs and
   the selected challenge ID, each exactly once; see the versioned contract.
5. Obtain an independent review, fix findings or record explicit risk acceptance,
   and record the human decision and limitations. Free, paid and manual workflows
   use the same criteria; model choice and token count earn no credit.
6. Pin the implementation commit in both `submission.json` and `sdlc-evidence.json`.
   Local artifact references are checked at that commit. Keep the submission bundle
   outside the pinned code snapshot if needed: a file cannot contain the hash of
   the very commit that introduces that file. Follow-up submission metadata may
   reference the prior implementation commit, not a moving branch.

Never submit prompts, private chats, API keys or personal reviewer details. A role
label is sufficient. Report actual test results, not assumed success. Evidence
validation establishes structure/existence; independent execution establishes
correctness, and a human reviews the engineering decisions.

## Deliverables

- Source code and a short README with the exact command to run your tool,
  Python/runtime requirements and expected output locations.
- For the combined case, `submission.json` plus the local files named by its
  `booking_predictions`, `impact_predictions` and `evidence` fields. The latter is
  `sdlc-evidence.json`; it must match the submission's challenge ID and commit SHA.
  Use [the complete synthetic bundle](../examples/combined/submission.json) as a
  format example and create your own predictions/evidence.
- For observability-only assignments, booking prediction JSONL (historically
  called `submission.jsonl`) and incident predictions if assigned. Do not confuse
  that JSONL with the combined `submission.json` manifest.
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
3. Keep the task focused. Add the observability tool in an agreed student directory.
   For the change challenge, modify its documented generator/API target while
   preserving default behavior. Do not rewrite references or expected results to
   fit your implementation.
4. Run tests and the prediction validator. Inspect `git diff` and `git status`
   before committing; exclude `reference/`, generated outputs and credentials.
5. Push the task branch to your fork. Open a PR targeting the upstream `main`,
   link the assigned task, and describe behavior, assumptions and validation.
6. Include your own intent/spec, tests, review findings, human decisions and a
   short demo: reproduce baseline, show the change, show a replay/timeout
   regression, explain indirect impact and demonstrate a validation failure.
   Prepare the combined bundle for the pinned implementation commit separately
   if necessary; never publish hidden assessment data.
7. Address review comments. A green format check or bot review is not an
   assessment score, and PR code is not automatically trusted.

Use [CONTRIBUTING.md](../CONTRIBUTING.md) for repository conventions and
[sandbox-security.md](sandbox-security.md) for the execution boundary.

## Before you start

Confirm the assigned dataset/challenge, implementation target, runtime command,
output paths, submission channel and agreed rubric with the instructor. The
public format examples and smoke command are available now. Protected execution,
held-out scoring and the full student pilot are separate instructor responsibilities;
this repository does not provision them. Keep generated reference data out of
student execution, even when asking an AI tool for help.
