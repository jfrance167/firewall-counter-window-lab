"""Whole-chain identity and two-sample observations, without traffic inference."""

from collections import Counter
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from .snapshot import Chain, InputError, Snapshot

LIMITATION = (
    "Source and epoch are operator assertions. Matching epochs and nondecreasing "
    "counters never prove continuity: hidden resets may occur. Zero observed change "
    "does not prove unreachability or removal safety. Rule text is opaque."
)


def _identity(chain: Chain) -> tuple:
    return chain.policy, tuple(rule.rule_text for rule in chain.rules)


def _rate(delta: int, elapsed: int) -> str:
    # Inputs are bounded uint64 and microseconds; no float precision or overflow.
    with localcontext() as context:
        context.prec = 80
        context.rounding = ROUND_HALF_EVEN
        value = Decimal(delta) * 1_000_000 / Decimal(elapsed)
        return format(value.quantize(Decimal("0.000000001")), "f")


def compare(before: Snapshot, after: Snapshot, *, assume_continuity: bool = False) -> dict:
    """Compare ordered snapshots. The assumption flag is never evidence."""
    duration = after.captured_at - before.captured_at
    elapsed = (duration.days * 86400 + duration.seconds) * 1_000_000 + duration.microseconds
    if elapsed <= 0:
        raise InputError("after captured_at must be strictly later than before")
    source_matches = before.source_id == after.source_id
    epoch_matches = before.epoch_id is not None and before.epoch_id == after.epoch_id
    report = {
        "report_version": 1,
        "before": {"source_id": before.source_id, "epoch_id": before.epoch_id,
                   "captured_at": before.captured_at.isoformat()},
        "after": {"source_id": after.source_id, "epoch_id": after.epoch_id,
                  "captured_at": after.captured_at.isoformat()},
        "elapsed_microseconds": elapsed,
        "mode": "conditional" if assume_continuity else "observation-only",
        "source_assertions_match": source_matches,
        "epoch_assertions_match": epoch_matches,
        "continuity_proven": False,
        "limitation": LIMITATION,
        "rate_rounding": "9 decimal places, decimal half-even; deltas and elapsed time remain exact",
        "chains": [],
    }
    left = {chain.name: chain for chain in before.chains}
    right = {chain.name: chain for chain in after.chains}
    for name in dict.fromkeys([*left, *right]):
        old, new = left.get(name), right.get(name)
        if not source_matches:
            status = "source-mismatch"
        elif old is None:
            status = "added"
        elif new is None:
            status = "removed"
        elif _identity(old) != _identity(new):
            status = "changed"
        else:
            status = "unchanged"
        chain_report = {
            "name": name, "status": status,
            "before_policy": old.policy if old else None,
            "after_policy": new.policy if new else None,
            "before_rules": [vars(rule).copy() for rule in old.rules] if old else [],
            "after_rules": [vars(rule).copy() for rule in new.rules] if new else [],
            "observations": [],
        }
        # Changed/added/removed/source-mismatched chains expose unpaired evidence.
        if status == "unchanged":
            duplicates = Counter(rule.rule_text for rule in old.rules)
            for first, second in zip(old.rules, new.rules):
                observation = {"position": first.position, "rule_text": first.rule_text,
                               "status": "observed", "observed_difference": None,
                               "conditional": None, "conditional_withheld": []}
                if duplicates[first.rule_text] > 1:
                    observation["status"] = "ambiguous-duplicate"
                elif any(value is None for value in (first.packets, first.bytes, second.packets, second.bytes)):
                    observation["status"] = "missing-counter"
                else:
                    packets = second.packets - first.packets
                    size = second.bytes - first.bytes
                    observation["observed_difference"] = {"packets": packets, "bytes": size}
                    if packets < 0 or size < 0:
                        observation["status"] = "discontinuity"
                    elif packets == size == 0:
                        observation["status"] = "zero-observed-change"
                reasons = observation["conditional_withheld"]
                if not assume_continuity:
                    reasons.append("continuity assumption not requested")
                if not epoch_matches:
                    reasons.append("matching non-null epoch assertions required")
                if observation["status"] not in ("observed", "zero-observed-change"):
                    reasons.append(observation["status"])
                if not reasons:
                    difference = observation["observed_difference"]
                    observation["conditional"] = {
                        "label": "conditional on operator-assumed continuity; hidden resets remain possible",
                        "delta_packets": difference["packets"], "delta_bytes": difference["bytes"],
                        "packets_per_second": _rate(difference["packets"], elapsed),
                        "bytes_per_second": _rate(difference["bytes"], elapsed),
                    }
                chain_report["observations"].append(observation)
        report["chains"].append(chain_report)
    return report
