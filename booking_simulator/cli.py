"""Generate deterministic synthetic booking events and separated ground truth."""
import argparse
import datetime as dt
import json
import hashlib
import secrets
import random
from pathlib import Path

SCHEMA_VERSION = "1.0"
BASE = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
SERVICES = ["booking", "payment", "supplier", "notification"]
TOPOLOGY = {
    "schema_version": SCHEMA_VERSION,
    "services": SERVICES,
    "dependencies": [
        {"from": "booking", "to": "payment"},
        {"from": "booking", "to": "supplier"},
        {"from": "booking", "to": "notification"},
    ],
    "business_process": "hotel_booking",
}

def canonical(obj):
    """Serialize a record consistently for reproducible output."""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def generate(seed: int, count: int):
    """Generate ordered events and instructor answers for a fixed seed."""
    if count < 1:
        raise ValueError("count must be positive")
    rng = random.Random(seed)
    events, ground_truth = [], []
    for n in range(count):
        booking = f"BOOK-{n+1:06d}"
        trace = hashlib.sha256(f"trace:{seed}:{n}".encode()).hexdigest()[:32]
        outcome = rng.choices(
            ["success", "payment_failed", "supplier_timeout", "message_delay"],
            [65, 12, 13, 10],
        )[0]
        start = n * 60
        steps = [("booking", "BookingRequested", 0, 0), ("payment", "PaymentAuthorized", 2, 3)]
        if outcome == "payment_failed":
            steps = [
                ("booking", "BookingRequested", 0, 0),
                ("payment", "PaymentDeclined", 2, 3),
                ("booking", "BookingFailed", 4, 5),
            ]
            status, root = "failed", "payment"
        elif outcome == "supplier_timeout":
            steps += [
                ("supplier", "ReservationRequested", 4, 5),
                ("supplier", "SupplierTimeout", 15, 16),
                ("booking", "BookingPending", 16, 17),
            ]
            status, root = "pending", "supplier"
        elif outcome == "message_delay":
            steps += [
                ("supplier", "ReservationRequested", 4, 5),
                ("supplier", "SupplierConfirmed", 7, 35),
                ("booking", "BookingConfirmed", 36, 37),
                ("notification", "NotificationSent", 39, 41),
            ]
            status, root = "confirmed", None
        else:
            steps += [
                ("supplier", "ReservationRequested", 4, 5),
                ("supplier", "SupplierConfirmed", 7, 8),
                ("booking", "BookingConfirmed", 10, 11),
                ("notification", "NotificationSent", 12, 13),
            ]
            status, root = "confirmed", None
        for idx, (service, kind, occurred, lag) in enumerate(steps):
            event = {
                "schema_version": SCHEMA_VERSION,
                "event_id": f"{booking}-{idx:02d}",
                "booking_id": booking,
                "trace_id": trace,
                "service": service,
                "event_type": kind,
                "occurred_at": (BASE + dt.timedelta(seconds=start + occurred)).isoformat().replace("+00:00", "Z"),
                "observed_at": (BASE + dt.timedelta(seconds=start + lag)).isoformat().replace("+00:00", "Z"),
                "attributes": {"synthetic": True, "region": rng.choice(["north", "south", "east"])},
            }
            events.append(event)
            if outcome == "message_delay" and kind == "SupplierConfirmed":
                duplicate = dict(event)
                duplicate["observed_at"] = (BASE + dt.timedelta(seconds=start + 38)).isoformat().replace("+00:00", "Z")
                events.append(duplicate)
        ground_truth.append({
            "booking_id": booking,
            "scenario": outcome,
            "status": status,
            "root_cause_service": root,
            "affected_services": (
                ["booking"] if root is None else
                ["payment", "booking"] if root == "payment" else
                ["supplier", "booking", "notification"]
            ),
        })
    events.sort(key=lambda e: (e["observed_at"], e["event_id"]))
    return events, ground_truth

