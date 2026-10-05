"""Strict, resource-bounded snapshot contract. Rule text is never executed."""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import stat

MAX_BYTES = 2 * 1024 * 1024
MAX_RULES = 1000
MAX_DEPTH = 8
MAX_NUMBER_TEXT = 20
UINT64_MAX = (1 << 64) - 1
IDENTIFIER = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")
TIMESTAMP = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})\Z",
    re.ASCII,
)


class InputError(ValueError):
    """A snapshot or window violates the supported contract."""


@dataclass(frozen=True)
class Rule:
    position: int
    rule_text: str
    packets: int | None
    bytes: int | None


@dataclass(frozen=True)
class Chain:
    name: str
    policy: str
    rules: tuple[Rule, ...]


@dataclass(frozen=True)
class Snapshot:
    source_id: str
    captured_at: datetime
    epoch_id: str | None
    chains: tuple[Chain, ...]


def _depth_check(text: str) -> None:
    # Count only outside JSON strings; reject before the recursive JSON decoder.
    depth = 0
    quoted = escaped = False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            if depth > MAX_DEPTH:
                raise InputError("JSON nesting exceeds 8 levels")
        elif char in "}]":
            depth -= 1


def _pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError("duplicate JSON object key")
        result[key] = value
    return result


def _integer_text(value: str) -> int:
    if len(value) > MAX_NUMBER_TEXT:
        raise InputError("numeric text exceeds 20 characters")
    return int(value)


def _reject_number(_value: str) -> None:
    raise InputError("only integer JSON numbers are supported")


def _fields(value: object, expected: set[str], label: str) -> dict:
    if type(value) is not dict or set(value) != expected:
        raise InputError(f"{label}: missing or unknown fields")
    return value


def _identifier(value: object, label: str) -> str:
    if type(value) is not str or not IDENTIFIER.fullmatch(value):
        raise InputError(f"{label}: expected 1–128 ASCII identifier characters")
    return value


def _counter(value: object) -> int | None:
    if value is not None and (type(value) is not int or not 0 <= value <= UINT64_MAX):
        raise InputError("counters must be null or uint64 integers")
    return value


def parse_snapshot(data: bytes) -> Snapshot:
    """Decode a UTF-8 JSON envelope within explicit byte/depth/record limits."""
    if len(data) > MAX_BYTES:
        raise InputError("snapshot exceeds 2 MiB")
    try:
        text = data.decode("utf-8")
        _depth_check(text)
        raw = json.loads(text, object_pairs_hook=_pairs, parse_int=_integer_text,
                         parse_float=_reject_number, parse_constant=_reject_number)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise InputError("invalid UTF-8 JSON") from error
    root = _fields(raw, {"schema_version", "source_id", "captured_at", "epoch_id", "chains"}, "snapshot")
    if type(root["schema_version"]) is not int or root["schema_version"] != 1:
        raise InputError("schema_version must be integer 1")
    source = _identifier(root["source_id"], "source_id")
    epoch = root["epoch_id"]
    if epoch is not None:
        epoch = _identifier(epoch, "epoch_id")
    stamp = root["captured_at"]
    if type(stamp) is not str or not TIMESTAMP.fullmatch(stamp):
        raise InputError("captured_at must be offset-aware RFC3339 with at most 6 fraction digits")
    # RFC3339 -00:00 means unknown offset, unsuitable for exact window arithmetic.
    if stamp.endswith("-00:00"):
        raise InputError("unknown timestamp offset -00:00 is unsupported")
    if stamp[-6:-5] in ("+", "-") and (int(stamp[-5:-3]) > 23 or int(stamp[-2:]) > 59):
        raise InputError("invalid timestamp offset")
    try:
        captured = datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(timezone.utc)
    except (ValueError, OverflowError) as error:
        raise InputError("invalid timestamp") from error
    if type(root["chains"]) is not list or len(root["chains"]) > 1000:
        raise InputError("chains must be an array with at most 1000 entries")
    names, chains, total = set(), [], 0
    for item in root["chains"]:
        chain = _fields(item, {"name", "policy", "rules"}, "chain")
        name = _identifier(chain["name"], "chain name")
        if name in names:
            raise InputError("duplicate chain identifier")
        names.add(name)
        policy = _identifier(chain["policy"], "policy")
        if type(chain["rules"]) is not list:
            raise InputError("rules must be an array")
        total += len(chain["rules"])
        if total > MAX_RULES:
            raise InputError("snapshot exceeds 1000 rules")
        rules = []
        for position, item in enumerate(chain["rules"], 1):
            rule = _fields(item, {"position", "rule_text", "packets", "bytes"}, "rule")
            if type(rule["position"]) is not int or rule["position"] != position:
                raise InputError("rule positions must be contiguous integers starting at 1")
            text = rule["rule_text"]
            if type(text) is not str or not 1 <= len(text) <= 8192:
                raise InputError("rule_text must contain 1–8192 characters")
            if any(ord(char) < 32 or 127 <= ord(char) <= 159 or 0xD800 <= ord(char) <= 0xDFFF for char in text):
                raise InputError("rule_text contains control characters or unpaired surrogates")
            rules.append(Rule(position, text, _counter(rule["packets"]), _counter(rule["bytes"])))
        chains.append(Chain(name, policy, tuple(rules)))
    return Snapshot(source, captured, epoch, tuple(chains))


def load_snapshot(path: Path) -> Snapshot:
    """Read a regular file with a bounded read, including growth after stat."""
    if not stat.S_ISREG(path.stat().st_mode):
        raise InputError("snapshot input must be a regular file")
    # On POSIX, nonblocking open prevents a regular-file-to-FIFO race hanging.
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
    with os.fdopen(os.open(path, flags), "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise InputError("snapshot input must be a regular file")
        if info.st_size > MAX_BYTES:
            raise InputError("snapshot exceeds 2 MiB")
        return parse_snapshot(handle.read(MAX_BYTES + 1))
