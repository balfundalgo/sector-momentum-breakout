"""
Sector Momentum Breakout Strategy — Tkinter GUI
"""

import sys
import os
import time
import threading
import traceback
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime

# ── path setup ──────────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    EXE_DIR    = os.path.dirname(sys.executable)
    SCRIPT_DIR = sys._MEIPASS
    sys.path.insert(0, EXE_DIR)
    sys.path.insert(0, SCRIPT_DIR)
else:
    EXE_DIR    = os.path.dirname(os.path.abspath(__file__))
    SCRIPT_DIR = EXE_DIR
    sys.path.insert(0, SCRIPT_DIR)

LOG_FILE = os.path.join(EXE_DIR, 'crash.log')

# ── colours ─────────────────────────────────────────────────────────────────
C_BG      = "#0d0d0d"
C_PANEL   = "#141414"
C_CARD    = "#1a1a1a"
C_BORDER  = "#2a2a2a"
C_GREEN   = "#00c87a"
C_RED     = "#ff4444"
C_YELLOW  = "#f5a623"
C_BLUE    = "#4a90d9"
C_TEXT    = "#e8e8e8"
C_MUTED   = "#666666"
C_WHITE   = "#ffffff"
C_ACCENT  = "#7c5cfc"

FONT_TITLE  = ("Helvetica", 14, "bold")
FONT_HEAD   = ("Helvetica", 11, "bold")
FONT_BODY   = ("Helvetica", 10)
FONT_SMALL  = ("Helvetica", 9)
FONT_MONO   = ("Courier", 9)


# ─────────────────────────────────────────────────────────────────────────────
# GUI-aware logger — redirects print() and log calls to the log panel
# ─────────────────────────────────────────────────────────────────────────────
class GUILogger:
    def __init__(self, text_widget: scrolledtext.ScrolledText):
        self._tw = text_widget
        self._tw.tag_configure("INFO",    foreground=C_TEXT)
        self._tw.tag_configure("SUCCESS", foreground=C_GREEN)
        self._tw.tag_configure("WARN",    foreground=C_YELLOW)
        self._tw.tag_configure("ERROR",   foreground=C_RED)
        self._tw.tag_configure("MUTED",   foreground=C_MUTED)
        self._tw.tag_configure("ACCENT",  foreground=C_ACCENT)
        self._lock = threading.Lock()

    def _tag(self, msg: str) -> str:
        m = msg.lower()
        if any(x in m for x in ["✅", "connected", "success", "executed", "subscribed"]):
            return "SUCCESS"
        if any(x in m for x in ["❌", "error", "failed", "fatal"]):
            return "ERROR"
        if any(x in m for x in ["⚠️", "warning", "retry", "backoff", "waiting"]):
            return "WARN"
        if any(x in m for x in ["📡", "🎯", "📈", "📉", "🏆", "⏰"]):
            return "ACCENT"
        return "INFO"

    def write(self, msg: str):
        if not msg.strip():
            return
        ts  = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg.rstrip()}\n"
        tag  = self._tag(msg)
        with self._lock:
            self._tw.configure(state='normal')
            self._tw.insert(tk.END, line, tag)
            self._tw.see(tk.END)
            self._tw.configure(state='disabled')

    def info(self, msg):    self.write(msg)
    def error(self, msg):   self.write(f"❌ {msg}")
    def warning(self, msg): self.write(f"⚠️ {msg}")
    def print_banner(self, msg): self.write(f"{'─'*40}\n  {msg}\n{'─'*40}")
    def flush(self): pass  # needed for sys.stdout redirect


# ─────────────────────────────────────────────────────────────────────────────
# Status card widget
# ─────────────────────────────────────────────────────────────────────────────
class StatusCard(tk.Frame):
    def __init__(self, parent, label: str, value: str = "—",
                 value_color: str = C_TEXT, **kw):
        super().__init__(parent, bg=C_CARD,
                         highlightbackground=C_BORDER, highlightthickness=1,
                         **kw)
        tk.Label(self, text=label, font=FONT_SMALL,
                 bg=C_CARD, fg=C_MUTED).pack(anchor='w', padx=10, pady=(8, 0))
        self._val = tk.Label(self, text=value, font=FONT_HEAD,
                             bg=C_CARD, fg=value_color)
        self._val.pack(anchor='w', padx=10, pady=(0, 8))

    def set(self, value: str, color: str = C_TEXT):
        self._val.config(text=value, fg=color)


