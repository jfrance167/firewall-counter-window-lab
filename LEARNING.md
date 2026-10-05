# Learning

Counters are observations. Interpreting them over time needs a defined window,
stable rule identity and explicit continuity assumptions. Even a higher second
counter can hide a reset and subsequent activity; zero is not unreachability.

JSON booleans are Python integers by inheritance, so exact type checks protect
the uint64 schema. Decoder callbacks alone do not bound nested input: inspect
depth outside quoted strings before invoking the recursive decoder.

Whole-chain identity is stronger than position or text similarity alone. If a
rule moves, a nearby counter is not evidence for the old record. Duplicates remain
ambiguous even at unchanged positions; null means unknown instead of zero.

Review found that inheriting a caller's decimal rounding mode contradicted the
report contract. Explicit contexts prevent ambient state from changing rates.
Empty inputs also need global evidence checks: a loop over zero rules cannot
validate source/epoch identity. Regression tests protect both fixes.
