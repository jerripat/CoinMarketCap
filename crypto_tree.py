#!/usr/bin/env python3
"""
Crypto Listings Treeview (CoinMarketCap)
- Reads API key from .env (CMC_API_KEY)
- Tkinter UI with sortable columns, search, refresh, and adjustable limit
"""

import os
import requests
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from dotenv import load_dotenv

# ===================== Config =====================
load_dotenv()  # Load .env from current folder
API_KEY = os.getenv("CMC_API_KEY")
if not API_KEY:
    raise ValueError(
        "API key not found. Create a .env file with:\n\nCMC_API_KEY=your_real_key_here\n"
        "and make sure python-dotenv is installed."
    )

URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
DEFAULT_LIMIT = 200           # default number of coins to fetch
AUTO_REFRESH_MS = 0           # set >0 (e.g., 60000) to auto-refresh every N ms

# ===================== Helpers =====================
def fetch_listings(limit=DEFAULT_LIMIT):
    """Return a list of coin dicts (or empty list on error)."""
    headers = {
        "Accepts": "application/json",
        "X-CMC_PRO_API_KEY": API_KEY
    }
    params = {
        "start": "1",
        "limit": str(limit),
        "convert": "USD"
    }
    try:
        r = requests.get(URL, headers=headers, params=params, timeout=20)
        r.raise_for_status()
        payload = r.json()
        return payload.get("data", [])
    except requests.exceptions.HTTPError as e:
        messagebox.showerror("HTTP Error", f"{e}\n\n{r.text if 'r' in locals() else ''}")
    except Exception as e:
        messagebox.showerror("Error", str(e))
    return []

def fmt_money(x):
    try:
        if x is None:
            return "-"
        if x >= 1_000_000_000_000:
            return f"${x/1_000_000_000_000:,.2f}T"
        if x >= 1_000_000_000:
            return f"${x/1_000_000_000:,.2f}B"
        if x >= 1_000_000:
            return f"${x/1_000_000:,.2f}M"
        if x >= 1_000:
            return f"${x/1_000:,.2f}K"
        return f"${x:,.2f}"
    except Exception:
        return "-"

def fmt_price(x):
    try:
        if x is None:
            return "-"
        # Small-price coins get more precision
        return f"${x:,.8f}" if x < 1 else f"${x:,.2f}"
    except Exception:
        return "-"

def fmt_pct(x):
    try:
        return f"{x:.2f}%"
    except Exception:
        return "-"

def fmt_dt(iso):
    try:
        if not iso:
            return "-"
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return iso or "-"

