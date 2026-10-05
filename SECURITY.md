# Security model

Threat boundary: user-supplied local JSON, opaque rule text and untrusted metadata.
The tool performs no network access, collection, subprocess execution, privilege
change or host firewall operation. It has no authentication or listening service.
Files/reports run under the invoking user's permissions.

Malformed input is rejected with byte, nesting, numeric-text, string and record
bounds. Duplicate keys/chain identifiers and noncontiguous positions cannot
silently replace evidence. Unknown fields fail closed. Rules are opaque data.
HTML escapes all content, uses no JavaScript/assets and includes a restrictive
CSP. Terminal output exposes non-ASCII/bidi code points; JSON uses ASCII escapes.
The CLI creates output exclusively, including refusal of existing symlink paths.

Misleading metadata remains possible. Source/epoch are operator assertions, not
signatures or trusted telemetry. Matching epochs and nondecreasing samples do not
prove continuity; a reset between samples can remain invisible. No zero-counter
claim licenses deletion. Changed whole-chain identity prevents arithmetic pairing;
duplicates/nulls/decreases withhold inference. Both observed counters are exposed.

Filesystem checks reject nonregular inputs before and after opening; bounded
reads handle file growth. POSIX nonblocking open guards a FIFO substitution race.
This is not an isolation boundary against hostile local processes or compromised
Python/system libraries. No encryption, authenticated snapshot provenance,
atomic full-report guarantee after a disk failure, or independent safety proof.
Do not expose real policy/topology records in public demos or commits. Private
evidence belongs outside tracked artifacts. Review reports before sharing.

Dependency posture: runtime is standard library only. Bandit and its transitive
packages are version-pinned development tools; the current file is not an
artifact-hash lock or a supply-chain safety certificate. Reassess before future
installation; no new dependencies were installed in this stage. Hosted CodeQL,
secret scanning and branch protections await a separately authorized remote.

Report potential defects privately to the repository owner. No public reporting
endpoint or live target testing is provided. Manual semantic review precedes
consequential use; publication and merges need Jake's explicit authorization.
