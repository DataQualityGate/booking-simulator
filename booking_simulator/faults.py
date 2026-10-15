"""Opt-in deterministic telemetry mutations, separate from business outcomes."""
import copy
import datetime as dt
import hashlib
import math

VERSION = "1.0"
FAULTS = ("missing_correlation", "late_delivery", "malformed_envelope")


def configuration(rates=None, late_seconds=120):
    """Normalize enabled rates, rejecting invalid values before writing output."""
    if not isinstance(late_seconds, int) or isinstance(late_seconds, bool) or not 1 <= late_seconds <= 86400:
        raise ValueError("late_seconds must be an integer between 1 and 86400")
    if rates is not None and not isinstance(rates, dict):
        raise ValueError("Fault rates must be a mapping")
    enabled = {}
    for name, rate in (rates or {}).items():
        if name not in FAULTS:
            raise ValueError(f"Unknown fault: {name}")
        if isinstance(rate, bool) or not isinstance(rate, (int, float)) or not math.isfinite(rate) or not 0 <= rate <= 1:
            raise ValueError(f"{name} rate must be finite and between 0 and 1")
        if rate:
            enabled[name] = float(rate)
    return {"version": VERSION, "rates": dict(sorted(enabled.items())), "late_seconds": late_seconds} if enabled else {}


def inject(events, seed, config):
    """Mutate logical events consistently across deliveries; return per-line originals.

    Selection uses a fault-specific hash, never the business generator RNG. All
    selected delivery copies share the same mutation, while keeping their times.
    """
    records = []
    for original in events:
        event = copy.deepcopy(original)
        applied = []
        for name, rate in config.get("rates", {}).items():
            digest = hashlib.sha256(f"fault:{VERSION}:{seed}:{name}:{event['event_id']}".encode()).digest()
            selected = int.from_bytes(digest[:8], "big") / 2**64 < rate
            if not selected:
                continue
            applied.append(name)
            if name == "missing_correlation":
                event.pop("trace_id", None)
            elif name == "late_delivery":
                observed = dt.datetime.fromisoformat(event["observed_at"].replace("Z", "+00:00"))
                event["observed_at"] = (observed + dt.timedelta(seconds=config["late_seconds"])).isoformat().replace("+00:00", "Z")
            elif name == "malformed_envelope":
                event["attributes"] = []
        records.append((event, applied, original))
    records.sort(key=lambda row: (row[0]["observed_at"], row[0]["event_id"]))
    mutations = [{"line": index, "event_id": event["event_id"],
                  "booking_id": original["booking_id"], "faults": applied,
                  "original": copy.deepcopy(original)}
                 for index, (event, applied, original) in enumerate(records, 1) if applied]
    return [row[0] for row in records], mutations