# ===================== UI App =====================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Crypto Listings (CoinMarketCap)")
        self.geometry("1150x640")

        # ----- Controls -----
        controls = ttk.Frame(self, padding=8)
        controls.pack(fill="x")

        ttk.Label(controls, text="Limit:").pack(side="left")
        self.limit_var = tk.StringVar(value=str(DEFAULT_LIMIT))
        ttk.Entry(controls, textvariable=self.limit_var, width=7).pack(side="left", padx=(4, 12))

        ttk.Button(controls, text="Refresh", command=self.refresh).pack(side="left")

        ttk.Label(controls, text=" Search:").pack(side="left", padx=(16, 4))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.apply_filter())
        ttk.Entry(controls, textvariable=self.search_var, width=34).pack(side="left")

        ttk.Label(controls, text="  Auto-refresh (ms):").pack(side="left", padx=(16, 4))
        self.auto_var = tk.StringVar(value=str(AUTO_REFRESH_MS))
        ttk.Entry(controls, textvariable=self.auto_var, width=10).pack(side="left")
        ttk.Button(controls, text="Apply", command=self.apply_auto_refresh).pack(side="left", padx=(6, 0))

        # ----- Treeview -----
        columns = ("rank", "symbol", "name", "price", "pct24h", "pct7d", "mcap", "vol24h", "updated")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=25)
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)

        headings = {
            "rank": "Rank", "symbol": "Symbol", "name": "Name",
            "price": "Price (USD)", "pct24h": "24h %", "pct7d": "7d %",
            "mcap": "Market Cap", "vol24h": "Volume (24h)", "updated": "Last Updated"
        }
        widths = {
            "rank": 60, "symbol": 80, "name": 200, "price": 130,
            "pct24h": 90, "pct7d": 90, "mcap": 150, "vol24h": 150, "updated": 170
        }

        for col in columns:
            self.tree.heading(col, text=headings[col], command=lambda c=col: self.sort_by(c))
            self.tree.column(
                col,
                width=widths[col],
                anchor=("e" if col in ("rank", "price", "pct24h", "pct7d", "mcap", "vol24h") else "w")
            )

        # Row tag styles for positive/negative %s
        self.tree.tag_configure("pos", foreground="green")
        self.tree.tag_configure("neg", foreground="red")
        self.tree.tag_configure("neu", foreground="gray20")

        # Data storage for filtering/sorting
        self.rows_raw = []
        self.current_sort = ("rank", False)  # (column, descending?)

        # Initial load
        self.refresh()
        self._after_id = None
        self.apply_auto_refresh()

    # ----- Data flow -----
    def refresh(self):
        try:
            limit = int(self.limit_var.get())
        except ValueError:
            messagebox.showerror("Input Error", "Limit must be an integer.")
            return

        data = fetch_listings(limit=limit)
        self.rows_raw = []

        for coin in data:
            q = coin.get("quote", {}).get("USD", {})
            row = {
                "rank": coin.get("cmc_rank"),
                "symbol": coin.get("symbol"),
                "name": coin.get("name"),
                "price": q.get("price"),
                "pct24h": q.get("percent_change_24h"),
                "pct7d": q.get("percent_change_7d"),
                "mcap": q.get("market_cap"),
                "vol24h": q.get("volume_24h"),
                "updated": q.get("last_updated") or coin.get("last_updated")
            }
            self.rows_raw.append(row)

        self.apply_filter()

    def apply_filter(self):
        query = (self.search_var.get() or "").strip().lower()

        def matches(row):
            if not query:
                return True
            hay = f"{row['symbol']} {row['name']}".lower()
            return query in hay

        filtered = [r for r in self.rows_raw if matches(r)]

        # Sort using current state
        col, desc = self.current_sort
        filtered.sort(key=lambda r: (r[col] is None, r[col]), reverse=desc)

        # repopulate tree
        self.tree.delete(*self.tree.get_children())
        for r in filtered:
            # Tag for percentage columns (green/red)
            tag = "neu"
            try:
                if r["pct24h"] is not None:
                    tag = "pos" if r["pct24h"] >= 0 else "neg"
            except Exception:
                pass

            self.tree.insert(
                "", "end",
                values=(
                    r["rank"] if r["rank"] is not None else "",
                    r["symbol"] or "",
                    r["name"] or "",
                    fmt_price(r["price"]),
                    fmt_pct(r["pct24h"]),
                    fmt_pct(r["pct7d"]),
                    fmt_money(r["mcap"]) if r["mcap"] is not None else "-",
                    fmt_money(r["vol24h"]) if r["vol24h"] is not None else "-",
                    fmt_dt(r["updated"]),
                ),
                tags=(tag,)
            )

    def sort_by(self, col):
        # Toggle direction if same column, else ascending
        if col == self.current_sort[0]:
            desc = not self.current_sort[1]
        else:
            desc = False
        self.current_sort = (col, desc)
        self.apply_filter()

    def apply_auto_refresh(self):
        # Cancel previous schedule
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None

        # Schedule new if > 0
        try:
            ms = int(self.auto_var.get())
        except ValueError:
            ms = 0

        if ms > 0:
            def _tick():
                self.refresh()
                self._after_id = self.after(ms, _tick)
            self._after_id = self.after(ms, _tick)

# ===================== Main =====================
if __name__ == "__main__":
    app = App()
    app.mainloop()
