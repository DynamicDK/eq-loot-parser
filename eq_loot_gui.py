"""GUI for browsing EverQuest loot from a log file and building a loot list.

Workflow:
  1. Pick a day and a character (left pane).
  2. Check the items you want (middle pane). "Ungroup items" shows each
     instance on its own row so you can pick individual copies.
  3. "Add checked" moves them into the collected list (right pane), tagged
     with the character that looted them.
  4. Repeat across characters, then Copy or Export the list. Each of those
     offers "Item names only" (one per line) or "Items + character" (CSV).
"""

import csv
import io
import os
import sys
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from collections import defaultdict

# Reuse the parser from the CLI script next to this file.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eq_loot import parse_log, owner_from_filename  # noqa: E402

DEFAULT_LOG = r"C:\Users\Public\Daybreak Game Company\Installed Games\EverQuest\Logs\eqlog_Nandoor_teek.txt"

CHECKED = "☑"    # ☑
UNCHECKED = "☐"  # ☐


def format_loot_text(collected, with_char):
    """Render the collected (item, character) pairs for copy/export.

    with_char=False -> one item name per line.
    with_char=True  -> CSV with an "Item,Character" header row.
    """
    if not with_char:
        return "\n".join(item for item, _ in collected)
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["Item", "Character"])
    for item, char in collected:
        writer.writerow([item, char])
    return buf.getvalue()


