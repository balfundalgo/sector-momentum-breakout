"""
Sector Momentum Breakout Strategy — GUI (Light Theme)

Phase timeline:
  PRE-MARKET  : Before 09:15 → countdown to market open
  CANDLE WAIT : 09:15–09:25  → countdown to candle close
  RUNNING     : 09:25+       → sector scan, stock select, entry, monitor
"""

import sys
import os
import csv
import time
import threading
import traceback
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime, timedelta

# ── path setup ───────────────────────────────────────────────────────────────
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

# ── colour palette (light) ───────────────────────────────────────────────────
C_BG        = "#f4f6f9"
C_PANEL     = "#ffffff"
C_SIDEBAR   = "#1e2a3a"
C_SIDEBAR2  = "#253447"
C_BORDER    = "#dde3ec"
C_GREEN     = "#1a8a5a"
C_RED       = "#d93025"
C_BLUE      = "#1a6fd4"
C_YELLOW    = "#b06000"
C_TEXT      = "#1a1a2e"
C_MUTED     = "#7a8899"
C_WHITE     = "#ffffff"
C_ACCENT    = "#1a6fd4"
C_HEADER    = "#f0f3f8"
C_ORANGE    = "#e07b00"

FONT_TITLE  = ("Helvetica", 13, "bold")
FONT_HEAD   = ("Helvetica", 10, "bold")
FONT_BODY   = ("Helvetica", 10)
FONT_SMALL  = ("Helvetica", 9)
FONT_MONO   = ("Courier", 9)
FONT_COUNT  = ("Helvetica", 22, "bold")


