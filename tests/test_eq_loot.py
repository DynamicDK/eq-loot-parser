"""Tests for the loot parser and the GUI's output formatting.

Run with:  python -m unittest discover -s tests
Uses only the standard library (unittest) — no extra dependencies.
"""

import os
import sys
import tempfile
import tkinter as tk
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import eq_loot_gui  # noqa: E402
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

    def test_single_digit_day_with_padded_space(self):
        # EQ pads single-digit days with a second space: "Wed Dec  3".
        fd, path = tempfile.mkstemp(suffix=".txt")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("[Wed Dec  3 21:15:33 2025] --Bixie has looted a Rusty Dagger from a rat.--\n")
        try:
            events = list(parse_log(path, "Nandoor"))
        finally:
            os.remove(path)
        self.assertEqual(events, [(date(2025, 12, 3), "Bixie", 1, "Rusty Dagger")])


class FormatLootTextTests(unittest.TestCase):
    def setUp(self):
        self.collected = [
            ("Cloak of Flames", "Nandoor"),
            ("Reaper of the Dead", "Bixie"),
        ]

    def test_names_only_one_per_line(self):
        # Intentionally no trailing newline (cleaner clipboard paste); the CSV
        # form below intentionally does have one, per CSV convention.
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


class GuiAddRemoveTests(unittest.TestCase):
    """Drive LootApp directly to lock in the check -> add -> remove flow.

    Skipped automatically when no display is available (e.g. headless CI).
    """

    GROUPED_LOG = "[Mon Jan 02 21:16:00 2024] --Bixie has looted 3 Bone Chips from a skeleton.--\n"

    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as e:
            self.skipTest(f"no display available: {e}")
        self.root.withdraw()
        self.app = eq_loot_gui.LootApp(self.root)
        fd, self.path = tempfile.mkstemp(prefix="eqlog_Nandoor_teek", suffix=".txt")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(self.GROUPED_LOG)
        self.app.load_log(self.path)
        self._select_char("Bixie")

    def tearDown(self):
        try:
            self.root.destroy()
        finally:
            os.remove(self.path)

    def _select_char(self, name):
        labels = list(self.app.char_list.get(0, tk.END))
        idx = next(i for i, c in enumerate(labels) if c.startswith(name))
        self.app.char_list.selection_clear(0, tk.END)
        self.app.char_list.selection_set(idx)

    def test_grouped_row_expands_by_quantity(self):
        self.app.ungroup.set(False)
        self.app.refresh_items()
        self.app._set_all_checks(True)
        self.app.add_checked()
        self.assertEqual(self.app.collected, [("Bone Chips", "Bixie")] * 3)

    def test_add_clears_checkboxes(self):
        self.app.refresh_items()
        self.app._set_all_checks(True)
        self.app.add_checked()
        checks = [self.app.item_tree.set(i, "check") for i in self.app.item_tree.get_children()]
        self.assertTrue(all(c == eq_loot_gui.UNCHECKED for c in checks))

    def test_ungrouped_shows_one_row_per_instance(self):
        self.app.ungroup.set(True)
        self.app.refresh_items()
        self.assertEqual(len(self.app.item_tree.get_children()), 3)

    def test_remove_collected_removes_only_selected_row(self):
        self.app.ungroup.set(True)
        self.app.refresh_items()
        self.app._set_all_checks(True)
        self.app.add_checked()  # 3 individual Bone Chips
        middle = self.app.collected_tree.get_children()[1]
        self.app.collected_tree.selection_set(middle)
        self.app.remove_collected()
        self.assertEqual(self.app.collected, [("Bone Chips", "Bixie")] * 2)


if __name__ == "__main__":
    unittest.main()
