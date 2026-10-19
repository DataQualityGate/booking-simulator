# Contributing

This project is a public educational sandbox. Contributions are welcome via forks and pull requests.

1. Open or choose an issue.
2. Create a focused branch in your fork.
3. Run `python -m unittest discover -s tests -v`.
4. Open a PR describing the change and showing reproducible test results.

Do not submit real booking data, company credentials, internal architecture, secrets, or private evaluation answer keys.

Changes to dataset schemas must remain versioned and compatible or document a breaking version bump. Evaluation fixtures should use synthetic data.

Bootcamp participants: follow the [student guide](docs/student-guide.md) for the
assignment, local commands, expected deliverables and fork/PR workflow. Read
[sandbox security](docs/sandbox-security.md) before running contributor code or
configuring assessment CI.
