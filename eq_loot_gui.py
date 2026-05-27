"""GUI for browsing EverQuest loot from a log file.

Left pane: characters who looted on the selected day.
Right pane: items they looted, easy to select and copy.
"""

import os
import sys
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from collections import defaultdict

# Reuse the parser from the CLI script next to this file.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eq_loot import parse_log, owner_from_filename  # noqa: E402

DEFAULT_LOG = r"C:\Users\Public\Daybreak Game Company\Installed Games\EverQuest\Logs\eqlog_Nandoor_teek.txt"


class LootApp:
    def __init__(self, root):
        self.root = root
        root.title("EverQuest Loot Viewer")
        root.geometry("900x600")

        self.events = []           # list of (date, char, qty, item)
        self.current_log = None
        self.owner = None

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

        self.exclude_trash = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar, text="Hide trash (meat/powder/low gems)",
                        variable=self.exclude_trash,
                        command=self.refresh_chars).pack(side=tk.LEFT, padx=10)

        ttk.Button(bar, text="Copy selected items", command=self.copy_selected).pack(side=tk.RIGHT)
        ttk.Button(bar, text="Copy all (this char)", command=self.copy_all).pack(side=tk.RIGHT, padx=4)

    def _build_panes(self):
        paned = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        # left: characters
        left = ttk.Frame(paned)
        ttk.Label(left, text="Characters").pack(anchor=tk.W)
        self.char_list = tk.Listbox(left, exportselection=False)
        self.char_list.pack(fill=tk.BOTH, expand=True)
        self.char_list.bind("<<ListboxSelect>>", lambda e: self.refresh_items())
        paned.add(left, weight=1)

        # right: items
        right = ttk.Frame(paned)
        top = ttk.Frame(right)
        top.pack(fill=tk.X)
        ttk.Label(top, text="Items").pack(side=tk.LEFT)
        ttk.Label(top, text="(Ctrl+click to multi-select, Ctrl+A to select all)",
                  foreground="gray").pack(side=tk.LEFT, padx=6)

        cols = ("qty", "item")
        self.item_tree = ttk.Treeview(right, columns=cols, show="headings", selectmode="extended")
        self.item_tree.heading("qty", text="Qty")
        self.item_tree.heading("item", text="Item")
        self.item_tree.column("qty", width=60, anchor=tk.E, stretch=False)
        self.item_tree.column("item", width=400, anchor=tk.W)
        self.item_tree.pack(fill=tk.BOTH, expand=True)
        self.item_tree.bind("<Control-a>", self._select_all_items)
        self.item_tree.bind("<Control-A>", self._select_all_items)
        self.item_tree.bind("<Control-c>", lambda e: self.copy_selected())
        paned.add(right, weight=3)

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
        rows = [e for e in self.events if e[0].isoformat() == day]
        if self.exclude_trash.get():
            trash = ("meat", "powder", "hide", "pelt", "fang", "claw", "scale",
                     "imperfect", "flawed", "nephrite", "jasper", "marble")
            rows = [e for e in rows if not any(t in e[3].lower() for t in trash)]
        return rows

    def refresh_chars(self):
        self.char_list.delete(0, tk.END)
        rows = self._current_day_events()
        totals = defaultdict(int)
        for _, who, qty, _ in rows:
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
        if not who:
            return
        merged = defaultdict(int)
        for _, c, qty, item in self._current_day_events():
            if c == who:
                merged[item] += qty
        for item in sorted(merged):
            self.item_tree.insert("", tk.END, values=(merged[item], item))

    # ---------- copy actions ----------
    def _select_all_items(self, event=None):
        for iid in self.item_tree.get_children():
            self.item_tree.selection_add(iid)
        return "break"

    def _rows_to_text(self, iids):
        lines = []
        for iid in iids:
            qty, item = self.item_tree.item(iid, "values")
            qty = int(qty)
            lines.append(f"{qty}x {item}" if qty > 1 else item)
        return "\n".join(lines)

    def _push_clipboard(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()  # ensure clipboard persists after window closes
        self.status.set(f"Copied {text.count(chr(10)) + 1 if text else 0} line(s) to clipboard.")

    def copy_selected(self):
        iids = self.item_tree.selection() or self.item_tree.get_children()
        self._push_clipboard(self._rows_to_text(iids))

    def copy_all(self):
        self._push_clipboard(self._rows_to_text(self.item_tree.get_children()))


def main():
    root = tk.Tk()
    LootApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
