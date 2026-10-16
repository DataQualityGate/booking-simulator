"""Inspect/export public change requests; never implement a student solution."""
import argparse
import copy
import json
from pathlib import Path

from .predictions import _parse

VERSION = "1.0"
CATALOG = Path(__file__).resolve().parent.parent / "challenges" / "v1"


def challenges():
    """Load fresh manifests in stable order; IDs include the contract revision."""
    return [_parse(path.read_text(encoding="utf-8")) for path in sorted(CATALOG.glob("*.json"))]


def get_challenge(challenge_id):
    """Resolve one immutable ID without exposing shared mutable state."""
    for challenge in challenges():
        if challenge["challenge_id"] == challenge_id:
            return copy.deepcopy(challenge)
    raise ValueError(f"Unknown challenge: {challenge_id}")


def main():
    """List the catalog or exclusively export a selected public manifest."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--challenge", help="Show one versioned challenge; omitted lists IDs")
    parser.add_argument("--output", type=Path, help="Export one manifest to a new file")
    args = parser.parse_args()
    if args.output and not args.challenge:
        parser.error("--output requires --challenge")
    try:
        value = get_challenge(args.challenge) if args.challenge else [c["challenge_id"] for c in challenges()]
        encoded = json.dumps(value, indent=2, sort_keys=True) + "\n"
        if args.output:
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(encoded)
        else:
            print(encoded, end="")
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
