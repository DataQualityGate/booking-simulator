# SDLC change challenges v1

The public catalog in `challenges/v1/` adds two independent opt-in change requests.
It does not change the generator or ship the student solution. A student implements
the specified keyword option in `booking_simulator.cli.generate` in their fork.
The existing CLI, incidents, data-quality faults and prediction contracts remain supported.

```bash
python -m booking_simulator.challenges
python -m booking_simulator.challenges --challenge supplier-recovery-v1
python -m booking_simulator.challenges --challenge confirmation-context-v1 --output challenge.json
python -m unittest discover -s tests -v
```

Exports exclusively create a new file, never overwrite existing work. Execute from
an ordinary repository checkout; no installed package data or network is needed.
Each immutable ID identifies a manifest revision. Incompatible changes require a
new ID/directory version. Manifests contain baseline, requested API and behavior,
public post-change acceptance fixtures, regression fixtures and impact expectations.

The fixture contract specifies seeds, counts, keyword arguments, ordered event
types, exact truth rows and optional event attribute subsets. Single-booking seeds
0/1/2/19 cover timeout, success, delayed duplicate delivery and payment decline.
Students must also test multiple bookings, both options together, unchanged default
output, unaffected envelopes, ordering, duplicate semantics and timestamp offsets.
Fixtures are examples, not exhaustive correctness tests or secret grading answers.

`supplier-recovery-v1` changes a transient timeout from pending to confirmed after
an opt-in recovery. This indirectly triggers notification and analytics; payment
stays unchanged and audit remains uncertain. `confirmation-context-v1` adds optional
confirmation metadata without breaking tolerant consumers. Impact sets describe
**business outcome changes** versus baseline, not which source files were edited;
this differs from per-booking `affected_services` in generator truth.

Use intent/spec, a plan, tests, review, revisions and a human decision to record
how the change was developed. Any editor or model is acceptable, including a
workflow without a paid model. No private prompts, credentials or company systems
are required. Engineering evidence validation and the combined evaluator handoff
are separate extensions. Protected variants belong only in `engineering-evals`.

This follows the combined bootcamp plan's boundaries: the simulator owns public
synthetic exercises; the independent evaluator owns protected assessment and
isolation of untrusted submissions.
