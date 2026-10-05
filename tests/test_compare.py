from copy import deepcopy
from decimal import localcontext, ROUND_DOWN
import unittest
from counter_window.compare import compare
from counter_window.snapshot import InputError, parse_snapshot, UINT64_MAX
from tests.fixtures import encoded, envelope


class CompareTests(unittest.TestCase):
    def window(self):
        old = envelope()
        new = deepcopy(old)
        new["captured_at"] = "2026-10-05T00:00:02Z"
        new["chains"][0]["rules"][0].update(packets=14, bytes=1400)
        return old, new

    def result(self, old, new, assume=False):
        return compare(parse_snapshot(encoded(old)), parse_snapshot(encoded(new)), assume_continuity=assume)

    def test_observation_default_and_zero(self):
        report = self.result(*self.window())
        first, second = report["chains"][0]["observations"]
        self.assertEqual(first["observed_difference"], {"packets": 4, "bytes": 400})
        self.assertEqual(second["status"], "zero-observed-change")
        self.assertIsNone(first["conditional"])
        self.assertFalse(report["continuity_proven"])
        self.assertIn("removal safety", report["limitation"])

    def test_conditional_rates_exact_time(self):
        old, new = self.window()
        new["captured_at"] = "2026-10-04T20:00:02.000001-04:00"
        report = self.result(old, new, True)
        self.assertEqual(report["elapsed_microseconds"], 2000001)
        rate = report["chains"][0]["observations"][0]["conditional"]
        self.assertEqual(rate["packets_per_second"], "1.999999000")
        self.assertIn("hidden resets", rate["label"])
        self.assertFalse(report["continuity_proven"])

    def test_one_microsecond_uint64_and_positive_window(self):
        old, new = self.window()
        old["chains"][0]["rules"][0].update(packets=0, bytes=0)
        new["chains"][0]["rules"][0].update(packets=UINT64_MAX, bytes=UINT64_MAX)
        new["captured_at"] = "2026-10-05T00:00:00.000001Z"
        report = self.result(old, new, True)
        self.assertEqual(report["elapsed_microseconds"], 1)
        self.assertEqual(report["chains"][0]["observations"][0]["conditional"]["packets_per_second"],
                         "18446744073709551615000000.000000000")
        for stamp in (old["captured_at"], "2026-10-04T23:59:59.999999Z"):
            new["captured_at"] = stamp
            with self.assertRaises(InputError):
                self.result(old, new, True)

    def test_chain_change_has_no_pairing(self):
        for change in ("policy", "reorder", "add", "remove", "text"):
            old, new = self.window()
            chain = new["chains"][0]
            if change == "policy":
                chain["policy"] = "ACCEPT"
            elif change == "reorder":
                chain["rules"].reverse()
                for index, rule in enumerate(chain["rules"], 1):
                    rule["position"] = index
            elif change == "add":
                chain["rules"].append(dict(position=3, rule_text="extra", packets=1, bytes=1))
            elif change == "remove":
                chain["rules"].pop()
            else:
                chain["rules"][0]["rule_text"] += " "
            with self.subTest(change=change):
                report = self.result(old, new, True)["chains"][0]
                self.assertEqual(report["status"], "changed")
                self.assertEqual(report["observations"], [])

    def test_added_removed_source_and_epoch(self):
        old, new = self.window()
        new["chains"] = [dict(name="OUTPUT", policy="DROP", rules=[])]
        self.assertEqual([c["status"] for c in self.result(old, new)["chains"]], ["removed", "added"])
        old, new = self.window()
        new["source_id"] = "other"
        self.assertEqual(self.result(old, new, True)["chains"][0]["status"], "source-mismatch")
        for epoch in (None, "another-epoch"):
            old, new = self.window()
            new["epoch_id"] = epoch
            first = self.result(old, new, True)["chains"][0]["observations"][0]
            self.assertEqual(first["observed_difference"]["packets"], 4)
            self.assertIsNone(first["conditional"])

    def test_duplicates_missing_and_either_decrease(self):
        old, new = self.window()
        for raw in (old, new):
            raw["chains"][0]["rules"][1]["rule_text"] = raw["chains"][0]["rules"][0]["rule_text"]
        for row in self.result(old, new, True)["chains"][0]["observations"]:
            self.assertEqual(row["status"], "ambiguous-duplicate")
            self.assertIsNone(row["observed_difference"])
        for field in ("packets", "bytes"):
            for value, status in ((None, "missing-counter"), (0, "discontinuity")):
                old, new = self.window()
                new["chains"][0]["rules"][0][field] = value
                row = self.result(old, new, True)["chains"][0]["observations"][0]
                self.assertEqual(row["status"], status)
                self.assertIsNone(row["conditional"])

    def test_hidden_reset_not_claimed_as_continuity(self):
        # Same visible samples fit both 4 increments and reset-to-zero + 14.
        old, new = self.window()
        report = self.result(old, new, True)
        self.assertTrue(report["epoch_assertions_match"])
        self.assertFalse(report["continuity_proven"])
        self.assertIn("hidden resets", report["limitation"])

    def test_fixed_rounding_and_day_boundary(self):
        old, new = self.window()
        new["captured_at"] = "2026-10-05T00:00:03Z"
        new["chains"][0]["rules"][0]["packets"] = 12
        with localcontext() as context:
            context.rounding = ROUND_DOWN
            row = self.result(old, new, True)["chains"][0]["observations"][0]
        self.assertEqual(row["conditional"]["packets_per_second"], "0.666666667")
        new["captured_at"] = "2026-10-06T00:00:00.000001Z"
        self.assertEqual(self.result(old, new)["elapsed_microseconds"], 86400000001)


if __name__ == "__main__":
    unittest.main()
