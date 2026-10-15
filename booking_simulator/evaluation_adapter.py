"""Prepare a versioned, instructor-only handoff to an external evaluator."""
import argparse
import hashlib
import json
from pathlib import Path

from .predictions import VERSION as PREDICTION_VERSION, _parse, booking_ids_from_events, validate_predictions

CONTRACT_VERSION = "1.0"
DIMENSIONS = ("status", "root_cause_service", "affected_services")


def _read(path):
    """Read exact UTF-8 bytes for validation and reproducible provenance hashes."""
    data = path.read_bytes()
    return data.decode("utf-8"), hashlib.sha256(data).hexdigest()


def _event_path(dataset, manifest):
    """Keep manifest-controlled file paths inside the public dataset directory."""
    name = manifest.get("events_path")
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise ValueError("Manifest events_path must be a relative file path")
    path = (dataset / name).resolve()
    if not path.is_relative_to(dataset.resolve()):
        raise ValueError("Manifest events_path escapes dataset directory")
    return path


def _rows(text):
    """Parse nonblank JSONL records after prediction validation succeeds."""
    return [_parse(line) for line in text.splitlines() if line.strip()]


def prepare_evaluation(dataset, reference, predictions):
    """Validate inputs and join public predictions to separate instructor truth.

    The returned object contains answers. Do not send it to student code or
    untrusted PR jobs. No external package or grader is imported or executed.
    """
    dataset, reference, predictions = Path(dataset), Path(reference), Path(predictions)
    truth_path = (reference / "truth.jsonl").resolve()
    if truth_path.is_relative_to(dataset.resolve()):
        raise ValueError("Instructor reference must be outside the student dataset")
    manifest_text, manifest_hash = _read(dataset / "manifest.json")
    manifest = _parse(manifest_text)
    if not isinstance(manifest, dict) or manifest.get("schema_version") != "1.0":
        raise ValueError("Unsupported dataset manifest schema_version")
    dataset_id, count = manifest.get("dataset_id"), manifest.get("booking_count")
    if not isinstance(dataset_id, str) or not dataset_id.strip():
        raise ValueError("Manifest dataset_id must be a nonempty string")
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise ValueError("Manifest booking_count must be a positive integer")
    event_text, event_hash = _read(_event_path(dataset, manifest))
    ids = booking_ids_from_events(event_text)
    if len(ids) != count:
        raise ValueError("Manifest booking_count does not match event booking IDs")
    prediction_text, prediction_hash = _read(predictions)
    report = validate_predictions(prediction_text, booking_ids=ids)
    if not report["valid"]:
        raise ValueError("Invalid prediction submission: " + json.dumps(report["errors"], sort_keys=True))
    truth_text, truth_hash = _read(truth_path)
    expected = []
    for row in _rows(truth_text):
        if not isinstance(row, dict):
            raise ValueError("Reference rows must be objects")
        try:
            expected.append({"schema_version": PREDICTION_VERSION, "booking_id": row["booking_id"],
                             **{key: row[key] for key in DIMENSIONS}})
        except KeyError as error:
            raise ValueError(f"Missing reference field: {error.args[0]}") from error
    truth_report = validate_predictions("\n".join(json.dumps(row) for row in expected), booking_ids=ids)
    if not truth_report["valid"]:
        raise ValueError("Invalid instructor reference: " + json.dumps(truth_report["errors"], sort_keys=True))
    by_id = {row["booking_id"]: row for row in expected}
    records = []
    for row in sorted(_rows(prediction_text), key=lambda row: row["booking_id"]):
        record = {"booking_id": row["booking_id"]}
        for name, source in (("prediction", row), ("expected", by_id[row["booking_id"]])):
            record[name] = {key: sorted(source[key]) if key == "affected_services" else source[key]
                            for key in DIMENSIONS}
        records.append(record)
    return {
        "contract_version": CONTRACT_VERSION,
        "task": "booking_predictions",
        "prediction_schema_version": PREDICTION_VERSION,
        "dataset": {"dataset_id": dataset_id, "schema_version": manifest["schema_version"], "booking_count": count},
        "input_sha256": {"manifest": manifest_hash, "events": event_hash,
                         "predictions": prediction_hash, "truth": truth_hash},
        "records": records,
    }


def write_request(dataset, reference, predictions, output):
    """Write a validated request outside public inputs; never overwrite files."""
    dataset, reference, predictions, output = map(Path, (dataset, reference, predictions, output))
    destination = output.resolve()
    if destination.is_relative_to(dataset.resolve()):
        raise ValueError("Evaluation request contains answers and must stay outside dataset/")
    manifest = _parse((dataset / "manifest.json").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("Manifest must be an object")
    inputs = {predictions.resolve(), (reference / "truth.jsonl").resolve(),
              (dataset / "manifest.json").resolve(), _event_path(dataset, manifest)}
    if destination in inputs:
        raise ValueError("Output must not overwrite an input file")
    request = prepare_evaluation(dataset, reference, predictions)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(request, indent=2, sort_keys=True) + "\n")
    return request


def main():
    """Export a local handoff without executing student or evaluator code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        request = write_request(args.dataset, args.reference, args.predictions, args.output)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f"Prepared {len(request['records'])} instructor-only records in {args.output}")


if __name__ == "__main__":
    main()