def save(output: Path, seed: int, count: int, *, incidents: bool = False, fault_rates=None, late_seconds=120):
    """Save student inputs separately from answers and reproduction metadata."""
    from .faults import configuration, inject
    fault_config = configuration(fault_rates, late_seconds)
    events, truth = generate(seed, count)
    mutations = []
    if fault_config:
        events, mutations = inject(events, seed, fault_config)
    incident_metadata = {}
    identity_suffix = ""
    if incidents:
        from .incidents import VERSION, TOPOLOGY as IMPACT_TOPOLOGY, exercises, save_exercises
        cases, _ = exercises()
        identity_suffix = canonical({"suite_version": VERSION, "cases": cases,
                                     "topology": IMPACT_TOPOLOGY})
        incident_metadata = {"incident_suite_version": VERSION,
                             "incidents_path": "incidents.jsonl",
                             "impact_topology_path": "impact-topology.json"}
    if fault_config:
        identity_suffix += canonical(fault_config)
    dataset, reference = output / "dataset", output / "reference"
    dataset.mkdir(parents=True, exist_ok=True)
    reference.mkdir(parents=True, exist_ok=True)
    (dataset / "events.jsonl").write_text(
        "".join(canonical(e) + "\n" for e in events), encoding="utf-8"
    )
    (dataset / "topology.json").write_text(json.dumps(TOPOLOGY, indent=2) + "\n", encoding="utf-8")
    (dataset / "manifest.json").write_text(json.dumps({
        "schema_version": SCHEMA_VERSION,
        "dataset_id": "booking-v1-" + hashlib.sha256(
            ("".join(canonical(e) + "\n" for e in events) + identity_suffix).encode("utf-8")
        ).hexdigest()[:16],
        "booking_count": count,
        "events_path": "events.jsonl",
        "topology_path": "topology.json",
        **incident_metadata,
        **({"data_quality": fault_config} if fault_config else {}),
    }, indent=2) + "\n", encoding="utf-8")
    (reference / "truth.jsonl").write_text(
        "".join(canonical(r) + "\n" for r in truth), encoding="utf-8"
    )
    (reference / "generation.json").write_text(json.dumps({
        "schema_version": SCHEMA_VERSION,
        "seed": seed,
        "booking_count": count,
        "incidents": incidents,
        **({"data_quality": fault_config} if fault_config else {}),
        **({"incident_suite_version": incident_metadata["incident_suite_version"]} if incidents else {}),
    }, indent=2) + "\n", encoding="utf-8")
    fault_truth = reference / "data-quality-truth.jsonl"
    if fault_config:
        fault_truth.write_text("".join(canonical(row) + "\n" for row in mutations), encoding="utf-8")
    else:
        fault_truth.unlink(missing_ok=True)
    if incidents:
        save_exercises(dataset, reference)
    else:
        for path in (dataset / "incidents.jsonl", dataset / "impact-topology.json",
                     reference / "impact-truth.jsonl"):
            path.unlink(missing_ok=True)
    return len(events)

def main():
    """Generate a dataset, choosing a random seed unless one is supplied."""
    parser = argparse.ArgumentParser(description="Generate synthetic booking telemetry (stdlib only)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Reproduction seed; omitted selects a random seed")
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--output", type=Path, default=Path("build"))
    parser.add_argument("--incidents", action="store_true", help="Include independent incident and impact exercises")
    parser.add_argument("--missing-correlation-rate", type=float, default=0)
    parser.add_argument("--late-delivery-rate", type=float, default=0)
    parser.add_argument("--malformed-envelope-rate", type=float, default=0)
    parser.add_argument("--late-seconds", type=int, default=120)
    args = parser.parse_args()
    seed = args.seed if args.seed is not None else secrets.randbits(128)
    try:
        number = save(args.output, seed, args.count, incidents=args.incidents,
                      fault_rates={"missing_correlation": args.missing_correlation_rate,
                                   "late_delivery": args.late_delivery_rate,
                                   "malformed_envelope": args.malformed_envelope_rate},
                      late_seconds=args.late_seconds)
    except ValueError as error:
        parser.error(str(error))
    print(f"Generated {args.count} bookings and {number} events in {args.output}")
    print("Share dataset/; keep reference/ for evaluation.")
