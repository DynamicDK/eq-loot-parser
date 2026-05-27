"""Tests for the loot parser and the GUI's output formatting.

Run with:  python -m unittest discover -s tests
Uses only the standard library (unittest) — no extra dependencies.
"""

import os
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eq_loot import parse_item, owner_from_filename, parse_log  # noqa: E402
from eq_loot_gui import format_loot_text  # noqa: E402

SAMPLE_LOG = """\
[Mon Jan 02 21:15:33 2024] --You have looted a Rusty Dagger from a decaying skeleton.--
[Mon Jan 02 21:16:00 2024] --Bixie has looted 3 Bone Chips from a skeleton.--
[Tue Jan 03 10:00:00 2024] --You have looted the Crown of King Tormax from King Tormax.--
You say, 'this line is not loot'
[Tue Jan 03 10:01:00 2024] --Bixie has looted a Cloak of Flames from a fire giant.--
"""


class ParseItemTests(unittest.TestCase):
    def test_strips_indefinite_article(self):
        self.assertEqual(parse_item("a Rusty Dagger"), (1, "Rusty Dagger"))
        self.assertEqual(parse_item("an Onyx Ring"), (1, "Onyx Ring"))

    def test_strips_definite_article(self):
        self.assertEqual(parse_item("the Crown of King Tormax"), (1, "Crown of King Tormax"))

    def test_parses_quantity(self):
        self.assertEqual(parse_item("3 Bone Chips"), (3, "Bone Chips"))

    def test_no_prefix(self):
        self.assertEqual(parse_item("Cloak of Flames"), (1, "Cloak of Flames"))


class OwnerFromFilenameTests(unittest.TestCase):
    def test_standard_name(self):
        self.assertEqual(owner_from_filename(r"C:\logs\eqlog_Nandoor_teek.txt"), "Nandoor")

    def test_unrecognized_name(self):
        self.assertIsNone(owner_from_filename("random.txt"))


class ParseLogTests(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".txt")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(SAMPLE_LOG)

    def tearDown(self):
        os.remove(self.path)

    def test_parses_all_loot_lines(self):
        events = list(parse_log(self.path, "Nandoor"))
        self.assertEqual(events, [
            (date(2024, 1, 2), "Nandoor", 1, "Rusty Dagger"),
            (date(2024, 1, 2), "Bixie", 3, "Bone Chips"),
            (date(2024, 1, 3), "Nandoor", 1, "Crown of King Tormax"),
            (date(2024, 1, 3), "Bixie", 1, "Cloak of Flames"),
        ])

    def test_you_falls_back_when_owner_unknown(self):
        events = list(parse_log(self.path, None))
        self.assertEqual(events[0][1], "You")


class FormatLootTextTests(unittest.TestCase):
    def setUp(self):
        self.collected = [
            ("Cloak of Flames", "Nandoor"),
            ("Reaper of the Dead", "Bixie"),
        ]

    def test_names_only_one_per_line(self):
        self.assertEqual(
            format_loot_text(self.collected, with_char=False),
            "Cloak of Flames\nReaper of the Dead",
        )

    def test_with_char_is_csv_with_header(self):
        self.assertEqual(
            format_loot_text(self.collected, with_char=True),
            "Item,Character\nCloak of Flames,Nandoor\nReaper of the Dead,Bixie\n",
        )

    def test_csv_quotes_names_with_commas(self):
        out = format_loot_text([("Sword, Rusty", "Bob")], with_char=True)
        self.assertEqual(out, 'Item,Character\n"Sword, Rusty",Bob\n')

    def test_empty_list(self):
        self.assertEqual(format_loot_text([], with_char=False), "")


if __name__ == "__main__":
    unittest.main()