# ─────────────────────────────────────────────────────────────────────────────
# Settings panel
# ─────────────────────────────────────────────────────────────────────────────
class SettingsPanel(tk.Toplevel):
    FIELDS = [
        ("API CREDENTIALS", None),
        ("CLIENT_ID",               "Client ID"),
        ("API_KEY",                 "API Key"),
        ("MPIN",                    "MPIN", True),
        ("TOTP_SECRET",             "TOTP Secret", True),
        ("STRATEGY PARAMETERS", None),
        ("ENTRY_CUTOFF",            "Entry Cutoff (HH:MM)"),
        ("FORCE_EXIT_TIME",         "Force Exit (HH:MM)"),
        ("MAX_TRADES_PER_DAY",      "Max Trades/Day"),
        ("LOTS_PER_TRADE",          "Lots Per Trade"),
        ("MAX_STOCK_MOVEMENT_PCT",  "Max Stock Move %"),
        ("TRAILING_TRIGGER_PCT",    "Trailing Trigger %"),
        ("RISK_REWARD_RATIO",       "Risk/Reward Ratio"),
    ]

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Settings")
        self.configure(bg=C_BG)
        self.resizable(False, False)
        self.grab_set()

        try:
            from settings_manager import get_settings, save_settings
            self._get = get_settings
            self._save = save_settings
        except ImportError:
            messagebox.showerror("Error", "settings_manager.py not found")
            self.destroy()
            return

        self._entries = {}
        self._build()

    def _build(self):
        tk.Label(self, text="⚙️  Settings", font=FONT_TITLE,
                 bg=C_BG, fg=C_WHITE).pack(pady=(16, 8), padx=20, anchor='w')

        frame = tk.Frame(self, bg=C_BG)
        frame.pack(fill='both', expand=True, padx=20, pady=8)

        s = self._get()
        row = 0
        for item in self.FIELDS:
            key   = item[0]
            label = item[1] if len(item) > 1 else None
            secret = item[2] if len(item) > 2 else False

            if label is None:
                # Section header
                tk.Label(frame, text=key, font=FONT_HEAD,
                         bg=C_BG, fg=C_ACCENT).grid(
                    row=row, column=0, columnspan=2,
                    sticky='w', pady=(14, 4))
                row += 1
                continue

            tk.Label(frame, text=label, font=FONT_BODY,
                     bg=C_BG, fg=C_MUTED, anchor='w', width=22).grid(
                row=row, column=0, sticky='w', pady=3)

            show = '*' if secret else None
            e = tk.Entry(frame, font=FONT_BODY, bg=C_CARD, fg=C_TEXT,
                         insertbackground=C_TEXT, relief='flat',
                         width=28, show=show,
                         highlightbackground=C_BORDER, highlightthickness=1)
            e.insert(0, s.get(key, ''))
            e.grid(row=row, column=1, sticky='ew', padx=(8, 0), pady=3)
            self._entries[key] = e
            row += 1

        # Buttons
        btn_frame = tk.Frame(self, bg=C_BG)
        btn_frame.pack(fill='x', padx=20, pady=16)

        tk.Button(btn_frame, text="Save", font=FONT_BODY,
                  bg=C_GREEN, fg=C_BG, relief='flat',
                  padx=20, pady=6, cursor='hand2',
                  command=self._save_click).pack(side='left')

        tk.Button(btn_frame, text="Cancel", font=FONT_BODY,
                  bg=C_CARD, fg=C_TEXT, relief='flat',
                  padx=20, pady=6, cursor='hand2',
                  command=self.destroy).pack(side='left', padx=(8, 0))

    def _save_click(self):
        updates = {k: e.get().strip() for k, e in self._entries.items()}
        self._save(updates)
        messagebox.showinfo("Saved", "Settings saved successfully!")
        self.destroy()


