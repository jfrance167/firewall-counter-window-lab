# Decisions

- Build original standard-library Python code rather than fork a live exporter.
  Source/license and alternative assessment is retained in docs/PLAN.md.
- Approved coordinator provenance is in STATE.md; four local stages only.
- Schema v1 uses source_id, epoch_id and unique chain names. Rule positions must
  be contiguous. Identical rule texts remain valid but ambiguous for pairing.
- Entire ordered chain policy/text identity gates arithmetic. Source and epoch
  are operator assertions. Nondecrease and epoch equality cannot prove continuity.
- Bound JSON depth before recursive decoding, numeric lexemes before conversion,
  bytes before decode, and records before processing. Reject unknown fields.
- Offset-aware timestamps normalize to UTC; reject unknown -00:00 offsets and
  sub-microsecond precision instead of silently truncating time evidence.
- Whole ordered chain identity includes policy and exact text. Chain-list order
  is irrelevant because each named chain is independently observed. No semantic
  evaluation or cross-chain pairing is performed.
- Conditional rate precision is fixed decimal half-even to 9 places; exact signed
  observed subtraction is diagnostic and never a negative traffic rate.
- Exit 3 exposes evidence gaps; global mismatches remain gaps even with empty
  chains. Exit 0 cannot certify safety or continuity.
- Terminal and HTML expose non-ASCII formatting as escapes; JSON preserves text
  through ASCII escapes. Static HTML has no scripts/assets and a restrictive CSP.
- Reuse owned predecessor CI conventions and same-day verified immutable action
  pins; no hosted eligibility, remote repository or protection changes assumed.
