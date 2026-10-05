"""Display untrusted text inertly in terminal, JSON and standalone HTML."""
from html import escape
import json


def visible(value: str) -> str:
    """Expose non-ASCII formatting/control code points, including bidi controls."""
    return value.encode("unicode_escape").decode("ascii")


def text_report(report: dict) -> str:
    lines = ["COUNTER WINDOW LAB", f"Mode: {report['mode']}",
             f"Elapsed: {report['elapsed_microseconds']} microseconds", report["limitation"],
             "Continuity proven: false"]
    for side in ("before", "after"):
        snapshot = report[side]
        lines.append(f"{side.title()}: {snapshot['captured_at']} source={snapshot['source_id']} "
                     f"asserted epoch={snapshot['epoch_id'] or 'unknown'}")
    lines.append(f"Source assertions match: {report['source_assertions_match']}; "
                 f"non-null epoch assertions match: {report['epoch_assertions_match']}")
    lines.append("")
    for chain in report["chains"]:
        lines.append(f"{chain['name']}: {chain['status']}")
        for row in chain["observations"]:
            lines.append(f"  {row['position']}. {visible(row['rule_text'])}: {row['status']}")
            for side in ("before", "after"):
                raw = chain[f"{side}_rules"][row["position"] - 1]
                packets = raw["packets"] if raw["packets"] is not None else "unknown"
                size = raw["bytes"] if raw["bytes"] is not None else "unknown"
                lines.append(f"     {side}: {packets} packets, {size} bytes")
            difference = row["observed_difference"]
            if difference is not None:
                lines.append(f"     Observed subtraction: {difference['packets']} packets, {difference['bytes']} bytes")
            if row["conditional"]:
                conditional = row["conditional"]
                lines.append(f"     {conditional['label']}")
                lines.append(f"     Conditional rates: {conditional['packets_per_second']} packets/s; "
                             f"{conditional['bytes_per_second']} bytes/s")
            else:
                lines.append("     Conditional rates withheld: " + "; ".join(row["conditional_withheld"]))
        if not chain["observations"]:
            lines.append("  No paired arithmetic.")
            for side in ("before", "after"):
                lines.append(f"  {side} policy: {chain[f'{side}_policy'] or 'absent'}")
                for raw in chain[f"{side}_rules"]:
                    packets = raw["packets"] if raw["packets"] is not None else "unknown"
                    size = raw["bytes"] if raw["bytes"] is not None else "unknown"
                    lines.append(f"     {raw['position']}. {visible(raw['rule_text'])}: "
                                 f"{packets} packets, {size} bytes (unpaired)")
    lines.append(report["rate_rounding"])
    return "\n".join(lines) + "\n"


def html_report(report: dict) -> str:
    content = escape(text_report(report))
    evidence = escape(json.dumps(report, indent=2, ensure_ascii=True))
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Counter window lab</title>
<style>
body{{margin:0;background:#f5f4f0;color:#171a20;font:16px system-ui,sans-serif}}
main{{max-width:1000px;margin:0 auto;padding:clamp(20px,5vw,64px)}}
header{{border-bottom:1px solid #c9ccd2;padding-bottom:24px;margin-bottom:28px}}
.brand{{color:#496c95;font:700 12px ui-monospace,monospace;letter-spacing:3px}}
h1{{font-size:clamp(32px,5vw,56px);letter-spacing:-2px;line-height:1.05}}
p{{max-width:70ch;line-height:1.6}}
pre{{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.7 ui-monospace,monospace;
background:white;border:1px solid #d5d7db;border-radius:8px;padding:20px}}
summary{{cursor:pointer;font-weight:600;padding:16px 0}}
</style></head><body><main><header><div class="brand">FWRULE / COUNTER WINDOW</div>
<h1>Two samples.<br>Explicit assumptions.</h1>
<p>Observe counter changes without mistaking them for proof of reachability.
Rates require an operator continuity assumption; hidden resets remain possible.</p></header>
<pre>{content}</pre><details><summary>Snapshot evidence and conditional results</summary>
<pre>{evidence}</pre></details></main></body></html>'''


def render(report: dict, format_name: str) -> str:
    if format_name == "json":
        return json.dumps(report, indent=2, ensure_ascii=True) + "\n"
    if format_name == "html":
        return html_report(report)
    return text_report(report)


def incomplete(report: dict) -> bool:
    # Global evidence gaps still matter when the envelopes have no chains/rules.
    if not report["source_assertions_match"]:
        return True
    if report["mode"] == "conditional" and not report["epoch_assertions_match"]:
        return True
    for chain in report["chains"]:
        if chain["status"] != "unchanged":
            return True
        for row in chain["observations"]:
            if row["status"] not in ("observed", "zero-observed-change"):
                return True
            if report["mode"] == "conditional" and row["conditional"] is None:
                return True
    return False
