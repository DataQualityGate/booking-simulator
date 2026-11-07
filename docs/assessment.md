# Bootcamp assessment contract

## Public practice and protected grading

All incident IDs returned by `booking_simulator.incidents.exercises()`, all
challenge examples in `challenges/v1/`, and all fixtures under `examples/`
are **practice-only**. The public challenge IDs name the API assignment and
may be reused to identify that assignment. Its exact fixture cases, including
public input tuples and incident IDs, are excluded from scored held-out packs.
Public history and generated practice references are safe to read and reuse
for rehearsal. Public smoke checks do not contribute to a scored run.

Students receive API contracts, assigned incident observations and topology,
grading criteria and practice examples. Instructors retain unseen behavioral
inputs until execution, unseen impact observations until assignment, and all
protected expected answers, case packs and full scoring reports. Answers
remain outside student runtimes, public PRs, artifacts and logs. A private seed
alone is insufficient. Include independently designed impact variants and
test whether copying public answers or implementing only the sample cases
can pass. The isolation and fresh-student red-team checks in the private
evaluator are prerequisites for scored use.

## Behavior

Implement the assigned change in `booking_simulator.cli.generate`. An
instructor pins the baseline SHA, exact submitted SHA, evaluator version,
isolated Python image digest and held-out pack version. Each case invokes
`generate(seed, count, **options)` with a blinded JSON input. The candidate
returns the documented pair of event records and booking truth records.
The trusted grader checks those observed results against protected expected
outputs. Tests include edge cases and regressions with unchanged defaults.
Timeout, crash, invalid output and infrastructure failures have distinct
outcomes. Infrastructure failures invalidate the run. Public rehearsal uses
`python -m booking_simulator.smoke` and the documented challenge examples.

## Impact

Submit a JSONL file, with one [v1 record](../schemas/impact-prediction-v1.schema.json)
per assigned case. Use the provided IDs and the case's service universe.
Declare definite and possible impact separately. Unlisted services count as
unaffected. Extra IDs, duplicates, unknown services and overlapping labels
are rejected. A missing prediction counts as unanswered and cannot earn
credit for correctly excluding services.

Definite-impact precision and recall penalize false positives and missed
affected services. F1 combines both. The private report also tracks uncertain
and unaffected labels, including overconfidence (possible labeled definite)
and missed uncertainty. Root-cause explanations can be reviewed separately.
Feedback is aggregate and excludes expected labels and private case diagnostics.

## SDLC evidence

Use the [evidence contract](sdlc-evidence.md). Reviewers verify pinned artifact
references and use independent CI records for execution claims. The scorecard
separates completeness, traceability, execution credibility, review quality
and confidence. Reviewers check how tests cover the requirement, what defects
review found, how findings were resolved and who accepted remaining risks.
Weak or unverified evidence cannot receive full credit. An independent
instructor can adjudicate disputed judgments. Evidence may use any tool and
should exclude credentials, private prompts and raw sessions.
