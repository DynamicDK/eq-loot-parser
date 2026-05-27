# eq-loot-parser

Parse EverQuest client logs to extract loot, grouped by character and filtered by date.

## Files

- `eq_loot.py` — CLI parser. Reads an `eqlog_<Name>_<server>.txt` file and prints loot grouped by character for a given day.
- `eq_loot_gui.py` — Tkinter GUI for browsing loot by day and character, with copy-to-clipboard for selected items.
- `eq_loot_gui.bat` — Windows launcher that runs the GUI with `pythonw`.

## CLI usage

```
python eq_loot.py <log_file> [--date YYYY-MM-DD] [--chars Name1,Name2,...]
```

- `--date` defaults to the most recent day with loot events in the log.
- `--chars` filters to specific characters (case-insensitive). Omit to include everyone.

The log owner is inferred from the filename (`eqlog_<Name>_<server>.txt`) and is substituted for `You` in loot lines so the logging character is attributed correctly.

## GUI usage

Double-click `eq_loot_gui.bat` (or run `python eq_loot_gui.py`). The GUI auto-loads the default log path if present; use **Open log...** to pick a different one.

Workflow:

1. Pick a **day** and a **character** (left pane).
2. **Check** the items you want (middle pane). Click a row to toggle its checkbox, or use **Check all / Uncheck all**. Turn on **Ungroup items** to list each copy on its own row (so you can pick individual ones) instead of a single row with a quantity.
3. **Add checked →** moves the checked items into the collected list on the right, tagged with the character that looted them. (A grouped row with quantity *N* adds *N* entries.) Adding clears the checkboxes.
4. Repeat across characters to build your list. Use **Remove selected** / **Clear** to fix mistakes.
5. **Copy ▾** (to clipboard) or **Export ▾** (to a file). Each offers:
   - **Item names only** — one item per line.
   - **Items + character** — CSV with an `Item,Character` header row.

## Standalone executable (no Python needed)

To produce a single Windows `.exe` that runs on a machine without Python or any
other tools installed:

```
python -m pip install pyinstaller   # one-time
build_exe.bat
```

This writes `dist\eq-loot-viewer.exe`. Double-click it to run — it bundles the
GUI, the parser, and the Python runtime into one file. (Build output under
`build\`, `dist\`, and `*.spec` is git-ignored.)

## Requirements

- **To run the executable:** nothing — it's self-contained (Windows).
- **To run from source or rebuild:** Python 3.10+ (uses `str | None` type hints).
  The GUI uses only the standard library (`tkinter`); building the exe needs
  [PyInstaller](https://pyinstaller.org/).

## Tests

```
python -m unittest discover -s tests
```

Standard-library `unittest` only — no extra dependencies.
