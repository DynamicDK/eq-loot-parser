# eq-loot-parser

Parse EverQuest client logs to extract loot, grouped by character and filtered by date.

## Files

- `eq_loot.py` — CLI parser. Reads an `eqlog_<Name>_<server>.txt` file and prints loot grouped by character for a given day.
- `eq_loot_gui.py` — Tkinter GUI for browsing loot by day and character, with copy-to-clipboard for selected items.
- `eq_loot_gui.bat` — Windows launcher that runs the GUI with `pythonw`.

## CLI usage

```
python eq_loot.py <log_file> [--date YYYY-MM-DD] [--chars Name1,Name2,...] [--exclude-trash]
```

- `--date` defaults to the most recent day with loot events in the log.
- `--chars` filters to specific characters (case-insensitive). Omit to include everyone.
- `--exclude-trash` hides common tradeskill / vendor drops (meat, powders, low gems, etc.).

The log owner is inferred from the filename (`eqlog_<Name>_<server>.txt`) and is substituted for `You` in loot lines so the logging character is attributed correctly.

## GUI usage

Double-click `eq_loot_gui.bat` (or run `python eq_loot_gui.py`). The GUI auto-loads the default log path if present; use **Open log...** to pick a different one. Select a day and character, then **Copy selected items** or **Copy all (this char)**.

## Requirements

Python 3.10+ (uses `str | None` type hints). The GUI uses only the standard library (`tkinter`).
