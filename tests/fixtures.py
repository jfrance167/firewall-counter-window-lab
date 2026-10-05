"""Synthetic fixtures, never actual firewall records."""
import json


def envelope():
    return {"schema_version": 1, "source_id": "synthetic-lab", "epoch_id": "asserted-epoch-1",
            "captured_at": "2026-10-05T00:00:00Z", "chains": [
                {"name": "INPUT", "policy": "DROP", "rules": [
                    {"position": 1, "rule_text": "-s 192.0.2.0/24 -j ACCEPT", "packets": 10, "bytes": 1000},
                    {"position": 2, "rule_text": "-j DROP", "packets": 0, "bytes": 0}]}]}


def encoded(raw):
    return json.dumps(raw).encode("utf-8")