# ─────────────────────────────────────────────────────────────────────────────
# Main application window
# ─────────────────────────────────────────────────────────────────────────────
class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Sector Momentum Breakout Strategy")
        self.configure(bg=C_BG)
        self.geometry("1000x700")
        self.minsize(860, 600)

        self._strategy_thread: threading.Thread = None
        self._running = False
        self._stop_event = threading.Event()

        self._build_ui()
        self._check_credentials_on_start()

    # ── UI construction ───────────────────────────────────────────────────
    def _build_ui(self):
        # ── top bar ──
        topbar = tk.Frame(self, bg=C_PANEL, height=52)
        topbar.pack(fill='x')
        topbar.pack_propagate(False)

        tk.Label(topbar, text="📈  Sector Momentum Breakout",
                 font=FONT_TITLE, bg=C_PANEL, fg=C_WHITE).pack(
            side='left', padx=16, pady=12)

        tk.Button(topbar, text="⚙️  Settings", font=FONT_BODY,
                  bg=C_CARD, fg=C_TEXT, relief='flat',
                  padx=12, pady=4, cursor='hand2',
                  command=self._open_settings).pack(side='right', padx=12, pady=10)

        # ── body ──
        body = tk.Frame(self, bg=C_BG)
        body.pack(fill='both', expand=True, padx=12, pady=12)

        # left column
        left = tk.Frame(body, bg=C_BG, width=220)
        left.pack(side='left', fill='y', padx=(0, 10))
        left.pack_propagate(False)
        self._build_left(left)

        # right column
        right = tk.Frame(body, bg=C_BG)
        right.pack(side='left', fill='both', expand=True)
        self._build_right(right)

    def _build_left(self, parent):
        # Status cards
        tk.Label(parent, text="STATUS", font=FONT_SMALL,
                 bg=C_BG, fg=C_MUTED).pack(anchor='w', pady=(0, 4))

        self._card_status = StatusCard(parent, "Strategy")
        self._card_status.pack(fill='x', pady=2)

        self._card_mode = StatusCard(parent, "Mode")
        self._card_mode.pack(fill='x', pady=2)

        self._card_trend = StatusCard(parent, "Market Trend")
        self._card_trend.pack(fill='x', pady=2)

        self._card_sector = StatusCard(parent, "Selected Sector")
        self._card_sector.pack(fill='x', pady=2)

        self._card_stock = StatusCard(parent, "Selected Stock")
        self._card_stock.pack(fill='x', pady=2)

        self._card_trades = StatusCard(parent, "Trades Today")
        self._card_trades.pack(fill='x', pady=2)

        self._card_trades.set("0 / 2")

        # Spacer
        tk.Frame(parent, bg=C_BG, height=10).pack()

        # Mode toggle
        tk.Label(parent, text="TRADING MODE", font=FONT_SMALL,
                 bg=C_BG, fg=C_MUTED).pack(anchor='w', pady=(8, 4))

        mode_frame = tk.Frame(parent, bg=C_CARD,
                              highlightbackground=C_BORDER, highlightthickness=1)
        mode_frame.pack(fill='x', pady=2)

        self._live_var = tk.BooleanVar(value=False)
        tk.Radiobutton(mode_frame, text="  Paper Trading",
                       variable=self._live_var, value=False,
                       font=FONT_BODY, bg=C_CARD, fg=C_GREEN,
                       selectcolor=C_CARD, activebackground=C_CARD).pack(
            anchor='w', padx=10, pady=4)
        tk.Radiobutton(mode_frame, text="  Live Trading",
                       variable=self._live_var, value=True,
                       font=FONT_BODY, bg=C_CARD, fg=C_RED,
                       selectcolor=C_CARD, activebackground=C_CARD).pack(
            anchor='w', padx=10, pady=4)

        # Trend override
        tk.Label(parent, text="TREND OVERRIDE", font=FONT_SMALL,
                 bg=C_BG, fg=C_MUTED).pack(anchor='w', pady=(12, 4))

        trend_frame = tk.Frame(parent, bg=C_CARD,
                               highlightbackground=C_BORDER, highlightthickness=1)
        trend_frame.pack(fill='x', pady=2)

        self._trend_var = tk.StringVar(value="AUTO")
        for t in ["AUTO", "BULLISH", "BEARISH"]:
            color = C_TEXT if t == "AUTO" else (C_GREEN if t == "BULLISH" else C_RED)
            tk.Radiobutton(trend_frame, text=f"  {t}",
                           variable=self._trend_var, value=t,
                           font=FONT_BODY, bg=C_CARD, fg=color,
                           selectcolor=C_CARD, activebackground=C_CARD).pack(
                anchor='w', padx=10, pady=2)

        # Start / Stop buttons
        tk.Frame(parent, bg=C_BG).pack(fill='y', expand=True)

        self._btn_start = tk.Button(parent, text="▶  START STRATEGY",
                                    font=FONT_HEAD,
                                    bg=C_GREEN, fg=C_BG,
                                    relief='flat', padx=10, pady=10,
                                    cursor='hand2',
                                    command=self._start_strategy)
        self._btn_start.pack(fill='x', pady=(4, 2))

        self._btn_stop = tk.Button(parent, text="⏹  STOP",
                                   font=FONT_HEAD,
                                   bg=C_RED, fg=C_WHITE,
                                   relief='flat', padx=10, pady=10,
                                   cursor='hand2', state='disabled',
                                   command=self._stop_strategy)
        self._btn_stop.pack(fill='x', pady=2)

        tk.Button(parent, text="🗑  Clear Log",
                  font=FONT_SMALL, bg=C_CARD, fg=C_MUTED,
                  relief='flat', pady=4, cursor='hand2',
                  command=self._clear_log).pack(fill='x', pady=(6, 0))

    def _build_right(self, parent):
        tk.Label(parent, text="ACTIVITY LOG", font=FONT_SMALL,
                 bg=C_BG, fg=C_MUTED).pack(anchor='w', pady=(0, 4))

        self._log_box = scrolledtext.ScrolledText(
            parent,
            font=FONT_MONO,
            bg=C_CARD, fg=C_TEXT,
            insertbackground=C_TEXT,
            relief='flat',
            state='disabled',
            wrap='word',
            highlightbackground=C_BORDER,
            highlightthickness=1
        )
        self._log_box.pack(fill='both', expand=True)

        self._gui_logger = GUILogger(self._log_box)

        # Status bar
        self._statusbar = tk.Label(parent, text="Ready",
                                   font=FONT_SMALL, bg=C_PANEL,
                                   fg=C_MUTED, anchor='w')
        self._statusbar.pack(fill='x', pady=(4, 0))

    # ── helpers ───────────────────────────────────────────────────────────
    def _log(self, msg: str):
        self._gui_logger.write(msg)

    def _set_status(self, msg: str):
        self._statusbar.config(text=msg)

    def _clear_log(self):
        self._log_box.configure(state='normal')
        self._log_box.delete('1.0', tk.END)
        self._log_box.configure(state='disabled')

    def _open_settings(self):
        SettingsPanel(self)

    def _check_credentials_on_start(self):
        try:
            from settings_manager import credentials_are_default
            if credentials_are_default():
                self._log("⚠️  Credentials not set — please open Settings first.")
                self.after(500, self._open_settings)
        except ImportError:
            pass

    def _update_card(self, card: StatusCard, value: str, color: str = C_TEXT):
        self.after(0, lambda: card.set(value, color))

    # ── strategy control ──────────────────────────────────────────────────
    def _start_strategy(self):
        if self._running:
            return

        live = self._live_var.get()
        if live:
            if not messagebox.askyesno(
                "⚠️  Live Trading",
                "You are about to enable LIVE trading.\nReal orders WILL be placed.\n\nAre you sure?"
            ):
                return

        self._running = True
        self._stop_event.clear()
        self._btn_start.config(state='disabled')
        self._btn_stop.config(state='normal')

        trend_choice = self._trend_var.get()
        force_trend  = None if trend_choice == "AUTO" else trend_choice

        mode_str = "LIVE" if live else "PAPER"
        self._update_card(self._card_status, "● RUNNING", C_GREEN)
        self._update_card(self._card_mode, mode_str, C_RED if live else C_GREEN)
        self._set_status("Strategy running...")
        self._log(f"{'='*50}")
        self._log(f"Starting strategy | Mode: {mode_str} | Trend: {trend_choice}")
        self._log(f"{'='*50}")

        self._strategy_thread = threading.Thread(
            target=self._run_strategy,
            args=(not live, force_trend),
            daemon=True
        )
        self._strategy_thread.start()

    def _stop_strategy(self):
        self._stop_event.set()
        self._log("🛑 Stop requested — finishing current operation...")
        self._set_status("Stopping...")

    def _on_strategy_done(self, trade_count: int):
        self._running = False
        self._btn_start.config(state='normal')
        self._btn_stop.config(state='disabled')
        self._update_card(self._card_status, "● STOPPED", C_MUTED)
        self._update_card(self._card_trades, f"{trade_count} / 2")
        self._set_status(f"Strategy ended — {trade_count} trade(s) today")
        self._log(f"Strategy ended. Total trades: {trade_count}")

    def _run_strategy(self, paper_trading: bool, force_trend):
        """Runs in a background thread."""
        trade_count = 0
        try:
            # Import here (inside thread) so errors show in GUI log
            from config import MAX_TRADES_PER_DAY, ENTRY_CUTOFF
            from angel_api import get_api
            from data_fetcher import DataFetcher
            from trend_identifier import TrendIdentifier
            from sector_scanner import SectorScanner
            from stock_selector import StockSelector
            from entry_monitor import EntryMonitor
            from order_executor import OrderExecutor
            from position_monitor import PositionMonitor

            # Redirect stdout to GUI log
            sys.stdout = self._gui_logger

            self._log("📡 Connecting to Angel One API...")
            api = get_api()
            if not api:
                self._log("❌ Failed to create API instance — check credentials in Settings")
                return

            if not api.is_connected:
                if not api.connect():
                    self._log("❌ API connection failed — check credentials in Settings")
                    return

            self._log("✅ API connected")

            # Subscribe sector indices
            from config import SECTORAL_INDICES
            if api.ws_manager:
                symbols = [{'exchange': 'NSE', 'token': '99926000'}]
                for _, (sym, tok, exch) in SECTORAL_INDICES.items():
                    symbols.append({'exchange': exch, 'token': tok})
                if api.subscribe_symbols(symbols):
                    self._log(f"✅ Subscribed to {len(symbols)} indices via WebSocket")
                time.sleep(2)

            data_fetcher     = DataFetcher(api)
            trend_id         = TrendIdentifier(api, self._gui_logger)
            sector_scanner   = SectorScanner(api, self._gui_logger)
            stock_selector   = StockSelector(api, data_fetcher, self._gui_logger)
            entry_monitor    = EntryMonitor(api, data_fetcher, self._gui_logger)
            order_executor   = OrderExecutor(api, data_fetcher, self._gui_logger)
            position_monitor = PositionMonitor(api, data_fetcher,
                                               order_executor, self._gui_logger)

            # Trend
            if force_trend:
                trend = force_trend
                self._log(f"🎯 Forced trend: {trend}")
            else:
                trend = trend_id.identify_trend()

            if not trend:
                self._log("❌ Could not identify market trend")
                return

            self._update_card(self._card_trend,
                              trend,
                              C_GREEN if trend == "BULLISH" else C_RED)

            # Sector scan
            sector_scanner.scan_all_sectors()
            sector_scanner.display_sector_ranking()

            selected_sector = None
            selected_stock  = None

            while trade_count < MAX_TRADES_PER_DAY and not self._stop_event.is_set():
                now = datetime.now()
                cutoff = datetime.strptime(ENTRY_CUTOFF, "%H:%M").time()
                if now.time() >= cutoff:
                    self._log("⏰ Entry cutoff reached — no more entries")
                    break

                if not selected_sector:
                    selected_sector = sector_scanner.select_sector_for_trend(trend)
                if not selected_sector:
                    self._log("❌ Could not select sector")
                    break

                self._update_card(self._card_sector,
                                  selected_sector.get('name', '—'), C_BLUE)

                selected_stock = stock_selector.select_best_stock(
                    selected_sector['name'], trend)

                if not selected_stock:
                    self._log("⚠️ No suitable stock found")
                    break

                self._update_card(self._card_stock,
                                  selected_stock.get('symbol', '—'), C_TEXT)

                # Subscribe stock
                if api.ws_manager:
                    api.subscribe_symbols([{
                        'exchange': selected_stock.get('exchange', 'NSE'),
                        'token':    selected_stock['token']
                    }])
                    time.sleep(1)

                if not entry_monitor.setup(selected_stock, trend):
                    self._log("❌ Entry monitor setup failed")
                    break

                entry_data = entry_monitor.monitor_for_entry()

                if self._stop_event.is_set():
                    break

                if entry_data:
                    result = order_executor.execute_entry(
                        selected_stock, trend,
                        entry_data['entry_price'], entry_data['stop_loss']
                    )
                    if result:
                        trade_count += 1
                        self._update_card(self._card_trades,
                                          f"{trade_count} / {MAX_TRADES_PER_DAY}",
                                          C_GREEN)
                        self._log(f"✅ Trade {trade_count} executed!")
                        position_monitor.start_monitoring()
                        selected_sector = None
                        selected_stock  = None
                    else:
                        self._log("⚠️ Order execution failed")
                        break
                else:
                    self._log("📊 Entry conditions not met")
                    break

            if api.ws_manager:
                api.ws_manager.disconnect()

        except Exception as e:
            err = f"Strategy error: {e}\n{traceback.format_exc()}"
            self._log(f"❌ {err}")
            try:
                with open(LOG_FILE, 'a') as f:
                    f.write(f"\n[{datetime.now()}] {err}\n")
            except Exception:
                pass
        finally:
            try:
                sys.stdout = sys.__stdout__
            except Exception:
                pass
            self.after(0, self._on_strategy_done, trade_count)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
