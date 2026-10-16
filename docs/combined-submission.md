# Combined SDLC and impact submission v1

This extends the existing booking/incident exercise and preserves its public
contracts. Booking Simulator owns public synthetic challenges and handoff formats;
`engineering-evals` owns execution, protected cases, grading and reporting. The
combined bootcamp plan's correctness, observability and SDLC tracks stay separate.

One-command, offline, repeatable rehearsal (stdlib + Python 3.10+, no model required):

```bash
python -m booking_simulator.smoke
```

It generates an ordinary incident-enabled dataset, validates the public example
submission and checks its impact fixture against public references, using temporary
output. It does **not** implement the change challenge, run student code, or claim
that sample SDLC evidence proves correctness.

Submit a directory containing `submission.json`, booking predictions JSONL,
impact predictions JSONL and `sdlc-evidence.json`; put code/tests/reviews in the
repository at the pinned commit. See [complete synthetic example](../examples/combined/submission.json)
and [combined JSON schema](../schemas/combined-submission-v1.schema.json).

| submission.json field | Contract |
| --- | --- |
| schema_version | String `1.0` |
| challenge_id | Versioned public challenge ID |
| commit_sha | Full pinned Git commit ID |
| booking_predictions | Local file in this directory, existing booking prediction v1 JSONL |
| impact_predictions | Local file, one impact record per incident **and selected challenge** |
| evidence | Local file, [SDLC evidence v1](sdlc-evidence.md) |

All file references stay inside the submission directory, including symlink
resolution. Remote files, traversal and unknown fields are rejected. Challenge ID
and commit SHA must match the evidence manifest. Impact records contain exactly
`case_id`, `affected_services` and `possibly_affected_services`; arrays must be
unique disjoint subsets of the six services in the incident topology. Omitted
services mean unaffected. Exact coverage is required; missing/extra/duplicate cases
are errors. The six existing incident IDs and selected challenge ID are independent
windows, not one shared timeline. This stricter combined coverage rule leaves the
legacy incident evaluator's missing-case behavior unchanged.

Instructor adapter example:

```bash
python -m booking_simulator.combined_evaluation \
  --dataset examples/evaluation/dataset \
  --reference examples/evaluation/reference \
  --submission examples/combined/submission.json \
  --repository . \
  --output build/combined-request.json
```

Output must be a new file outside dataset, reference and submission directories.
It contains answer keys: keep it instructor-only. Separate references must never be
inside student input directories. Exit codes are 0 success, 2 invalid/input error.

The versioned request includes the unchanged booking adapter request, sorted impact
prediction/expected records, the public functional challenge, evidence and its
validation level. SHA-256 provenance covers submission, evidence, impact inputs,
public challenge, and (in the nested booking request) booking inputs. No student
command, URL, hook, model or external evaluator is invoked. Reported student test
results remain untrusted claims; output explicitly marks all grading as pending.

An external evaluator can consume the data without importing student code into its
controller:

```python
import json
request = json.load(open('build/combined-request.json', encoding='utf-8'))
assert request['contract_version'] == '1.0'
public_cases = request['functional_contract']  # data, never eval()/exec()
impact_pairs = request['impact_records']
# Pass only public fixture inputs and the pinned submission to a disposable worker.
# Compare returned observations in the trusted controller, then review process evidence.
```

## Independent evaluation criteria

| Track | Objective checks / review criteria |
| --- | --- |
| Functional change | Execute the pinned implementation against public post-change inputs plus protected variants; compare ordered events, truth, required attributes, exact timestamps and unaffected envelopes. Report each case and failure. |
| Regression | Run original simulator tests; compare complete default output to a trusted baseline for multiple seeds/counts; check failure, pending, success, duplicate delivery and both options together. Do not rely only on tests edited by the student. |
| Business impact | Report per-service confusion across affected/possible/unaffected, with definite-affected precision/recall, uncertainty errors and false positives. Measure case outcomes, not file edits or dependency fan-out alone. |
| Process | Independently inspect rationale against intent/spec, test relevance/results, reviewer independence, finding remediation or explicit risk acceptance, human decisions, limitations and reproduction instructions. Existence earns no correctness credit. |

For **definite affected** precision: TP = actual affected predicted affected; FP =
actual possible/unaffected predicted affected. Recall denominator includes every
actual affected service (possible/unaffected predictions are FN). Zero denominator
means `null` (not applicable), not automatic success. Report raw counts, per-case
and micro-aggregated metrics. Also publish the full three-class confusion matrix,
possible-as-affected overconfidence and affected-as-possible underconfidence.
Booking status/root-cause and booking impact keep their existing contract semantics.
Proposed rubric remains 35% correctness/regression, 30% observability/impact, 25%
SDLC quality, 10% reproduction/presentation, subject to bootcamp approval. No score
is inferred here from a student's self-reported `passed` field.

## Execution boundary

Public CI runs only synthetic public fixture checks with read-only repository
permissions, no deployment/model credentials and no protected grading data. Keep
PR validation on `pull_request`, never privileged `pull_request_target` executing
PR code. For assessment, `engineering-evals` must use hardened disposable workers
with no secrets, host mounts, privileged socket, or default network, with CPU,
memory, process, time and output limits. Do not mount answer keys in the worker;
compare observations outside it. Treat logs/results as untrusted data. Pin the
submission commit and evaluator version, retain input hashes, and destroy workers.
A subprocess alone, including a Docker default configuration, is not this boundary.

Use identical correctness and review criteria for paid-model, free-model and manual
workflows. No private prompts or key capture. Held-out cases and protected runner
configuration must remain exclusively in `engineering-evals`, never public PR CI.
