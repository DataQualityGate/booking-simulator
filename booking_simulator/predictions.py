"""Validate public booking prediction JSONL without access to answer keys."""
import argparse
import json
from pathlib import Path
import re

VERSION = "1.0"
SERVICES = ("booking", "payment", "supplier", "notification")
STATUSES = ("confirmed", "failed", "pending")
FIELDS = {"schema_version", "booking_id", "status", "root_cause_service", "affected_services"}
BOOKING_ID = re.compile(r"BOOK-[0-9]{6,}\Z")


def _object(pairs):
    """Reject duplicate JSON keys instead of silently accepting the last value."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _constant(value):
    """Reject nonstandard JSON numbers such as NaN and Infinity."""
    raise ValueError(f"Nonstandard JSON constant: {value}")


def _parse(line):
    """Read strict JSON with unique object keys."""
    try:
        return json.loads(line, object_pairs_hook=_object, parse_constant=_constant)
    except RecursionError as error:
        raise ValueError("JSON nesting exceeds the parser limit") from error


def _row_errors(row):
    """Check one prediction's shape and vocabulary, not its correctness."""
    if not isinstance(row, dict):
        return ["Prediction must be a JSON object"]
    errors = []
    missing, extra = FIELDS - row.keys(), row.keys() - FIELDS
    if missing:
        errors.append("Missing fields: " + ", ".join(sorted(missing)))
    if extra:
        errors.append("Unknown fields: " + ", ".join(sorted(extra)))
    if missing:
        return errors
    if row["schema_version"] != VERSION:
        errors.append("Unsupported schema_version; expected string 1.0")
    if not isinstance(row["booking_id"], str) or not BOOKING_ID.fullmatch(row["booking_id"]):
        errors.append("booking_id must match BOOK- followed by at least six ASCII digits")
    if row["status"] not in STATUSES:
        errors.append("status must be confirmed, failed or pending")
    root = row["root_cause_service"]
    if root is not None and root not in SERVICES:
        errors.append("root_cause_service must be a known service or null")
    affected = row["affected_services"]
    if not isinstance(affected, list) or not all(isinstance(s, str) and s in SERVICES for s in affected):
        errors.append("affected_services must be an array of known service names")
    elif len(affected) != len(set(affected)):
        errors.append("affected_services must not contain duplicates")
    return errors


def validate_predictions(text, *, booking_ids=None):
    """Return deterministic diagnostics; optional booking IDs enforce exact coverage.

    Blank lines are ignored. Physical line numbers are preserved in diagnostics.
    This validates structure only and never reads reference truth or grades a row.
    """
    errors, seen = [], set()
    row_count = 0
    expected = set(booking_ids) if booking_ids is not None else None
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        row_count += 1
        try:
            row = _parse(line)
        except ValueError as error:
            errors.append({"line": number, "code": "invalid_json", "message": str(error)})
            continue
        row_errors = _row_errors(row)
        for message in row_errors:
            errors.append({"line": number, "code": "invalid_prediction", "message": message})
        booking_id = row.get("booking_id") if isinstance(row, dict) else None
        if not isinstance(booking_id, str) or not BOOKING_ID.fullmatch(booking_id):
            continue
        if booking_id in seen:
            errors.append({"line": number, "code": "duplicate_booking", "message": booking_id})
        seen.add(booking_id)
        if expected is not None and booking_id not in expected:
            errors.append({"line": number, "code": "unknown_booking", "message": booking_id})
    if row_count == 0:
        errors.append({"line": None, "code": "empty_submission", "message": "At least one prediction is required"})
    if expected is not None:
        for booking_id in sorted(expected - seen):
            errors.append({"line": None, "code": "missing_booking", "message": booking_id})
    return {"schema_version": VERSION, "valid": not errors, "row_count": row_count, "errors": errors}


def booking_ids_from_events(text):
    """Collect IDs from student events; repeated deliveries/bookings are expected."""
    ids = set()
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = _parse(line)
        except ValueError as error:
            raise ValueError(f"Invalid events JSON on line {number}: {error}") from error
        booking_id = row.get("booking_id") if isinstance(row, dict) else None
        if not isinstance(booking_id, str) or not BOOKING_ID.fullmatch(booking_id):
            raise ValueError(f"Invalid events booking_id on line {number}")
        ids.add(booking_id)
    if not ids:
        raise ValueError("Events input must contain booking IDs")
    return ids


def main():
    """Print a validation report; exit 0 for valid, 1 for invalid, 2 for input errors."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--events", type=Path, help="Check exact coverage using student events.jsonl")
    args = parser.parse_args()
    try:
        expected = booking_ids_from_events(args.events.read_text(encoding="utf-8")) if args.events else None
        report = validate_predictions(args.predictions.read_text(encoding="utf-8"), booking_ids=expected)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["valid"] else 1)


if __name__ == "__main__":
    main()
