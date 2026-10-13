# Intent: Open-source Booking Simulator

## Why
Create a small, reusable engineering laboratory for distributed business process observability and impact analysis. Enable independent student teams to reason over synthetic events with measurable outcomes. Reuse the lab after the bootcamp for architecture and evaluation experiments.

## Principles
- Fully open source, no corporate credentials or private data.
- Reproducibility first: a seed and generator version determine output.
- Domain-level semantics, not just technical traces.
- Keep the simulator useful without a UI, Kafka, Kubernetes or hosted services.
- Separate task input from the answer key.
- Validate contracts and scenarios in automated tests.
- Do not build student solutions inside the simulator.

## MVP
Generate a hotel-booking process with booking, payment, supplier, and notification events. Support success, payment rejection, supplier timeout, delayed and duplicate delivery. Output JSONL, a service topology, manifest, and a separated reference truth dataset.

## Definition of done
- `python -m booking_simulator --seed 42 --count 1000` generates data.
- Repeated runs with identical seed and count produce identical files.
- `python -m unittest discover -s tests -v` succeeds.
- Synthetic events can be parsed without external services.
- Documentation clearly differentiates observable input from reference outcomes.

## Constraints
Do not require ETG infrastructure, external paid services, Python packages, or distributed runtimes for the core MVP. No real customer or transaction data.

## Future
Streaming transports, configurable fault injection, richer event correlation, a separate evaluation system, impact scenarios and hidden tests.
