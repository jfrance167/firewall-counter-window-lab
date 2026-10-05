# Verification — October 5, 2026

Windows, Python 3.13.7. Evidence under ignored `.private/verification/`;
full logs and exit codes retained locally. No additional dependencies installed.

| Check | Outcome | Evidence / scope |
| --- | --- | --- |
| `python -m unittest discover -v` | PASS, 22 tests, exit 0 | tests.log; parser, independent specified comparison fixtures, CLI subprocess tests |
| `python scripts/demo_reports.py --check` | PASS, six exact artifacts, exit 0 | demo.log; inputs + text/JSON/HTML reports |
| `python -m compileall -q counter_window scripts tests` | PASS, exit 0 | compile.log |
| `python -m bandit -r counter_window scripts -f json -o .private/verification/bandit.json` | PASS, exit 0 | Bandit 1.9.4, zero findings/errors, 424 lines; no suppressions |
| Playwright CLI / headless Chrome | PASS, exit 0 | browser-*.js/log, browser-exits.json; desktop 1280×900 and mobile 390×844, no overflow, disclosure opens |
| Inert injection rendering | PASS | browser-injection.js/log; escaped closing tags/script/img/bidi, zero scripts/images/execution/requests/page errors; console errors 0 |
| Workflow YAML structure / action pins | PASS | repository-checks.json; full 40-character SHAs, minimum permissions, main triggers, manual dispatch, weekly CodeQL, checkout credentials disabled |
| Targeted tracked/history secret signatures | PASS within limited patterns | repository-checks.json; no matches; not a dedicated secret scan or proof of absence |
| `git diff --cached --check` | PASS, exit 0 | diff.log |
| Hosted CI / CodeQL / branch protections | NOT RUN | no remote repository, eligibility unknown |
| Linux / POSIX file-race execution | NOT RUN | Windows environment; guards inspected, no Linux claim |
| Static type checker | NOT RUN | not installed/requested; runtime and compile checks performed |
| Live counter collection / firewall operations | NOT APPLICABLE | outside scope, none performed |

Tests cover malformed/duplicate JSON, unknown/missing fields, numeric bounds and
booleans, timestamp offsets/precision/overflow, resource limits, unique chain
names/contiguous rule positions, null and duplicate rule identities. Comparison
fixtures cover both increasing and zero counts, either counter decreasing,
changed/reordered/added/removed rules and policies, source/epoch mismatches,
hidden resets and exact positive microsecond windows. CLI tests verify output
exclusivity/input preservation, errors without tracebacks and incomplete exits,
including empty envelopes. Decimal rate rounding is fixed even under changed
ambient rounding. Browser assertions loaded generated content into about:blank;
no server was started. Screenshots inspected at samples/desktop.png and mobile.png.

The first CLI test run failed because Windows sandbox scratch temp paths denied
file writes; tests now use ignored workspace scratch directories. Final tests
pass. Review findings and fixes are in REVIEW.md. These checks do not establish
telemetry continuity, authenticity, reachability or removal safety.
