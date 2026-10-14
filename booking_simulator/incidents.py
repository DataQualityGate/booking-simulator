"""Synthetic incident exercises and scoring; no impact inference implementation."""
import json

VERSION = "1.0"
SERVICES = ["booking", "payment", "supplier", "notification", "analytics", "audit"]
TOPOLOGY = {
    "schema_version": VERSION,
    "services": SERVICES,
    "dependency_direction": "consumer_to_provider",
    "dependencies": [
        {"from": "booking", "to": "payment", "contract": "authorize.v1", "mode": "required"},
        {"from": "booking", "to": "supplier", "contract": "reserve.v1", "mode": "required"},
        {"from": "notification", "to": "booking", "contract": "BookingConfirmed.v1", "mode": "required"},
        {"from": "analytics", "to": "booking", "contract": "BookingConfirmed.v1", "mode": "optional"},
        {"from": "audit", "to": "booking", "contract": "BookingConfirmed.v1", "mode": "unknown"},
    ],
}


def exercises():
    """Return independent cases and explicit, curated service-level answer keys."""
    cases, answers = [], []
    definitions = [
        ("payment-outage", "service_failure", "payment", None,
         "Payment authorization is unavailable during the observation window.",
         {"payment": "unavailable", "booking": "failed", "notification": "not_triggered"},
         ["payment", "booking", "notification"], ["audit"]),
        ("supplier-outage", "service_failure", "supplier", None,
         "Supplier reservation requests time out; bookings remain pending.",
         {"supplier": "timeout", "booking": "pending", "notification": "not_triggered"},
         ["supplier", "booking", "notification"], ["audit"]),
        ("notification-outage", "service_failure", "notification", None,
         "Notification delivery is unavailable; booking confirmations still succeed.",
         {"notification": "unavailable", "booking": "confirmed"},
         ["notification"], []),
        ("payment-api-break", "api_change", "payment", "authorize.v1",
         "authorize.v1 is removed in favor of authorize.v2; booking still calls v1.",
         {"payment": "v2_available", "booking": "http_404", "notification": "not_triggered"},
         ["booking", "notification"], ["audit"]),
        ("confirmation-schema-break", "schema_change", "booking", "BookingConfirmed.v1",
         "BookingConfirmed replaces booking_id with reservation_id. Notification requires booking_id; analytics ignores it.",
         {"booking": "confirmed", "notification": "schema_rejected", "analytics": "processed"},
         ["notification"], ["audit"]),
        ("confirmation-schema-add", "schema_change", "booking", "BookingConfirmed.v1",
         "BookingConfirmed adds an optional field; notification and analytics accept unknown fields.",
         {"booking": "confirmed", "notification": "sent", "analytics": "processed"},
         [], ["audit"]),
    ]
    for case_id, kind, source, contract, description, observations, affected, possible in definitions:
        cases.append({
            "case_id": case_id, "kind": kind, "source_service": source,
            "contract": contract, "description": description,
            "observations": [{"service": service, "signal": signal}
                             for service, signal in observations.items()],
            "context": "Independent synthetic window with new bookings; analytics has a tested fallback. Audit telemetry is unavailable.",
        })
        answers.append({
            "case_id": case_id,
            "affected_services": sorted(affected),
            "possibly_affected_services": sorted(possible),
            "unaffected_services": sorted(set(SERVICES) - set(affected) - set(possible)),
        })
    return cases, answers


def save_exercises(dataset, reference):
    """Write observable exercises separately from instructor classifications."""
    cases, answers = exercises()
    (dataset / "impact-topology.json").write_text(json.dumps(TOPOLOGY, indent=2) + "\n", encoding="utf-8")
    (dataset / "incidents.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in cases), encoding="utf-8")
    (reference / "impact-truth.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in answers), encoding="utf-8")


def _index(rows, name):
    indexed = {}
    for row in rows:
        case_id = row["case_id"]
        if case_id in indexed:
            raise ValueError(f"Duplicate {name} case: {case_id}")
        indexed[case_id] = row
    return indexed


def _labels(row, universe, *, reference=False):
    fields = ("affected_services", "possibly_affected_services")
    if reference:
        fields += ("unaffected_services",)
    for field in fields:
        values = row[field]
        if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
            raise ValueError(f"{field} must be a list of service names")
        if len(values) != len(set(values)):
            raise ValueError(f"Duplicate service in {field}")
    affected = set(row["affected_services"])
    possible = set(row["possibly_affected_services"])
    if affected & possible or (affected | possible) - universe:
        raise ValueError("Impact sets must be disjoint and contain only known services")
    if reference:
        unaffected = set(row["unaffected_services"])
        if unaffected & (affected | possible) or affected | possible | unaffected != universe:
            raise ValueError("Reference impact sets must partition all known services")
    return {service: "affected" if service in affected else
            "possible" if service in possible else "unaffected" for service in universe}


def evaluate(predictions, truth):
    """Score exact classifications, including overconfident and speculative positives.

    Missing cases are empty predictions; unknown/duplicate cases are errors.
    No topology traversal or student solution is provided here.
    """
    expected = _index(truth, "reference")
    submitted = _index(predictions, "prediction")
    if not expected:
        raise ValueError("Reference cases must not be empty")
    if submitted.keys() - expected.keys():
        raise ValueError("Unknown prediction case")
    confusion = {actual: {predicted: 0 for predicted in ("affected", "possible", "unaffected")}
                 for actual in ("affected", "possible", "unaffected")}
    for case_id, answer in expected.items():
        universe = set(SERVICES)
        actual = _labels(answer, universe, reference=True)
        predicted = _labels(submitted.get(case_id, {"affected_services": [], "possibly_affected_services": []}), universe)
        for service in universe:
            confusion[actual[service]][predicted[service]] += 1
    return {
        "confusion_matrix": confusion,
        "correct": sum(confusion[label][label] for label in confusion),
        "total": sum(sum(row.values()) for row in confusion.values()),
        "false_positives": confusion["unaffected"]["affected"] + confusion["unaffected"]["possible"],
        "false_negatives": confusion["affected"]["unaffected"] + confusion["possible"]["unaffected"],
        "overconfident": confusion["possible"]["affected"],
        "underconfident": confusion["affected"]["possible"],
    }


def main():
    """Evaluate a student's JSONL submission against instructor-only truth."""
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--truth", type=Path, required=True)
    args = parser.parse_args()
    try:
        predictions = [json.loads(line) for line in args.predictions.read_text(encoding="utf-8").splitlines() if line.strip()]
        truth = [json.loads(line) for line in args.truth.read_text(encoding="utf-8").splitlines() if line.strip()]
        result = evaluate(predictions, truth)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
