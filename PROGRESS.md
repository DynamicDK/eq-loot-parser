# Progress

## 2026-05-27 — Loot-list builder + remove trash filter

**Objective:** Drop the unreliable trash filter and turn the GUI into a tool for
hand-picking loot across characters into a single copy/exportable list.

**Done:**
- Removed `--exclude-trash` from the CLI and the trash-substring filter from both
  `eq_loot.py` and the GUI (it would inevitably mis-classify items).
- GUI redesigned into three panes: characters → items → collected list.
  - "Ungroup items" toggle: show each copy on its own row vs. one row with a qty.
  - Checkbox column on the items pane (click a row to toggle); Check/Uncheck all.
  - "Add checked →" copies checked items into the collected list, tagged with the
    looting character, and clears the checkboxes. A grouped qty-N row adds N entries.
  - Remove selected / Clear on the collected list.
  - Copy ▾ and Export ▾ menubuttons, each offering "Item names only" (one per line)
    and "Items + character" (CSV with an Item,Character header).
- Added `tests/test_eq_loot.py` (stdlib `unittest`, 12 tests) covering the parser
  and the GUI's output formatting. Extracted `format_loot_text()` as a pure,
  testable function.
- Updated README.

**Status:** Complete. All 12 tests pass; GUI smoke-tested headlessly.

**Known caveat (pre-existing, not in scope):** the loot-line regex expects a single
space before the day-of-month, so single-digit days (which EQ pads with two spaces,
e.g. `Wed Dec  3`) may not match. Worth confirming against a real log before relying on it.