# ─────────────────────────────────────────────────────────────────────────────
# GUI Logger
# ─────────────────────────────────────────────────────────────────────────────
class GUILogger:
    def __init__(self, text_widget: scrolledtext.ScrolledText):
        self._tw   = text_widget
        self._lock = threading.Lock()
        self._today   = datetime.now().strftime("%Y-%m-%d")
        self._log_dir = EXE_DIR
        self.trade_log_file = os.path.join(EXE_DIR, f"trades_{self._today}.csv")
        self._init_trade_log()

        self._tw.tag_configure("INFO",    foreground=C_TEXT,   font=FONT_MONO)
        self._tw.tag_configure("SUCCESS", foreground=C_GREEN,  font=FONT_MONO)
        self._tw.tag_configure("WARN",    foreground=C_YELLOW, font=FONT_MONO)
        self._tw.tag_configure("ERROR",   foreground=C_RED,    font=FONT_MONO)
        self._tw.tag_configure("MUTED",   foreground=C_MUTED,  font=FONT_MONO)
        self._tw.tag_configure("ACCENT",  foreground=C_BLUE,   font=FONT_MONO)
        self._tw.tag_configure("BANNER",  foreground=C_ACCENT,
                               font=("Courier", 9, "bold"))

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
        if any(x in m for x in ["✅","success","connected","executed","subscribed"]):
            return "SUCCESS"
        if any(x in m for x in ["❌","error","failed","fatal"]):
            return "ERROR"
        if any(x in m for x in ["⚠️","warning","retry","backoff","waiting","⏳"]):
            return "WARN"
        if "═" in msg or "║" in msg or "╔" in msg or "╚" in msg:
            return "BANNER"
        if any(x in m for x in ["📡","🎯","📈","📉","🏆","⏰","🔴","🟢","📊"]):
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

    def write(self, msg: str):   self._write(msg)
    def flush(self):              pass
    def debug(self, msg: str):   self._write(f"[DEBUG] {msg}", "MUTED")
    def info(self, msg: str):    self._write(msg)
    def warning(self, msg: str): self._write(f"⚠️  {msg}", "WARN")
    def error(self, msg: str):   self._write(f"❌ {msg}", "ERROR")

    def print_banner(self, msg: str):
        self._write(f"{'─'*48}", "BANNER")
        self._write(f"  {msg}",  "BANNER")
        self._write(f"{'─'*48}", "BANNER")

    def log_event(self, event_type: str, details: dict):
        detail_str = ", ".join(f"{k}={v}" for k, v in details.items())
        self._write(f"📋 [{event_type}] {detail_str}", "ACCENT")
        event_file = os.path.join(self._log_dir, f"events_{self._today}.csv")
        try:
            write_hdr = not os.path.exists(event_file)
            with open(event_file, 'a', newline='') as f:
                w = csv.writer(f)
                if write_hdr:
                    w.writerow(['timestamp', 'event_type', 'details'])
                w.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            event_type, str(details)])
        except Exception:
            pass

    def log_trade_entry(self, trade: dict):
        self._write(
            f"📝 Trade Entry: {trade.get('symbol')} "
            f"{trade.get('direction')} @ {trade.get('entry_price')} "
            f"SL={trade.get('stop_loss')} TP={trade.get('take_profit')}",
            "SUCCESS"
        )
        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            trade.get('trade_id',''), trade.get('symbol',''),
            trade.get('trade_type',''), trade.get('direction',''),
            trade.get('entry_price',0), trade.get('stop_loss',0),
            trade.get('take_profit',0), trade.get('quantity',0),
            trade.get('option_symbol',''), trade.get('option_entry_price',0),
            trade.get('option_quantity',0), trade.get('future_symbol',''),
            trade.get('future_entry_price',0), trade.get('future_quantity',0),
            '','','','','OPEN'
        ]
        try:
            with open(self.trade_log_file, 'a', newline='') as f:
                csv.writer(f).writerow(row)
        except Exception:
            pass

    def log_trade_exit(self, trade_id: str, exit_price: float,
                       exit_reason: str, pnl: float):
        col = "SUCCESS" if pnl >= 0 else "ERROR"
        self._write(
            f"📝 Trade Exit: {trade_id} | {exit_reason} @ {exit_price} "
            f"PnL={pnl:+.2f}", col
        )
        try:
            rows = []
            with open(self.trade_log_file, 'r') as f:
                rows = list(csv.reader(f))
            if len(rows) > 1:
                hdr = rows[0]
                for i, row in enumerate(rows[1:], 1):
                    if row[hdr.index('trade_id')] == trade_id:
                        rows[i][hdr.index('exit_price')]  = exit_price
                        rows[i][hdr.index('exit_time')]   = \
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        rows[i][hdr.index('exit_reason')] = exit_reason
                        rows[i][hdr.index('pnl')]         = pnl
                        rows[i][hdr.index('status')]      = 'CLOSED'
                        break
                with open(self.trade_log_file, 'w', newline='') as f:
                    csv.writer(f).writerows(rows)
        except Exception:
            pass

    def get_daily_summary(self) -> dict:
        try:
            with open(self.trade_log_file, 'r') as f:
                rows = list(csv.DictReader(f))
            closed = [r for r in rows if r.get('status') == 'CLOSED']
            pnl    = sum(float(r.get('pnl', 0) or 0) for r in closed)
            return {'total_trades': len(rows), 'closed_trades': len(closed),
                    'open_trades': len(rows)-len(closed), 'total_pnl': pnl}
        except Exception:
            return {'total_trades':0,'open_trades':0,'closed_trades':0,'total_pnl':0}


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar card helper
# ─────────────────────────────────────────────────────────────────────────────
class _Card:
    def __init__(self, label_widget):
        self._lbl = label_widget
    def set(self, v, c=C_WHITE):
        self._lbl.config(text=v, fg=c)


