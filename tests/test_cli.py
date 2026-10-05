from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from counter_window.compare import compare
from counter_window.report import html_report, text_report
from counter_window.snapshot import parse_snapshot
from tests.fixtures import encoded, envelope

ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def setUp(self):
        temp_root = ROOT / ".private" / "test-temp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=temp_root)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.old = envelope()
        self.new = deepcopy(self.old)
        self.new["captured_at"] = "2026-10-05T00:00:10Z"
        self.new["chains"][0]["rules"][0].update(packets=30, bytes=3000)
        self.before, self.after = self.root / "before.json", self.root / "after.json"

    def run_cli(self, *options):
        self.before.write_bytes(encoded(self.old))
        self.after.write_bytes(encoded(self.new))
        return subprocess.run([sys.executable, "-m", "counter_window", str(self.before), str(self.after), *options],
                              cwd=ROOT, capture_output=True, text=True, timeout=10, check=False)

    def test_default_json_and_conditional(self):
        process = self.run_cli("--format", "json")
        self.assertEqual(process.returncode, 0, process.stderr)
        report = json.loads(process.stdout)
        self.assertEqual(report["mode"], "observation-only")
        self.assertIsNone(report["chains"][0]["observations"][0]["conditional"])
        process = self.run_cli("--format", "json", "--assume-continuity")
        report = json.loads(process.stdout)
        self.assertEqual(process.returncode, 0)
        self.assertEqual(report["chains"][0]["observations"][0]["conditional"]["packets_per_second"], "2.000000000")

    def test_evidence_preservation_and_exclusive_output(self):
        process = self.run_cli("--output", str(self.before))
        self.assertEqual(process.returncode, 2)
        self.assertEqual(self.before.read_bytes(), encoded(self.old))
        output = self.root / "result.html"
        process = self.run_cli("--format", "html", "--output", str(output))
        self.assertEqual(process.returncode, 0)
        original = output.read_bytes()
        self.assertEqual(self.run_cli("--output", str(output)).returncode, 2)
        self.assertEqual(output.read_bytes(), original)

    def test_partial_exit_and_invalid_window(self):
        self.new["epoch_id"] = None
        self.assertEqual(self.run_cli("--assume-continuity").returncode, 3)
        self.assertEqual(self.run_cli().returncode, 0)
        self.new["chains"][0]["rules"][0]["bytes"] = 1
        self.assertEqual(self.run_cli().returncode, 3)
        self.new["captured_at"] = self.old["captured_at"]
        process = self.run_cli()
        self.assertEqual(process.returncode, 2)
        self.assertEqual(process.stdout, "")
        self.assertNotIn("Traceback", process.stderr)

    def test_invalid_input_no_output(self):
        self.before.write_text('{"bad":1}', encoding="utf-8")
        self.after.write_bytes(encoded(self.new))
        output = self.root / "report.json"
        process = subprocess.run([sys.executable, "-m", "counter_window", str(self.before), str(self.after),
                                  "--output", str(output)], cwd=ROOT, capture_output=True, text=True,
                                 timeout=10, check=False)
        self.assertEqual(process.returncode, 2)
        self.assertFalse(output.exists())

    def test_inert_text_html_and_bidi(self):
        text = '</pre><script>alert(1)</script><img src="https://example.invalid/x">\u202e{{content}}'
        self.old["chains"][0]["rules"][0]["rule_text"] = text
        self.new["chains"][0]["rules"][0]["rule_text"] = text
        report = compare(parse_snapshot(encoded(self.old)), parse_snapshot(encoded(self.new)))
        html = html_report(report)
        self.assertNotIn("<script>", html)
        self.assertNotIn('<img src=', html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("default-src 'none'", html)
        self.assertIn("\\u202e", text_report(report))
        self.assertNotIn("\u202e", text_report(report))
        self.assertIn("{{content}}", html)

    def test_empty_envelope_still_reports_global_gaps(self):
        self.old["chains"] = self.new["chains"] = []
        self.assertEqual(self.run_cli().returncode, 0)
        self.new["source_id"] = "another-source"
        self.assertEqual(self.run_cli().returncode, 3)
        self.new["source_id"] = self.old["source_id"]
        self.old["epoch_id"] = self.new["epoch_id"] = None
        self.assertEqual(self.run_cli("--assume-continuity").returncode, 3)

    def test_missing_directory_and_oversized_inputs(self):
        self.after.write_bytes(encoded(self.new))
        for path in (self.root / "missing.json", self.root):
            process = subprocess.run([sys.executable, "-m", "counter_window", str(path), str(self.after)],
                                     cwd=ROOT, capture_output=True, text=True, timeout=10, check=False)
            self.assertEqual(process.returncode, 2)
            self.assertNotIn("Traceback", process.stderr)
        self.before.write_bytes(b" " * (2*1024*1024+1))
        process = subprocess.run([sys.executable, "-m", "counter_window", str(self.before), str(self.after)],
                                 cwd=ROOT, capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(process.returncode, 2)
        self.assertIn("2 MiB", process.stderr)


if __name__ == "__main__":
    unittest.main()
