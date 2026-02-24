"""
Sector Momentum Breakout Strategy — GUI (Light Theme)
"""

import sys
import os
import csv
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

# ── Light colour palette ────────────────────────────────────────────────────
C_BG        = "#f4f6f9"
C_PANEL     = "#ffffff"
C_CARD      = "#ffffff"
C_SIDEBAR   = "#1e2a3a"
C_SIDEBAR2  = "#253447"
C_BORDER    = "#dde3ec"
C_GREEN     = "#1a8a5a"
C_GREEN_BG  = "#e6f7f0"
C_RED       = "#d93025"
C_RED_BG    = "#fdecea"
C_BLUE      = "#1a6fd4"
C_BLUE_BG   = "#e8f0fd"
C_YELLOW    = "#b06000"
C_YELLOW_BG = "#fff8e6"
C_TEXT      = "#1a1a2e"
C_MUTED     = "#7a8899"
C_WHITE     = "#ffffff"
C_ACCENT    = "#1a6fd4"
C_BTN_START = "#1a8a5a"
C_BTN_STOP  = "#d93025"
C_HEADER    = "#f0f3f8"

FONT_TITLE  = ("Helvetica", 13, "bold")
FONT_HEAD   = ("Helvetica", 10, "bold")
FONT_BODY   = ("Helvetica", 10)
FONT_SMALL  = ("Helvetica", 9)
FONT_MONO   = ("Courier", 9)