class LootApp:
    def __init__(self, root):
        self.root = root
        root.title("EverQuest Loot Viewer")
        root.geometry("1150x640")

        self.events = []           # list of (date, char, qty, item)
        self.current_log = None
        self.owner = None
        self.collected = []        # list of (item, character), one entry per item

        self._build_toolbar()
        self._build_panes()
        self._build_statusbar()

        if os.path.exists(DEFAULT_LOG):
            self.load_log(DEFAULT_LOG)

    # ---------- layout ----------
    def _build_toolbar(self):
        bar = ttk.Frame(self.root, padding=6)
        bar.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(bar, text="Open log...", command=self.open_log).pack(side=tk.LEFT)

        ttk.Label(bar, text="  Date:").pack(side=tk.LEFT)
        self.date_var = tk.StringVar()
        self.date_combo = ttk.Combobox(bar, textvariable=self.date_var, width=14, state="readonly")
        self.date_combo.pack(side=tk.LEFT)
        self.date_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_chars())

        self.ungroup = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar, text="Ungroup items (one row per copy)",
                        variable=self.ungroup,
                        command=self.refresh_items).pack(side=tk.LEFT, padx=10)

    def _build_panes(self):
        paned = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        # --- left: characters ---
        left = ttk.Frame(paned)
        ttk.Label(left, text="Characters").pack(anchor=tk.W)
        self.char_list = tk.Listbox(left, exportselection=False)
        self.char_list.pack(fill=tk.BOTH, expand=True)
        self.char_list.bind("<<ListboxSelect>>", lambda e: self.refresh_items())
        paned.add(left, weight=1)

        # --- middle: items for the selected character ---
        middle = ttk.Frame(paned)
        self.items_label = ttk.Label(middle, text="Items")
        self.items_label.pack(anchor=tk.W)
        ttk.Label(middle, text="(click a row to check it)", foreground="gray").pack(anchor=tk.W)

        cols = ("check", "qty", "item")
        self.item_tree = ttk.Treeview(middle, columns=cols, show="headings", selectmode="none")
        self.item_tree.heading("check", text="✓")
        self.item_tree.heading("qty", text="Qty")
        self.item_tree.heading("item", text="Item")
        self.item_tree.column("check", width=34, anchor=tk.CENTER, stretch=False)
        self.item_tree.column("qty", width=50, anchor=tk.E, stretch=False)
        self.item_tree.column("item", width=340, anchor=tk.W)
        self.item_tree.pack(fill=tk.BOTH, expand=True)
        self.item_tree.bind("<Button-1>", self._on_item_click)

        item_btns = ttk.Frame(middle)
        item_btns.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(item_btns, text="Check all", command=lambda: self._set_all_checks(True)).pack(side=tk.LEFT)
        ttk.Button(item_btns, text="Uncheck all", command=lambda: self._set_all_checks(False)).pack(side=tk.LEFT, padx=4)
        ttk.Button(item_btns, text="Add checked →", command=self.add_checked).pack(side=tk.RIGHT)
        paned.add(middle, weight=2)

        # --- right: the collected loot list ---
        right = ttk.Frame(paned)
        self.collected_label = ttk.Label(right, text="Selected for loot (0)")
        self.collected_label.pack(anchor=tk.W)

        ccols = ("item", "character")
        self.collected_tree = ttk.Treeview(right, columns=ccols, show="headings", selectmode="extended")
        self.collected_tree.heading("item", text="Item")
        self.collected_tree.heading("character", text="Character")
        self.collected_tree.column("item", width=300, anchor=tk.W)
        self.collected_tree.column("character", width=120, anchor=tk.W)
        self.collected_tree.pack(fill=tk.BOTH, expand=True)

        col_btns = ttk.Frame(right)
        col_btns.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(col_btns, text="Remove selected", command=self.remove_collected).pack(side=tk.LEFT)
        ttk.Button(col_btns, text="Clear", command=self.clear_collected).pack(side=tk.LEFT, padx=4)

        self._build_output_button(col_btns, "Copy ▾", self.copy)
        self._build_output_button(col_btns, "Export ▾", self.export)
        paned.add(right, weight=2)

    def _build_output_button(self, parent, text, action):
        """A Menubutton whose two entries perform the action in each mode."""
        mb = ttk.Menubutton(parent, text=text)
        menu = tk.Menu(mb, tearoff=False)
        menu.add_command(label="Item names only", command=lambda: action(False))
        menu.add_command(label="Items + character", command=lambda: action(True))
        mb["menu"] = menu
        mb.pack(side=tk.RIGHT, padx=4)
        return mb

    def _build_statusbar(self):
        self.status = tk.StringVar(value="No log loaded.")
        ttk.Label(self.root, textvariable=self.status, anchor=tk.W,
                  relief=tk.SUNKEN, padding=(6, 2)).pack(side=tk.BOTTOM, fill=tk.X)

    # ---------- data ----------
    def open_log(self):
        path = filedialog.askopenfilename(
            title="Choose EverQuest log",
            initialdir=os.path.dirname(DEFAULT_LOG) if os.path.exists(os.path.dirname(DEFAULT_LOG)) else "/",
            filetypes=[("EQ logs", "eqlog_*.txt"), ("Text", "*.txt"), ("All", "*.*")],
        )
        if path:
            self.load_log(path)

    def load_log(self, path):
        try:
            self.owner = owner_from_filename(path)
            self.events = list(parse_log(path, self.owner))
        except Exception as e:
            messagebox.showerror("Failed to read log", str(e))
            return
        self.current_log = path
        dates = sorted({d.isoformat() for d, *_ in self.events}, reverse=True)
        self.date_combo["values"] = dates
        if dates:
            self.date_var.set(dates[0])
        self.status.set(f"Loaded {os.path.basename(path)} — {len(self.events)} loot events, "
                        f"{len(dates)} days. Owner: {self.owner or '(unknown)'}")
        self.refresh_chars()

    def _current_day_events(self):
        day = self.date_var.get()
        if not day:
            return []
        return [e for e in self.events if e[0].isoformat() == day]

    def refresh_chars(self):
        self.char_list.delete(0, tk.END)
        totals = defaultdict(int)
        for _, who, qty, _ in self._current_day_events():
            totals[who] += qty
        for who in sorted(totals):
            self.char_list.insert(tk.END, f"{who}  ({totals[who]})")
        self.item_tree.delete(*self.item_tree.get_children())
        if totals:
            self.char_list.selection_set(0)
            self.refresh_items()

    def _selected_char(self):
        sel = self.char_list.curselection()
        if not sel:
            return None
        label = self.char_list.get(sel[0])
        return label.rsplit("  (", 1)[0]

    def refresh_items(self):
        self.item_tree.delete(*self.item_tree.get_children())
        who = self._selected_char()
        self.items_label.config(text=f"Items — {who}" if who else "Items")
        if not who:
            return
        rows = [(qty, item) for _, c, qty, item in self._current_day_events() if c == who]
        if self.ungroup.get():
            instances = []
            for qty, item in rows:
                instances.extend([item] * qty)
            for item in sorted(instances):
                self.item_tree.insert("", tk.END, values=(UNCHECKED, "", item))
        else:
            merged = defaultdict(int)
            for qty, item in rows:
                merged[item] += qty
            for item in sorted(merged):
                self.item_tree.insert("", tk.END, values=(UNCHECKED, merged[item], item))

    # ---------- checkbox handling ----------
    def _on_item_click(self, event):
        row = self.item_tree.identify_row(event.y)
        if row:
            current = self.item_tree.set(row, "check")
            self.item_tree.set(row, "check", UNCHECKED if current == CHECKED else CHECKED)
        return "break"  # suppress default row selection

    def _set_all_checks(self, checked):
        mark = CHECKED if checked else UNCHECKED
        for iid in self.item_tree.get_children():
            self.item_tree.set(iid, "check", mark)

    # ---------- collected list ----------
    def add_checked(self):
        who = self._selected_char()
        if not who:
            return
        added = 0
        for iid in self.item_tree.get_children():
            if self.item_tree.set(iid, "check") != CHECKED:
                continue
            item = self.item_tree.set(iid, "item")
            qty_str = self.item_tree.set(iid, "qty")
            n = int(qty_str) if qty_str else 1
            self.collected.extend([(item, who)] * n)
            added += n
            self.item_tree.set(iid, "check", UNCHECKED)
        if added:
            self.refresh_collected()
            self.status.set(f"Added {added} item(s) from {who} to the list.")
        else:
            self.status.set("No items checked.")

    def refresh_collected(self):
        self.collected_tree.delete(*self.collected_tree.get_children())
        for item, char in self.collected:
            self.collected_tree.insert("", tk.END, values=(item, char))
        self.collected_label.config(text=f"Selected for loot ({len(self.collected)})")

    def remove_collected(self):
        sel = set(self.collected_tree.selection())
        if not sel:
            self.status.set("Select rows in the list to remove them.")
            return
        children = self.collected_tree.get_children()
        self.collected = [pair for iid, pair in zip(children, self.collected) if iid not in sel]
        self.refresh_collected()

    def clear_collected(self):
        self.collected = []
        self.refresh_collected()

    # ---------- copy / export ----------
    def _format_text(self, with_char):
        return format_loot_text(self.collected, with_char)

    def copy(self, with_char):
        if not self.collected:
            self.status.set("List is empty — nothing to copy.")
            return
        text = self._format_text(with_char)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()  # ensure clipboard persists after window closes
        self.status.set(f"Copied {len(self.collected)} item(s) to clipboard.")

    def export(self, with_char):
        if not self.collected:
            self.status.set("List is empty — nothing to export.")
            return
        if with_char:
            ext, ftypes, default = ".csv", [("CSV", "*.csv"), ("All", "*.*")], "loot.csv"
        else:
            ext, ftypes, default = ".txt", [("Text", "*.txt"), ("All", "*.*")], "loot.txt"
        path = filedialog.asksaveasfilename(defaultextension=ext, filetypes=ftypes, initialfile=default)
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(self._format_text(with_char))
        except Exception as e:
            messagebox.showerror("Export failed", str(e))
            return
        self.status.set(f"Exported {len(self.collected)} item(s) to {os.path.basename(path)}.")


def main():
    root = tk.Tk()
    LootApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
