"""Regenerate fixed synthetic sample artifacts; --check verifies exact bytes.

Usage: python scripts/demo_reports.py [--check]
No user-supplied paths. Write mode overwrites only the fixed documented samples.
CLI report creation remains exclusive. Never use real firewall records here.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from counter_window.compare import compare
from counter_window.report import render
from counter_window.snapshot import parse_snapshot


def artifacts() -> dict[str, str]:
    before = {"schema_version": 1, "source_id": "synthetic-lab", "epoch_id": "asserted-epoch-1",
              "captured_at": "2026-10-05T00:00:00Z", "chains": [
                  {"name": "INPUT", "policy": "DROP", "rules": [
                      {"position": 1, "rule_text": "-s 192.0.2.0/24 -j ACCEPT", "packets": 10, "bytes": 1000},
                      {"position": 2, "rule_text": "-s 198.51.100.0/24 -j ACCEPT", "packets": 0, "bytes": 0},
                      {"position": 3, "rule_text": "-j DROP", "packets": 500, "bytes": 50000}]}]}
    after = deepcopy(before)
    after["captured_at"] = "2026-10-05T00:00:10Z"
    after["chains"][0]["rules"][0].update(packets=30, bytes=3000)
    after["chains"][0]["rules"][2].update(packets=3, bytes=300)
    encode = lambda value: json.dumps(value, indent=2, ensure_ascii=True) + "\n"
    old = parse_snapshot(encode(before).encode())
    new = parse_snapshot(encode(after).encode())
    observation = compare(old, new)
    conditional = compare(old, new, assume_continuity=True)
    return {"before.json": encode(before), "after.json": encode(after),
            "observations.json": render(observation, "json"),
            "observations.txt": render(observation, "text"),
            "conditional.json": render(conditional, "json"),
            "counter-window.html": render(conditional, "html")}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for name, content in artifacts().items():
        path = ROOT / "samples" / name
        if args.check:
            if not path.is_file() or path.read_bytes() != content.encode("utf-8"):
                print(f"sample mismatch: {name}")
                return 1
        else:
            path.write_bytes(content.encode("utf-8"))
    print("six synthetic samples verified" if args.check else "six synthetic samples generated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
