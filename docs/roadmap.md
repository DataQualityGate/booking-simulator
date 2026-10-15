# Roadmap

MVP completed: deterministic booking event generation, four scenarios, topology, separated ground truth, tests and basic GitHub CI.

## Next
1. Public booking prediction contract v1.0 and local format validator implemented (Issue #2).
2. Add data quality mutations: missing identifiers, out-of-order ingestion, malformed events.
3. Add configurable incident scenarios and their reference outcomes.
4. Provide a local evaluation adapter consuming prediction JSONL.
5. Add optional HTTP/event-stream transport without requiring a cloud environment.

## Later
- Event schemas and versioning
- OpenTelemetry and infrastructure-free local observability integration
- Multiple business processes and richer impact graphs
- Student onboarding and reproducible grading protocol

Avoid coupling the simulator to a specific AI framework, LLM provider, ETG platform, or grading vendor.