# ─────────────────────────────────────────────────────────────────────────────
# GUI Logger — implements ALL methods used by strategy modules
# ─────────────────────────────────────────────────────────────────────────────
class GUILogger:
    """Drop-in replacement for StrategyLogger — writes everything to the GUI log panel."""

    def __init__(self, text_widget: scrolledtext.ScrolledText):
        self._tw   = text_widget
        self._lock = threading.Lock()
        self._today = datetime.now().strftime("%Y-%m-%d")
        self._log_dir = EXE_DIR

        # CSV trade log (same format as StrategyLogger)
        self.trade_log_file = os.path.join(
            EXE_DIR, f"trades_{self._today}.csv")
        self._init_trade_log()

        # Tag colours
        self._tw.tag_configure("INFO",    foreground="#1a1a2e", font=FONT_MONO)
        self._tw.tag_configure("SUCCESS", foreground=C_GREEN,   font=FONT_MONO)
        self._tw.tag_configure("WARN",    foreground=C_YELLOW,  font=FONT_MONO)
        self._tw.tag_configure("ERROR",   foreground=C_RED,     font=FONT_MONO)
        self._tw.tag_configure("MUTED",   foreground=C_MUTED,   font=FONT_MONO)
        self._tw.tag_configure("ACCENT",  foreground=C_BLUE,    font=FONT_MONO)
        self._tw.tag_configure("BANNER",  foreground=C_ACCENT,  font=("Courier", 9, "bold"))

    def _init_trade_log(self):
        if not os.path.exists(self.trade_log_file):
            try:
                with open(self.trade_log_file, 'w', newline='') as f:
                    csv.writer(f).writerow([
                        'timestamp','trade_id','symbol','trade_type','direction',
                        'entry_price','stop_loss','take_profit','quantity',
                        'option_symbol','option_entry_price','option_quantity',
                        'future_symbol','future_entry_price','future_quantity',
                        'exit_price','exit_time','exit_reason','pnl','status'
                    ])
            except Exception:
                pass

    def _tag(self, msg: str) -> str:
        m = msg.lower()
        if any(x in m for x in ["✅", "success", "connected", "executed", "subscribed"]):
            return "SUCCESS"
        if any(x in m for x in ["❌", "error", "failed", "fatal"]):
            return "ERROR"
        if any(x in m for x in ["⚠️", "warning", "retry", "backoff", "waiting", "⏳"]):
            return "WARN"
        if "═" in msg or "║" in msg or "╔" in msg or "╚" in msg:
            return "BANNER"
        if any(x in m for x in ["📡", "🎯", "📈", "📉", "🏆", "⏰", "🔴", "🟢"]):
            return "ACCENT"
        return "INFO"

    def _write(self, msg: str, tag: str = None):
        if not msg.strip():
            return
        ts   = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg.rstrip()}\n"
        tag  = tag or self._tag(msg)
        with self._lock:
            self._tw.configure(state='normal')
            self._tw.insert(tk.END, line, tag)
            self._tw.see(tk.END)
            self._tw.configure(state='disabled')

    # ── Standard log methods ──────────────────────────────────────────────
    def write(self, msg: str):   self._write(msg)
    def flush(self):             pass   # for sys.stdout redirect
    def debug(self, msg: str):   self._write(f"[DEBUG] {msg}", "MUTED")
    def info(self, msg: str):    self._write(msg)
    def warning(self, msg: str): self._write(f"⚠️  {msg}", "WARN")
    def error(self, msg: str):   self._write(f"❌ {msg}", "ERROR")

    def print_banner(self, msg: str):
        self._write(f"{'─'*48}", "BANNER")
        self._write(f"  {msg}", "BANNER")
        self._write(f"{'─'*48}", "BANNER")

    # ── Extended methods (used by strategy modules) ───────────────────────
    def log_event(self, event_type: str, details: dict):
        """Log a strategy event to CSV and GUI."""
        # Write to GUI
        detail_str = ", ".join(f"{k}={v}" for k, v in details.items())
        self._write(f"📋 [{event_type}] {detail_str}", "ACCENT")

        # Write to CSV
        event_file = os.path.join(self._log_dir, f"events_{self._today}.csv")
        try:
            write_header = not os.path.exists(event_file)
            with open(event_file, 'a', newline='') as f:
                w = csv.writer(f)
                if write_header:
                    w.writerow(['timestamp', 'event_type', 'details'])
                w.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            event_type, str(details)])
        except Exception:
            pass

    def log_trade_entry(self, trade: dict):
        """Log trade entry to CSV and GUI."""
        self._write(
            f"📝 Trade Entry: {trade.get('symbol')} "
            f"{trade.get('direction')} @ {trade.get('entry_price')} "
            f"SL={trade.get('stop_loss')} TP={trade.get('take_profit')}",
            "SUCCESS"
        )
        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            trade.get('trade_id', ''),
            trade.get('symbol', ''),
            trade.get('trade_type', ''),
            trade.get('direction', ''),
            trade.get('entry_price', 0),
            trade.get('stop_loss', 0),
            trade.get('take_profit', 0),
            trade.get('quantity', 0),
            trade.get('option_symbol', ''),
            trade.get('option_entry_price', 0),
            trade.get('option_quantity', 0),
            trade.get('future_symbol', ''),
            trade.get('future_entry_price', 0),
            trade.get('future_quantity', 0),
            '', '', '', '', 'OPEN'
        ]
        try:
            with open(self.trade_log_file, 'a', newline='') as f:
                csv.writer(f).writerow(row)
        except Exception:
            pass

    def log_trade_exit(self, trade_id: str, exit_price: float,
                       exit_reason: str, pnl: float):
        """Log trade exit and update CSV."""
        color = "SUCCESS" if pnl >= 0 else "ERROR"
        self._write(
            f"📝 Trade Exit: {trade_id} | Reason={exit_reason} "
            f"ExitPrice={exit_price} PnL={pnl:+.2f}",
            color
        )
        try:
            rows = []
            with open(self.trade_log_file, 'r') as f:
                rows = list(csv.reader(f))
            if len(rows) > 1:
                headers = rows[0]
                for i, row in enumerate(rows[1:], 1):
                    if row[headers.index('trade_id')] == trade_id:
                        rows[i][headers.index('exit_price')]  = exit_price
                        rows[i][headers.index('exit_time')]   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        rows[i][headers.index('exit_reason')] = exit_reason
                        rows[i][headers.index('pnl')]         = pnl
                        rows[i][headers.index('status')]      = 'CLOSED'
                        break
                with open(self.trade_log_file, 'w', newline='') as f:
                    csv.writer(f).writerows(rows)
        except Exception:
            pass

    def get_daily_summary(self) -> dict:
        try:
            with open(self.trade_log_file, 'r') as f:
                rows = list(csv.DictReader(f))
            total  = len(rows)
            closed = [r for r in rows if r.get('status') == 'CLOSED']
            pnl    = sum(float(r.get('pnl', 0) or 0) for r in closed)
            return {'total_trades': total, 'closed_trades': len(closed),
                    'open_trades': total - len(closed), 'total_pnl': pnl}
        except Exception:
            return {'total_trades': 0, 'open_trades': 0,
                    'closed_trades': 0, 'total_pnl': 0}


