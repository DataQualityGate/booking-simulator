# SDLC evidence v1

Submit `sdlc-evidence.json` following
[`schemas/sdlc-evidence-v1.schema.json`](../schemas/sdlc-evidence-v1.schema.json).
The closed schema rejects unknown fields. Local CLI validation uses only stdlib,
strict JSON (no duplicate keys/NaN), the bundled schema, cross-reference checks and
optional read-only Git object inspection. It does not run any submitted command.

```bash
python -m booking_simulator.evidence --evidence examples/evidence/valid.json
python -m booking_simulator.evidence --evidence examples/evidence/valid.json --repository .
# Negative examples deliberately exit 1:
python -m booking_simulator.evidence --evidence examples/evidence/missing.json
python -m booking_simulator.evidence --evidence examples/evidence/invalid.json
```

Exit codes: 0 valid, 1 invalid, 2 input/read errors. The public valid example points
to a real baseline commit and uses `not_run`: it is structurally valid evidence,
not a claim that a challenge has been implemented or reviewed successfully.

Required fields:

| Field | Meaning |
| --- | --- |
| schema_version | String `1.0` |
| challenge_id | An immutable ID from the public challenge catalog |
| commit_sha | Full lowercase 40/64 hexadecimal Git commit ID, never a moving branch |
| rationale | Engineering rationale for the change |
| intent, spec | Artifact references |
| tests | Nonempty list of unique IDs, command, passed/failed/not_run, artifact |
| reviews | Nonempty list of unique IDs, reviewer label, artifact, findings |
| human_decisions | Nonempty list of unique IDs, approve/revise/accept_risk, rationale, finding_ids |
| limitations | Explicit list, possibly empty |

Each finding has a globally unique ID, severity (info/minor/major/critical), status
(open/fixed/accepted) and rationale. Decision finding IDs must resolve; empty lists
are allowed for decisions unrelated to a specific finding. Presence checks do not
infer independence, truth of reported results, remediation or approval quality.

References are repository-relative POSIX file paths or HTTPS links without embedded
credentials or query strings. Paths must not traverse parents. With `--repository`,
the commit must exist locally and local artifacts must be blobs at **that commit**;
working-tree files cannot satisfy the check. Remote links are never fetched and
remain unverified. Without that option, only structure/reference syntax is checked.
Reports expose the verification level and always say correctness is not demonstrated.
Schema validation by external JSON Schema engines covers structure; the CLI adds
reference safety, unique IDs, referential integrity and optional Git existence checks.

Do not capture prompts, chat history, API keys, tokens, private URLs or personal
reviewer details. Use a role/pseudonym. Unknown fields are rejected, but free text
cannot be reliably secret-scanned: redact it before submission. Reports avoid
echoing rejected JSON values; no telemetry or remote calls are made.

Assess decisions, reproducible tests and independent review using the same rubric
whether the team used free tools, commercial models or manual engineering. Model
choice, token consumption, agent count and prompt length earn no points. An artifact
existing or a student reporting `passed` proves neither code correctness nor review
quality: external execution and human process review remain separate criteria.
