# Sandbox and assessment security

## Trust model

Student forks, PR branches, test files, dependencies, build scripts and generated
artifacts are **untrusted executable input**. A test can run arbitrary Python,
read environment/files, make network requests or consume runner resources. A
passing test, code review or model output does not change that trust boundary.

Threats include credential exfiltration, reading hidden answers, poisoned output
artifacts/caches, escaping a weak sandbox, resource exhaustion and using a known
public generator/seed to reconstruct a benchmark. The simulator and validator
are not sandbox implementations. They do not make arbitrary code safe to run.

## Public pull-request CI

The repository uses GitHub-hosted disposable runners with a five-minute job
limit, read-only `contents` permissions and `persist-credentials: false` on
checkout. The workflow runs only public tests and synthetic fixtures.

- Never provide provider keys, company credentials, personal tokens, hidden
  datasets or answer keys to a PR job. GitHub still supplies job metadata and a
  scoped `GITHUB_TOKEN`; keep permissions minimal and do not persist it in Git.
- Do not use `pull_request_target` to check out and execute a contributor's head
  revision. Do not promote PR artifacts or caches into a privileged job without
  treating their contents as attacker-controlled input.
- Do not use self-hosted production runners or hosts with internal network
  access for these PRs. Review workflow/dependency changes as code-execution
  changes, not just text edits.
- Fork workflows may require a maintainer to approve execution in GitHub. That
  is GitHub's execution gate, not evidence that the code is safe. Public CI
  results are development feedback, not hidden assessment results.

These settings reduce exposure; they are not proof against every runner or
supply-chain vulnerability. Before running a fork locally, use a disposable
workspace without credentials or internal access. A virtual environment alone
is a package environment, not an isolation boundary.

## Hidden evaluation: three separate stages

1. **Untrusted execution:** run the student's code in an isolated disposable
   runtime. Mount only the assigned **student dataset**, not `reference/` or the
   prepared evaluator request. Disable network egress and avoid host sockets,
   home-directory mounts and cloud metadata access. Enforce CPU, memory, disk,
   process and time limits at the runtime boundary. Pin the code revision and
   public input hashes.
2. **Output transfer:** terminate the student's processes before grading. Copy
   bounded plain JSONL output as data, not a script, archive or executable.
   Reject links and unexpected file types/paths; validate record shape and ID
   coverage in a clean trusted process. Bound file sizes and record counts in
   the assessment runner before parsing.
3. **Trusted grading:** only now load instructor references and run the trusted
   evaluator. The local handoff from Issue #5 contains expected answers and is
   instructor-only. Do not return it to the student runtime or expose it in
   logs, downloadable CI artifacts or PR comments. Release only the agreed
   score report and feedback.

This repository documents the required boundary; it does **not** provision or
claim to provide the isolation runtime. Containers need their own enforced
isolation/network/resource policies; merely putting code in a container is not
the complete assessment system.

## Public generator versus hidden benchmark

All scenario definitions, examples and fixtures in this repository are public.
A fixed seed is convenient for development. Keeping a seed secret does not make
a public deterministic generator a secure hidden test set: outputs, IDs or a
small seed space can reveal it, and students can inspect generator logic.

For an assessment, the instructor must define independently maintained private
cases or a controlled evaluation protocol, protect references, test against
leakage and separate private scoring infrastructure from public PR CI. Do not
claim that high scores on the public fixtures demonstrate generalization.
Dataset IDs and SHA-256 input hashes support reproduction; they do not establish
answer authenticity or prevent a student from memorizing public cases.

## Instructor run checklist

- Assign a precise task/track and prediction contract version; record code
  revision, dataset ID and input hashes. Distribute only `dataset/`.
- Run student code with the untrusted-execution boundary above. Verify that no
  reference files, credentials or private network routes are available there.
- Collect bounded prediction output, stop execution, validate, and grade in the
  trusted stage. Keep the original dataset/reference pair together; matching
  booking IDs alone do not prove that the references belong to that seed.
- Retain reproducible results with an appropriate private retention policy.
  Share public synthetic examples freely; do not publish hidden inputs or
  expected answers as troubleshooting attachments.

Report repository security concerns privately through the maintainer contact
available on the GitHub repository. Do not post credentials or hidden answers
in an issue. Revoke any exposed credential through its provider before sharing
redacted details.