# ─────────────────────────────────────────────────────────────────────────────
# Status card
# ─────────────────────────────────────────────────────────────────────────────
class StatusCard(tk.Frame):
    def __init__(self, parent, label: str, value: str = "—",
                 value_color: str = C_TEXT, **kw):
        super().__init__(parent, bg=C_CARD,
                         highlightbackground=C_BORDER,
                         highlightthickness=1, **kw)
        tk.Label(self, text=label.upper(), font=("Helvetica", 8, "bold"),
                 bg=C_CARD, fg=C_MUTED).pack(anchor='w', padx=10, pady=(8, 0))
        self._val = tk.Label(self, text=value, font=FONT_HEAD,
                             bg=C_CARD, fg=value_color)
        self._val.pack(anchor='w', padx=10, pady=(2, 8))

    def set(self, value: str, color: str = C_TEXT):
        self._val.config(text=value, fg=color)


# ─────────────────────────────────────────────────────────────────────────────
# Settings panel (light)
# ─────────────────────────────────────────────────────────────────────────────
class SettingsPanel(tk.Toplevel):
    FIELDS = [
        ("API CREDENTIALS", None),
        ("CLIENT_ID",               "Client ID",         False),
        ("API_KEY",                 "API Key",            False),
        ("MPIN",                    "MPIN",               True),
        ("TOTP_SECRET",             "TOTP Secret",        True),
        ("STRATEGY PARAMETERS", None),
        ("ENTRY_CUTOFF",            "Entry Cutoff HH:MM", False),
        ("FORCE_EXIT_TIME",         "Force Exit HH:MM",   False),
        ("MAX_TRADES_PER_DAY",      "Max Trades/Day",     False),
        ("LOTS_PER_TRADE",          "Lots Per Trade",     False),
        ("MAX_STOCK_MOVEMENT_PCT",  "Max Stock Move %",   False),
        ("TRAILING_TRIGGER_PCT",    "Trailing Trigger %", False),
        ("RISK_REWARD_RATIO",       "Risk/Reward Ratio",  False),
    ]

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Settings")
        self.configure(bg=C_BG)
        self.resizable(False, False)
        self.grab_set()

        try:
            from settings_manager import get_settings, save_settings
            self._get  = get_settings
            self._save = save_settings
        except ImportError:
            messagebox.showerror("Error", "settings_manager.py not found")
            self.destroy()
            return

        self._entries = {}
        self._build()

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=C_SIDEBAR, height=48)
        hdr.pack(fill='x')
        hdr.pack_propagate(False)
        tk.Label(hdr, text="⚙️   Settings", font=FONT_TITLE,
                 bg=C_SIDEBAR, fg=C_WHITE).pack(side='left', padx=16, pady=10)

        frame = tk.Frame(self, bg=C_BG)
        frame.pack(fill='both', expand=True, padx=24, pady=16)

        s   = self._get()
        row = 0
        for item in self.FIELDS:
            key    = item[0]
            label  = item[1]
            secret = item[2] if len(item) > 2 else False

            if label is None:
                tk.Label(frame, text=key, font=("Helvetica", 9, "bold"),
                         bg=C_BG, fg=C_ACCENT).grid(
                    row=row, column=0, columnspan=2,
                    sticky='w', pady=(16, 4))
                row += 1
                continue

            tk.Label(frame, text=label, font=FONT_BODY,
                     bg=C_BG, fg=C_TEXT, anchor='w', width=22).grid(
                row=row, column=0, sticky='w', pady=4)

            e = tk.Entry(frame, font=FONT_BODY,
                         bg=C_WHITE, fg=C_TEXT,
                         relief='solid', bd=1,
                         width=30,
                         show='●' if secret else '')
            e.insert(0, s.get(key, ''))
            e.grid(row=row, column=1, sticky='ew', padx=(8, 0), pady=4)
            self._entries[key] = e
            row += 1

        # Buttons
        btn_f = tk.Frame(self, bg=C_BG)
        btn_f.pack(fill='x', padx=24, pady=(0, 20))

        tk.Button(btn_f, text="  Save Settings  ", font=FONT_HEAD,
                  bg=C_BTN_START, fg=C_WHITE, relief='flat',
                  padx=16, pady=8, cursor='hand2',
                  command=self._save_click).pack(side='left')

        tk.Button(btn_f, text="  Cancel  ", font=FONT_BODY,
                  bg=C_BORDER, fg=C_TEXT, relief='flat',
                  padx=16, pady=8, cursor='hand2',
                  command=self.destroy).pack(side='left', padx=(8, 0))

    def _save_click(self):
        updates = {k: e.get().strip() for k, e in self._entries.items()}
        self._save(updates)
        messagebox.showinfo("Saved", "✅ Settings saved successfully!")
        self.destroy()


