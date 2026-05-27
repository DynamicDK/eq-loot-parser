"""Extract loot from an EverQuest log file, grouped by character and filtered by date.

Usage:
    python eq_loot.py <log_file> [--date YYYY-MM-DD] [--chars Name1,Name2,...]

If --date is omitted, the most recent day with loot events in the log is used.
If --chars is omitted, every character that looted on that day is included.
The owner of the log (parsed from the filename: eqlog_<Name>_<server>.txt) replaces
"You" so loot to the logging character is attributed correctly.
"""

import argparse
import os
import re
import sys
from collections import defaultdict
from datetime import datetime

LOOT_RE = re.compile(
    r"^\[(?P<ts>[A-Z][a-z]{2} [A-Z][a-z]{2} \d{1,2} \d{2}:\d{2}:\d{2} \d{4})\] "
    r"--(?P<who>You|[A-Z][a-zA-Z]+) (?:have|has) looted "
    r"(?P<item>.+?) from (?P<source>.+?)\s*\.--\s*$"
)

ITEM_PREFIX_RE = re.compile(r"^(?:(?P<qty>\d+)\s+|an?\s+|the\s+)", re.IGNORECASE)


def parse_item(raw: str):
    """Return (quantity, item_name). Strips leading article or count."""
    m = ITEM_PREFIX_RE.match(raw)
    if not m:
        return 1, raw.strip()
    qty = int(m.group("qty")) if m.group("qty") else 1
    return qty, raw[m.end():].strip()


def owner_from_filename(path: str) -> str | None:
    base = os.path.basename(path)
    m = re.match(r"eqlog_([A-Za-z]+)_", base)
    return m.group(1) if m else None


def parse_log(path: str, owner: str | None):
    """Yield (date_obj, character, quantity, item_name) for each loot line."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if "looted" not in line:
                continue
            m = LOOT_RE.match(line)
            if not m:
                continue
            ts = datetime.strptime(m.group("ts"), "%a %b %d %H:%M:%S %Y")
            who = m.group("who")
            if who == "You":
                who = owner or "You"
            qty, item = parse_item(m.group("item"))
            yield ts.date(), who, qty, item


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("log_file")
    ap.add_argument("--date", help="YYYY-MM-DD; defaults to the most recent loot day in the log")
    ap.add_argument("--chars", help="Comma-separated character names to include (case-insensitive)")
    args = ap.parse_args(argv)

    owner = owner_from_filename(args.log_file)

    events = list(parse_log(args.log_file, owner))
    if not events:
        print("No loot events found in log.", file=sys.stderr)
        return 1

    if args.date:
        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    else:
        target_date = max(d for d, *_ in events)

    char_filter = None
    if args.chars:
        char_filter = {c.strip().lower() for c in args.chars.split(",") if c.strip()}

    # character -> item -> total quantity
    loot = defaultdict(lambda: defaultdict(int))
    for d, who, qty, item in events:
        if d != target_date:
            continue
        if char_filter and who.lower() not in char_filter:
            continue
        loot[who][item] += qty

    if not loot:
        print(f"No loot found for {target_date}"
              + (f" with characters {sorted(char_filter)}" if char_filter else ""))
        return 0

    print(f"=== Loot for {target_date} ===\n")
    for who in sorted(loot):
        items = loot[who]
        total = sum(items.values())
        print(f"{who}  ({total} item{'s' if total != 1 else ''})")
        for item in sorted(items):
            qty = items[item]
            print(f"  {qty:>3} x {item}" if qty > 1 else f"      - {item}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
