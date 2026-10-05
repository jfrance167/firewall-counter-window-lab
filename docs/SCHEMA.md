# Snapshot schema version 1

UTF-8 JSON without a BOM. Exact field sets; unknown/missing fields are errors.
Duplicate object keys are errors at every level. Numbers must be JSON integers:
no booleans, fractional numbers, exponents or nonfinite constants.

```json
{
  "schema_version": 1,
  "source_id": "synthetic-lab",
  "captured_at": "2026-10-05T00:00:00Z",
  "epoch_id": "operator-asserted-epoch",
  "chains": [
    {"name": "INPUT", "policy": "DROP", "rules": [
      {"position": 1, "rule_text": "-s 192.0.2.0/24 -j ACCEPT", "packets": 10, "bytes": 1000}
    ]}
  ]
}
```

- `schema_version`: exact integer 1.
- `source_id`: opaque operator source assertion; 1–128 ASCII characters from
  letters, digits, underscore, dot, colon or hyphen. One source per envelope.
- `epoch_id`: same identifier contract, or null. Equality is an assertion, not
  a collector guarantee or proof of continuity.
- `captured_at`: RFC3339 subset: uppercase T/Z, seconds required, 0–6 fractional
  digits, Z or numeric ±HH:MM offset. Valid calendar/time required; no leap
  seconds, naive time, -00:00 unknown offset or precision truncation. UTC
  normalization must remain representable in Python years 1–9999.
- `chains`: ordered array of at most 1,000 chains; empty permitted. `name` unique
  within each envelope and uses the identifier contract. `policy` uses the same
  string contract and is compared as opaque text; no policy semantics evaluated.
- `rules`: ordered array; at most 1,000 total records per envelope. `position`
  contiguous integer 1 through chain length, unique within the chain. No separate
  record identifier is accepted. Exact duplicate texts are allowed but ambiguous.
- `rule_text`: 1–8,192 Unicode characters, excluding C0/C1 controls, DEL and
  unpaired surrogates. Whitespace/case changes affect identity. Display escapes
  non-ASCII characters (including bidi formatting); it never executes the text.
- `packets`, `bytes`: independently null or uint64 (0 through 2^64 − 1). Null
  means unknown. Missing either counter withholds both paired differences/rates.

Each file: at most 2 MiB; JSON nesting at most 8 (outside strings); numeric
lexemes at most 20 characters including sign. Root/chain/rule fields must match
the illustrated sets exactly. Regular files only, bounded reads. Unicode escape
expansion occurs within the byte limit and decoded text limit.

## Report version 1

JSON retains both source/time/epoch assertions, exact `elapsed_microseconds`,
`continuity_proven: false`, shared limitations and each chain's policies/raw
before/after rules. Chain status: unchanged, changed, added, removed or
source-mismatch. Source mismatch takes precedence over chain status.

Only unchanged chains produce `observations`: position/text, status, optional
`observed_difference` and optional `conditional`, with `conditional_withheld`
reasons. Rule status is observed, zero-observed-change, ambiguous-duplicate,
missing-counter or discontinuity. Signed observed subtraction is diagnostic;
a negative value is never a negative traffic rate. Duplicate/missing evidence
has a null subtraction. No union, heuristic renumbering or cross-chain pairing.

Conditional estimates require the explicit flag, matching source and non-null
epoch assertions, unchanged ordered chain, unique text, known counters and no
decrease in either. Rate strings are rounded to 9 fractional places, half-even;
the `delta_packets`, `delta_bytes` and elapsed microseconds are exact integers.
No estimate claims continuity, actual traffic, reachability or removal safety.