# ─────────────────────────────────────────────────────────────────────────────
# Main window
# ─────────────────────────────────────────────────────────────────────────────
class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Sector Momentum Breakout Strategy")
        self.configure(bg=C_BG)
        self.geometry("1060x680")
        self.minsize(900, 580)

        self._running     = False
        self._stop_event  = threading.Event()
        self._strat_thread: threading.Thread = None

        self._build_ui()
        self._check_credentials()

    # ── UI ────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # Top nav bar
        nav = tk.Frame(self, bg=C_SIDEBAR, height=52)
        nav.pack(fill='x')
        nav.pack_propagate(False)

        tk.Label(nav, text="📈  Sector Momentum Breakout Strategy",
                 font=FONT_TITLE, bg=C_SIDEBAR, fg=C_WHITE).pack(
            side='left', padx=20, pady=12)

        tk.Button(nav, text="⚙️  Settings", font=FONT_SMALL,
                  bg=C_SIDEBAR2, fg=C_WHITE, relief='flat',
                  padx=14, pady=6, cursor='hand2',
                  command=self._open_settings).pack(side='right', padx=14, pady=10)

        # Body
        body = tk.Frame(self, bg=C_BG)
        body.pack(fill='both', expand=True)

        # Left sidebar (dark)
        sidebar = tk.Frame(body, bg=C_SIDEBAR, width=220)
        sidebar.pack(side='left', fill='y')
        sidebar.pack_propagate(False)
        self._build_sidebar(sidebar)

        # Right content
        content = tk.Frame(body, bg=C_BG)
        content.pack(side='left', fill='both', expand=True, padx=14, pady=14)
        self._build_content(content)

    def _build_sidebar(self, parent):
        # Status section
        self._sidebar_label("STATUS", parent)

        self._card_status = self._sidebar_card(parent, "Strategy", "● Idle", C_MUTED)
        self._card_mode   = self._sidebar_card(parent, "Mode",     "—")
        self._card_trend  = self._sidebar_card(parent, "Trend",    "—")
        self._card_sector = self._sidebar_card(parent, "Sector",   "—")
        self._card_stock  = self._sidebar_card(parent, "Stock",    "—")
        self._card_trades = self._sidebar_card(parent, "Trades",   "0 / 2")

        # Mode
        self._sidebar_label("TRADING MODE", parent, top=14)
        mode_f = tk.Frame(parent, bg=C_SIDEBAR2)
        mode_f.pack(fill='x', padx=10, pady=2)
        self._live_var = tk.BooleanVar(value=False)
        for text, val, col in [("Paper Trading", False, "#4caf8a"),
                                ("Live Trading",  True,  "#e57373")]:
            tk.Radiobutton(mode_f, text=f"  {text}",
                           variable=self._live_var, value=val,
                           font=FONT_SMALL, bg=C_SIDEBAR2, fg=col,
                           selectcolor=C_SIDEBAR2,
                           activebackground=C_SIDEBAR2).pack(
                anchor='w', padx=10, pady=4)

        # Trend override
        self._sidebar_label("TREND OVERRIDE", parent, top=10)
        trend_f = tk.Frame(parent, bg=C_SIDEBAR2)
        trend_f.pack(fill='x', padx=10, pady=2)
        self._trend_var = tk.StringVar(value="AUTO")
        for text, col in [("AUTO", "#aaaaaa"), ("BULLISH", "#4caf8a"), ("BEARISH", "#e57373")]:
            tk.Radiobutton(trend_f, text=f"  {text}",
                           variable=self._trend_var, value=text,
                           font=FONT_SMALL, bg=C_SIDEBAR2, fg=col,
                           selectcolor=C_SIDEBAR2,
                           activebackground=C_SIDEBAR2).pack(
                anchor='w', padx=10, pady=3)

        # Push buttons to bottom
        tk.Frame(parent, bg=C_SIDEBAR).pack(fill='y', expand=True)

        self._btn_start = tk.Button(parent, text="▶  START",
                                    font=FONT_HEAD,
                                    bg="#1a8a5a", fg=C_WHITE,
                                    relief='flat', pady=10,
                                    cursor='hand2',
                                    command=self._start)
        self._btn_start.pack(fill='x', padx=10, pady=(2, 3))

        self._btn_stop = tk.Button(parent, text="⏹  STOP",
                                   font=FONT_HEAD,
                                   bg="#c0392b", fg=C_WHITE,
                                   relief='flat', pady=10,
                                   cursor='hand2', state='disabled',
                                   command=self._stop)
        self._btn_stop.pack(fill='x', padx=10, pady=(0, 3))

        tk.Button(parent, text="🗑  Clear Log",
                  font=FONT_SMALL, bg=C_SIDEBAR, fg=C_MUTED,
                  relief='flat', pady=4, cursor='hand2',
                  command=self._clear_log).pack(fill='x', padx=10, pady=(0, 10))

    def _sidebar_label(self, text, parent, top=8):
        tk.Label(parent, text=text, font=("Helvetica", 8, "bold"),
                 bg=C_SIDEBAR, fg="#6b8099").pack(
            anchor='w', padx=14, pady=(top, 2))

    def _sidebar_card(self, parent, label, value="—", color=C_WHITE):
        f = tk.Frame(parent, bg=C_SIDEBAR2)
        f.pack(fill='x', padx=10, pady=2)
        tk.Label(f, text=label, font=("Helvetica", 8),
                 bg=C_SIDEBAR2, fg="#6b8099").pack(anchor='w', padx=10, pady=(6, 0))
        lbl = tk.Label(f, text=value, font=FONT_HEAD,
                       bg=C_SIDEBAR2, fg=color)
        lbl.pack(anchor='w', padx=10, pady=(0, 6))

        # Return a simple object with .set()
        class _Card:
            def set(self_, v, c=C_WHITE):
                lbl.config(text=v, fg=c)
        return _Card()

    def _build_content(self, parent):
        # Header row
        hdr = tk.Frame(parent, bg=C_BG)
        hdr.pack(fill='x', pady=(0, 10))
        tk.Label(hdr, text="Activity Log", font=FONT_TITLE,
                 bg=C_BG, fg=C_TEXT).pack(side='left')

        # Log panel (white card)
        log_card = tk.Frame(parent, bg=C_PANEL,
                            highlightbackground=C_BORDER,
                            highlightthickness=1)
        log_card.pack(fill='both', expand=True)

        # Toolbar inside log card
        toolbar = tk.Frame(log_card, bg=C_HEADER)
        toolbar.pack(fill='x')
        tk.Label(toolbar, text="  Console Output",
                 font=FONT_SMALL, bg=C_HEADER, fg=C_MUTED).pack(side='left', padx=4, pady=4)

        self._log_box = scrolledtext.ScrolledText(
            log_card,
            font=FONT_MONO,
            bg=C_WHITE, fg=C_TEXT,
            relief='flat',
            state='disabled',
            wrap='word',
            padx=10, pady=8
        )
        self._log_box.pack(fill='both', expand=True)
        self._gui_logger = GUILogger(self._log_box)

        # Status bar
        self._statusbar = tk.Label(parent, text="Ready — configure credentials in Settings",
                                   font=FONT_SMALL, bg=C_BORDER,
                                   fg=C_MUTED, anchor='w', padx=8)
        self._statusbar.pack(fill='x', pady=(6, 0))

    # ── helpers ───────────────────────────────────────────────────────────
    def _log(self, msg):        self._gui_logger.write(msg)
    def _clear_log(self):
        self._log_box.configure(state='normal')
        self._log_box.delete('1.0', tk.END)
        self._log_box.configure(state='disabled')
    def _set_status(self, msg): self._statusbar.config(text=f"  {msg}")
    def _open_settings(self):   SettingsPanel(self)
    def _card(self, card, val, col=C_WHITE):
        self.after(0, lambda: card.set(val, col))

    def _check_credentials(self):
        try:
            from settings_manager import credentials_are_default
            if credentials_are_default():
                self._log("⚠️  Credentials not set — opening Settings...")
                self.after(600, self._open_settings)
        except ImportError:
            pass

    # ── strategy control ──────────────────────────────────────────────────
    def _start(self):
        if self._running:
            return
        live = self._live_var.get()
        if live and not messagebox.askyesno(
            "⚠️  Live Trading",
            "LIVE mode will place REAL orders.\n\nAre you sure?"
        ):
            return

        self._running = True
        self._stop_event.clear()
        self._btn_start.config(state='disabled')
        self._btn_stop.config(state='normal')

        force_trend = self._trend_var.get()
        if force_trend == "AUTO":
            force_trend = None

        mode = "LIVE" if live else "PAPER"
        self._card(self._card_status, "● RUNNING", "#4caf8a")
        self._card(self._card_mode,   mode, "#e57373" if live else "#4caf8a")
        self._set_status(f"Strategy running in {mode} mode...")
        self._log("=" * 50)
        self._log(f"Starting | Mode: {mode} | Trend: {self._trend_var.get()}")
        self._log("=" * 50)

        self._strat_thread = threading.Thread(
            target=self._run, args=(not live, force_trend), daemon=True)
        self._strat_thread.start()

    def _stop(self):
        self._stop_event.set()
        self._log("🛑 Stop requested...")
        self._set_status("Stopping...")

    def _done(self, trade_count):
        self._running = False
        self._btn_start.config(state='normal')
        self._btn_stop.config(state='disabled')
        self._card(self._card_status, "● Stopped", C_MUTED)
        self._card(self._card_trades, f"{trade_count} / 2")
        self._set_status(f"Strategy ended — {trade_count} trade(s) today")

    # ── background strategy thread ────────────────────────────────────────
    def _run(self, paper_trading: bool, force_trend):
        trade_count = 0
        try:
            from config import MAX_TRADES_PER_DAY, ENTRY_CUTOFF, SECTORAL_INDICES
            from angel_api import get_api
            from data_fetcher import DataFetcher
            from trend_identifier import TrendIdentifier
            from sector_scanner import SectorScanner
            from stock_selector import StockSelector
            from entry_monitor import EntryMonitor
            from order_executor import OrderExecutor
            from position_monitor import PositionMonitor

            sys.stdout = self._gui_logger   # redirect print() to GUI

            self._log("📡 Connecting to Angel One API...")
            api = get_api()
            if not api:
                self._log("❌ Failed to create API — check credentials in Settings")
                return

            if not api.is_connected and not api.connect():
                self._log("❌ API connection failed — check credentials")
                return

            self._log("✅ API connected")

            # WebSocket sector subscription
            if api.ws_manager:
                symbols = [{'exchange': 'NSE', 'token': '99926000'}]
                for _, (sym, tok, exch) in SECTORAL_INDICES.items():
                    symbols.append({'exchange': exch, 'token': tok})
                if api.subscribe_symbols(symbols):
                    self._log(f"✅ Subscribed to {len(symbols)} indices")
                time.sleep(2)

            logger         = self._gui_logger
            data_fetcher   = DataFetcher(api)
            trend_id       = TrendIdentifier(api, logger)
            sector_scanner = SectorScanner(api, logger)
            stock_selector = StockSelector(api, data_fetcher, logger)
            entry_monitor  = EntryMonitor(api, data_fetcher, logger)
            order_executor = OrderExecutor(api, data_fetcher, logger)
            pos_monitor    = PositionMonitor(api, data_fetcher, order_executor, logger)

            # Identify trend
            if force_trend:
                trend = force_trend
                self._log(f"🎯 Forced trend: {trend}")
            else:
                trend = trend_id.identify_trend()

            if not trend:
                self._log("❌ Could not identify trend")
                return

            t_col = "#4caf8a" if trend == "BULLISH" else "#e57373"
            self._card(self._card_trend, trend, t_col)

            # Sector scan
            sector_scanner.scan_all_sectors()
            sector_scanner.display_sector_ranking()

            selected_sector = None
            selected_stock  = None

            while trade_count < MAX_TRADES_PER_DAY and not self._stop_event.is_set():
                cutoff = datetime.strptime(ENTRY_CUTOFF, "%H:%M").time()
                if datetime.now().time() >= cutoff:
                    self._log("⏰ Entry cutoff reached")
                    break

                if not selected_sector:
                    selected_sector = sector_scanner.select_sector_for_trend(trend)
                if not selected_sector:
                    self._log("❌ No sector selected")
                    break

                self._card(self._card_sector,
                           selected_sector.get('name', '—'), C_WHITE)

                selected_stock = stock_selector.select_best_stock(
                    selected_sector['name'], trend)
                if not selected_stock:
                    self._log("⚠️ No suitable stock found")
                    break

                self._card(self._card_stock,
                           selected_stock.get('symbol', '—'), C_WHITE)

                if api.ws_manager:
                    api.subscribe_symbols([{
                        'exchange': selected_stock.get('exchange', 'NSE'),
                        'token': selected_stock['token']
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
                        self._card(self._card_trades,
                                   f"{trade_count} / {MAX_TRADES_PER_DAY}",
                                   "#4caf8a")
                        self._log(f"✅ Trade {trade_count} executed!")
                        pos_monitor.start_monitoring()
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
            err = f"{e}\n{traceback.format_exc()}"
            self._log(f"❌ Strategy error: {err}")
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
            self.after(0, self._done, trade_count)


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
