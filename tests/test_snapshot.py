import unittest
from counter_window.snapshot import InputError, MAX_BYTES, UINT64_MAX, parse_snapshot
from tests.fixtures import encoded, envelope


class SnapshotTests(unittest.TestCase):
    def rejected(self, raw):
        with self.assertRaises(InputError):
            parse_snapshot(encoded(raw))

    def test_valid_and_null_uint64(self):
        raw = envelope()
        raw["chains"][0]["rules"][0].update(packets=UINT64_MAX, bytes=None)
        snap = parse_snapshot(encoded(raw))
        self.assertEqual(snap.chains[0].rules[0].packets, UINT64_MAX)
        self.assertIsNone(snap.chains[0].rules[0].bytes)
        self.assertEqual(snap.captured_at.utcoffset().total_seconds(), 0)

    def test_exact_fields_every_level(self):
        for target in ("root", "chain", "rule"):
            for added in (True, False):
                raw = envelope()
                item = raw if target == "root" else raw["chains"][0]
                if target == "rule":
                    item = item["rules"][0]
                if added:
                    item["unknown"] = 1
                else:
                    item.pop(next(iter(item)))
                with self.subTest(target=target, added=added):
                    self.rejected(raw)

    def test_duplicate_keys_and_numeric_lexemes(self):
        for text in ('{"a":1,"a":2}', '{"a":{"b":1,"b":2}}', '{"a":NaN}',
                     '{"a":Infinity}', '{"a":1.0}', '{"a":1e400}', '{"a":' + '9'*21 + '}'):
            with self.subTest(text=text), self.assertRaises(InputError):
                parse_snapshot(text.encode())

    def test_bool_negative_overflow(self):
        for value in (True, False, -1, UINT64_MAX + 1, "1", 1.5, [], {}):
            raw = envelope()
            raw["chains"][0]["rules"][0]["packets"] = value
            self.rejected(raw)
        for field in ("schema_version",):
            raw = envelope()
            raw[field] = True
            self.rejected(raw)

    def test_identifiers_positions_and_duplicates(self):
        for field in ("source_id", "epoch_id"):
            for bad in ("", "x"*129, "new\nline", "é", 1):
                raw = envelope()
                raw[field] = bad
                self.rejected(raw)
        raw = envelope()
        raw["chains"].append(raw["chains"][0].copy())
        self.rejected(raw)
        for bad in (0, 2, True, "1"):
            raw = envelope()
            raw["chains"][0]["rules"][0]["position"] = bad
            self.rejected(raw)
        raw = envelope()
        raw["chains"][0]["rules"][1]["rule_text"] = raw["chains"][0]["rules"][0]["rule_text"]
        self.assertEqual(len(parse_snapshot(encoded(raw)).chains[0].rules), 2)

    def test_timestamp_contract(self):
        for bad in ("2026-10-05", "2026-10-05T00:00:00", "2026-02-30T00:00:00Z",
                    "2026-10-05T00:00:00.1234567Z", "2026-10-05T00:00:00-00:00",
                    "2026-10-05T00:00:00+01:60", "2026-10-05T00:00:60Z",
                    "0001-01-01T00:00:00+01:00"):
            raw = envelope()
            raw["captured_at"] = bad
            self.rejected(raw)
        raw = envelope()
        raw["captured_at"] = "2026-10-04T20:00:00.000001-04:00"
        self.assertEqual(parse_snapshot(encoded(raw)).captured_at.microsecond, 1)

    def test_resources_and_text(self):
        for data in (b"x"*(MAX_BYTES+1), b"["*9+b"]"*9, b"\xff", b"{bad", b"\xef\xbb\xbf{}"):
            with self.assertRaises(InputError):
                parse_snapshot(data)
        for text in ("", "x"*8193, "bad\x00", "bad\x7f", "bad\u0085", "bad\ud800"):
            raw = envelope()
            raw["chains"][0]["rules"][0]["rule_text"] = text
            self.rejected(raw)
        raw = envelope()
        raw["chains"][0]["rules"][0]["rule_text"] = '["\\escaped\\"]'*10
        self.assertEqual(len(parse_snapshot(encoded(raw)).chains), 1)
        raw["chains"][0]["rules"] *= 501
        self.rejected(raw)
        raw = envelope()
        raw["chains"] = [dict(name=f"C{i}", policy="DROP", rules=[]) for i in range(1001)]
        self.rejected(raw)


if __name__ == "__main__":
    unittest.main()