# ─────────────────────────────────────────────────────────────────────────────
# Settings panel
# ─────────────────────────────────────────────────────────────────────────────
class SettingsPanel(tk.Toplevel):
    FIELDS = [
        ("API CREDENTIALS", None),
        ("CLIENT_ID",              "Client ID",          False),
        ("API_KEY",                "API Key",             False),
        ("MPIN",                   "MPIN",                True),
        ("TOTP_SECRET",            "TOTP Secret",         True),
        ("STRATEGY PARAMETERS", None),
        ("ENTRY_CUTOFF",           "Entry Cutoff HH:MM",  False),
        ("FORCE_EXIT_TIME",        "Force Exit HH:MM",    False),
        ("MAX_TRADES_PER_DAY",     "Max Trades/Day",      False),
        ("LOTS_PER_TRADE",         "Lots Per Trade",      False),
        ("MAX_STOCK_MOVEMENT_PCT", "Max Stock Move %",    False),
        ("TRAILING_TRIGGER_PCT",   "Trailing Trigger %",  False),
        ("RISK_REWARD_RATIO",      "Risk/Reward Ratio",   False),
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
            key, label = item[0], item[1]
            secret = item[2] if len(item) > 2 else False
            if label is None:
                tk.Label(frame, text=key, font=("Helvetica", 9, "bold"),
                         bg=C_BG, fg=C_ACCENT).grid(
                    row=row, column=0, columnspan=2, sticky='w', pady=(16,4))
                row += 1
                continue
            tk.Label(frame, text=label, font=FONT_BODY,
                     bg=C_BG, fg=C_TEXT, anchor='w', width=22).grid(
                row=row, column=0, sticky='w', pady=4)
            e = tk.Entry(frame, font=FONT_BODY, bg=C_WHITE, fg=C_TEXT,
                         relief='solid', bd=1, width=30,
                         show='●' if secret else '')
            e.insert(0, s.get(key, ''))
            e.grid(row=row, column=1, sticky='ew', padx=(8,0), pady=4)
            self._entries[key] = e
            row += 1

        btn_f = tk.Frame(self, bg=C_BG)
        btn_f.pack(fill='x', padx=24, pady=(0,20))
        tk.Button(btn_f, text="  Save Settings  ", font=FONT_HEAD,
                  bg=C_GREEN, fg=C_WHITE, relief='flat',
                  padx=16, pady=8, cursor='hand2',
                  command=self._save_click).pack(side='left')
        tk.Button(btn_f, text="  Cancel  ", font=FONT_BODY,
                  bg=C_BORDER, fg=C_TEXT, relief='flat',
                  padx=16, pady=8, cursor='hand2',
                  command=self.destroy).pack(side='left', padx=(8,0))

    def _save_click(self):
        updates = {k: e.get().strip() for k, e in self._entries.items()}
        self._save(updates)
        messagebox.showinfo("Saved", "✅ Settings saved!")
        self.destroy()


# ─────────────────────────────────────────────────────────────────────────────
# Main application
# ─────────────────────────────────────────────────────────────────────────────
class App(tk.Tk):

    # Market timing constants
    MARKET_OPEN  = "09:15"   # API connect / WebSocket subscribe
    CANDLE_CLOSE = "09:25"   # trend candle completes — strategy starts here

    def __init__(self):
        super().__init__()
        self.title("Sector Momentum Breakout Strategy")
        self.configure(bg=C_BG)
        self.geometry("1080x700")
        self.minsize(900, 580)

        self._running    = False
        self._stop_event = threading.Event()
        self._strat_thread: threading.Thread = None
        self._countdown_job = None   # after() job id for countdown ticker

        self._build_ui()
        self._check_credentials()

    # ── UI construction ───────────────────────────────────────────────────
    def _build_ui(self):
        # Top nav
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

        # Sidebar (left, dark)
        sidebar = tk.Frame(body, bg=C_SIDEBAR, width=230)
        sidebar.pack(side='left', fill='y')
        sidebar.pack_propagate(False)
        self._build_sidebar(sidebar)

        # Content (right, light)
        content = tk.Frame(body, bg=C_BG)
        content.pack(side='left', fill='both', expand=True, padx=14, pady=14)
        self._build_content(content)

    def _build_sidebar(self, parent):
        # ── Phase / countdown banner ──────────────────────────────────────
        self._phase_frame = tk.Frame(parent, bg="#0f1e2e")
        self._phase_frame.pack(fill='x', pady=(0,2))

        self._phase_label = tk.Label(
            self._phase_frame, text="READY",
            font=("Helvetica", 9, "bold"),
            bg="#0f1e2e", fg="#6b8099")
        self._phase_label.pack(pady=(8,2))

        self._countdown_label = tk.Label(
            self._phase_frame, text="",
            font=FONT_COUNT, bg="#0f1e2e", fg=C_WHITE)
        self._countdown_label.pack(pady=(0,4))

        self._phase_sub = tk.Label(
            self._phase_frame, text="",
            font=FONT_SMALL, bg="#0f1e2e", fg="#6b8099",
            wraplength=200)
        self._phase_sub.pack(pady=(0,8))

        # ── Status cards ──────────────────────────────────────────────────
        self._sb_label("STATUS", parent)
        self._card_status = self._sb_card(parent, "Strategy", "● Idle",  C_MUTED)
        self._card_mode   = self._sb_card(parent, "Mode",     "—")
        self._card_trend  = self._sb_card(parent, "Trend",    "—")
        self._card_sector = self._sb_card(parent, "Sector",   "—")
        self._card_stock  = self._sb_card(parent, "Stock",    "—")
        self._card_trades = self._sb_card(parent, "Trades",   "0 / 2")

        # ── Mode toggle ───────────────────────────────────────────────────
        self._sb_label("TRADING MODE", parent, top=10)
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

        # ── Trend override ────────────────────────────────────────────────
        self._sb_label("TREND OVERRIDE", parent, top=8)
        trend_f = tk.Frame(parent, bg=C_SIDEBAR2)
        trend_f.pack(fill='x', padx=10, pady=2)
        self._trend_var = tk.StringVar(value="AUTO")
        for text, col in [("AUTO","#aaaaaa"),("BULLISH","#4caf8a"),("BEARISH","#e57373")]:
            tk.Radiobutton(trend_f, text=f"  {text}",
                           variable=self._trend_var, value=text,
                           font=FONT_SMALL, bg=C_SIDEBAR2, fg=col,
                           selectcolor=C_SIDEBAR2,
                           activebackground=C_SIDEBAR2).pack(
                anchor='w', padx=10, pady=3)

        # ── Buttons ───────────────────────────────────────────────────────
        tk.Frame(parent, bg=C_SIDEBAR).pack(fill='y', expand=True)

        self._btn_start = tk.Button(parent, text="▶  START",
                                    font=FONT_HEAD,
                                    bg="#1a8a5a", fg=C_WHITE,
                                    relief='flat', pady=10, cursor='hand2',
                                    command=self._start)
        self._btn_start.pack(fill='x', padx=10, pady=(2,3))

        self._btn_stop = tk.Button(parent, text="⏹  STOP",
                                   font=FONT_HEAD,
                                   bg="#c0392b", fg=C_WHITE,
                                   relief='flat', pady=10, cursor='hand2',
                                   state='disabled', command=self._stop)
        self._btn_stop.pack(fill='x', padx=10, pady=(0,3))

        tk.Button(parent, text="🗑  Clear Log",
                  font=FONT_SMALL, bg=C_SIDEBAR, fg=C_MUTED,
                  relief='flat', pady=4, cursor='hand2',
                  command=self._clear_log).pack(fill='x', padx=10, pady=(0,10))

    def _sb_label(self, text, parent, top=8):
        tk.Label(parent, text=text, font=("Helvetica", 8, "bold"),
                 bg=C_SIDEBAR, fg="#6b8099").pack(
            anchor='w', padx=14, pady=(top,2))

    def _sb_card(self, parent, label, value="—", color=C_WHITE) -> _Card:
        f = tk.Frame(parent, bg=C_SIDEBAR2)
        f.pack(fill='x', padx=10, pady=2)
        tk.Label(f, text=label, font=("Helvetica", 8),
                 bg=C_SIDEBAR2, fg="#6b8099").pack(anchor='w', padx=10, pady=(6,0))
        lbl = tk.Label(f, text=value, font=FONT_HEAD,
                       bg=C_SIDEBAR2, fg=color)
        lbl.pack(anchor='w', padx=10, pady=(0,6))
        return _Card(lbl)

    def _build_content(self, parent):
        tk.Label(parent, text="Activity Log", font=FONT_TITLE,
                 bg=C_BG, fg=C_TEXT).pack(anchor='w', pady=(0,8))

        log_card = tk.Frame(parent, bg=C_PANEL,
                            highlightbackground=C_BORDER, highlightthickness=1)
        log_card.pack(fill='both', expand=True)

        toolbar = tk.Frame(log_card, bg=C_HEADER)
        toolbar.pack(fill='x')
        tk.Label(toolbar, text="  Console Output",
                 font=FONT_SMALL, bg=C_HEADER, fg=C_MUTED).pack(
            side='left', padx=4, pady=4)

        self._log_box = scrolledtext.ScrolledText(
            log_card, font=FONT_MONO,
            bg=C_WHITE, fg=C_TEXT,
            relief='flat', state='disabled', wrap='word',
            padx=10, pady=8)
        self._log_box.pack(fill='both', expand=True)
        self._gui_logger = GUILogger(self._log_box)

        self._statusbar = tk.Label(
            parent,
            text="Ready — configure credentials in Settings",
            font=FONT_SMALL, bg=C_BORDER, fg=C_MUTED, anchor='w', padx=8)
        self._statusbar.pack(fill='x', pady=(6,0))

    # ── Helpers ───────────────────────────────────────────────────────────
    def _log(self, msg):         self._gui_logger.write(msg)
    def _clear_log(self):
        self._log_box.configure(state='normal')
        self._log_box.delete('1.0', tk.END)
        self._log_box.configure(state='disabled')
    def _set_status(self, msg):  self._statusbar.config(text=f"  {msg}")
    def _open_settings(self):    SettingsPanel(self)
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

    # ── Phase / countdown display ─────────────────────────────────────────
    def _set_phase(self, phase: str, countdown: str = "", sub: str = ""):
        """Update the phase banner in the sidebar (safe to call from any thread)."""
        colours = {
            "READY":         ("#6b8099", C_WHITE),
            "PRE-MARKET":    (C_ORANGE,  C_WHITE),
            "CANDLE WAIT":   (C_BLUE,    C_WHITE),
            "RUNNING":       (C_GREEN,   C_WHITE),
            "STOPPED":       (C_MUTED,   C_WHITE),
        }
        lbl_col, cnt_col = colours.get(phase, ("#6b8099", C_WHITE))

        def _upd():
            self._phase_label.config(text=phase, fg=lbl_col)
            self._countdown_label.config(text=countdown, fg=cnt_col)
            self._phase_sub.config(text=sub)
        self.after(0, _upd)

    def _start_countdown(self, target_time: datetime, phase: str, sub: str):
        """Tick every second updating the countdown label until target_time."""
        if self._countdown_job:
            self.after_cancel(self._countdown_job)

        def _tick():
            if not self._running:
                return
            remaining = (target_time - datetime.now()).total_seconds()
            if remaining <= 0:
                self._set_phase(phase, "00:00:00", sub)
                return
            h = int(remaining // 3600)
            m = int((remaining % 3600) // 60)
            s = int(remaining % 60)
            self._set_phase(phase, f"{h:02d}:{m:02d}:{s:02d}", sub)
            self._countdown_job = self.after(1000, _tick)

        _tick()

    def _stop_countdown(self):
        if self._countdown_job:
            self.after_cancel(self._countdown_job)
            self._countdown_job = None

    # ── Strategy control ──────────────────────────────────────────────────
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
        self._card(self._card_status, "● CONNECTING", "#f5a623")
        self._card(self._card_mode,   mode, "#e57373" if live else "#4caf8a")
        self._set_status(f"Starting in {mode} mode...")
        self._log("=" * 52)
        self._log(f"  START  |  Mode: {mode}  |  Trend: {self._trend_var.get()}")
        self._log("=" * 52)

        self._strat_thread = threading.Thread(
            target=self._run, args=(not live, force_trend), daemon=True)
        self._strat_thread.start()

    def _stop(self):
        self._stop_event.set()
        self._stop_countdown()
        self._log("🛑 Stop requested...")
        self._set_status("Stopping...")

    def _done(self, trade_count):
        self._running = False
        self._stop_countdown()
        self._btn_start.config(state='normal')
        self._btn_stop.config(state='disabled')
        self._card(self._card_status, "● Stopped", C_MUTED)
        self._card(self._card_trades, f"{trade_count} / 2")
        self._set_phase("STOPPED", "", "Strategy ended")
        self._set_status(f"Strategy ended — {trade_count} trade(s) today")

    # ── Background strategy thread ────────────────────────────────────────
    def _run(self, paper_trading: bool, force_trend):
        trade_count = 0
        try:
            from config import (MAX_TRADES_PER_DAY, ENTRY_CUTOFF,
                                SECTORAL_INDICES)
            from angel_api import get_api
            from data_fetcher import DataFetcher
            from trend_identifier import TrendIdentifier
            from sector_scanner import SectorScanner
            from stock_selector import StockSelector
            from entry_monitor import EntryMonitor
            from order_executor import OrderExecutor
            from position_monitor import PositionMonitor

            sys.stdout = self._gui_logger   # redirect print() → GUI

            today = datetime.now().strftime("%Y-%m-%d")
            market_open  = datetime.strptime(f"{today} {self.MARKET_OPEN}",
                                             "%Y-%m-%d %H:%M")
            candle_close = datetime.strptime(f"{today} {self.CANDLE_CLOSE}",
                                             "%Y-%m-%d %H:%M")

            # ── PHASE 0: Connect to API (always do this immediately) ──────
            self._log("📡 Connecting to Angel One API...")
            api = get_api()
            if not api:
                self._log("❌ Failed to create API — check credentials in Settings")
                return
            if not api.is_connected and not api.connect():
                self._log("❌ API connection failed")
                return
            self._log("✅ API connected")
            self._card(self._card_status, "● WAITING", "#f5a623")

            # Subscribe sector indices via WebSocket right away
            if api.ws_manager:
                symbols = [{'exchange': 'NSE', 'token': '99926000'}]
                for _, (sym, tok, exch) in SECTORAL_INDICES.items():
                    symbols.append({'exchange': exch, 'token': tok})
                if api.subscribe_symbols(symbols):
                    self._log(f"✅ WebSocket: subscribed to {len(symbols)} indices")
                time.sleep(2)

            # ── PHASE 1: PRE-MARKET — wait until 09:15 ───────────────────
            now = datetime.now()
            if now < market_open and not self._stop_event.is_set():
                self._log(f"⏳ Pre-market: waiting until {self.MARKET_OPEN}...")
                self._set_status(f"Waiting for market open at {self.MARKET_OPEN}")
                self.after(0, lambda: self._start_countdown(
                    market_open, "PRE-MARKET",
                    f"Market opens at {self.MARKET_OPEN}"))

                while datetime.now() < market_open and not self._stop_event.is_set():
                    time.sleep(1)

                if self._stop_event.is_set():
                    return
                self._log(f"✅ Market open time reached ({self.MARKET_OPEN})")

            if self._stop_event.is_set():
                return

            # ── PHASE 2: CANDLE WAIT — 09:15 to 09:25 ────────────────────
            now = datetime.now()
            if now < candle_close and not self._stop_event.is_set():
                self._log(
                    f"⏳ Candle forming: waiting until {self.CANDLE_CLOSE} "
                    f"for NIFTY 10-min candle to close...")
                self._set_status(
                    f"Waiting for NIFTY candle to close at {self.CANDLE_CLOSE}")
                self.after(0, lambda: self._start_countdown(
                    candle_close, "CANDLE WAIT",
                    f"NIFTY 10-min candle closes at {self.CANDLE_CLOSE}"))

                while datetime.now() < candle_close and not self._stop_event.is_set():
                    time.sleep(1)

                if self._stop_event.is_set():
                    return
                self._log(f"✅ Candle window closed — reading trend candle now")
                time.sleep(3)   # small buffer for Angel One data to propagate

            if self._stop_event.is_set():
                return

            # ── PHASE 3: STRATEGY RUNNING ─────────────────────────────────
            self._stop_countdown()
            self._set_phase("RUNNING", "", "Strategy active")
            self._card(self._card_status, "● RUNNING", "#4caf8a")
            self._set_status("Strategy running...")

            logger         = self._gui_logger
            data_fetcher   = DataFetcher(api)
            trend_id       = TrendIdentifier(api, logger)
            sector_scanner = SectorScanner(api, logger)
            stock_selector = StockSelector(api, data_fetcher, logger)
            entry_monitor  = EntryMonitor(api, data_fetcher, logger)
            order_executor = OrderExecutor(api, data_fetcher, logger)
            pos_monitor    = PositionMonitor(api, data_fetcher, order_executor, logger)

            # Identify trend (trend_identifier will NOT re-wait since we already
            # waited above — it's past 09:25 now)
            if force_trend:
                trend = force_trend
                self._log(f"🎯 Forced trend: {trend}")
            else:
                trend = trend_id.identify_trend()

            if not trend or self._stop_event.is_set():
                self._log("❌ Could not identify trend")
                return

            t_col = "#4caf8a" if trend == "BULLISH" else "#e57373"
            self._card(self._card_trend, trend, t_col)

            # Sector scan
            sector_scanner.scan_all_sectors()
            sector_scanner.display_sector_ranking()

            selected_sector = None
            selected_stock  = None

            while (trade_count < MAX_TRADES_PER_DAY
                   and not self._stop_event.is_set()):

                cutoff = datetime.strptime(ENTRY_CUTOFF, "%H:%M").time()
                if datetime.now().time() >= cutoff:
                    self._log("⏰ Entry cutoff reached — no more entries today")
                    break

                # Sector selection
                if not selected_sector:
                    selected_sector = sector_scanner.select_sector_for_trend(trend)
                if not selected_sector:
                    self._log("❌ No sector selected — exiting")
                    break
                self._card(self._card_sector,
                           selected_sector.get('name', '—'), C_WHITE)

                # Stock selection
                selected_stock = stock_selector.select_best_stock(
                    selected_sector['name'], trend)
                if not selected_stock:
                    self._log("⚠️ No suitable stock found")
                    break
                self._card(self._card_stock,
                           selected_stock.get('symbol', '—'), C_WHITE)

                # Subscribe stock via WebSocket
                if api.ws_manager:
                    api.subscribe_symbols([{
                        'exchange': selected_stock.get('exchange', 'NSE'),
                        'token':    selected_stock['token']
                    }])
                    time.sleep(1)

                # Entry monitoring
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
    App().mainloop()


if __name__ == "__main__":
    main()
