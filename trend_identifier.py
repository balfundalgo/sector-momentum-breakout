"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         TREND IDENTIFIER MODULE                                ║
║          Analyzes first 10-minute NIFTY 50 candle to determine trend          ║
║                                                                               ║
║  TIMING RULES (strictly enforced):                                            ║
║  • 09:15 – 09:25 : Candle forming — do NOT fetch yet                         ║
║  • 09:25+         : Candle complete — fetch and identify trend                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

from datetime import datetime, timedelta
from typing import Optional, Dict
import time

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    TREND_START, TREND_END, TREND_CANDLE_MINUTES,
    NIFTY_50_TOKEN, NIFTY_50_SYMBOL, NIFTY_50_EXCHANGE
)
from api_rate_limiter import api_rate_limiter


class TrendIdentifier:
    """
    Identifies market trend from the completed first 10-minute NIFTY 50 candle.
    Always waits until TREND_END (09:25) before fetching — never reads a partial candle.
    """

    def __init__(self, api, logger):
        self.api        = api
        self.logger     = logger
        self.trend      = None
        self.candle_data = None

    # ── Public entry point ────────────────────────────────────────────────
    def identify_trend(self) -> Optional[str]:
        """
        Main entry point.
        - If called before 09:25 → waits (with 5-sec ticks so logger stays alive)
        - Fetches the completed candle and returns 'BULLISH' or 'BEARISH'
        """
        today       = datetime.now().strftime("%Y-%m-%d")
        candle_done = datetime.strptime(f"{today} {TREND_END}", "%Y-%m-%d %H:%M")

        # ── Phase 1: wait for candle to complete ──────────────────────────
        now = datetime.now()
        if now < candle_done:
            remaining = (candle_done - now).total_seconds() + 5  # +5s safety buffer
            self.logger.info(
                f"⏳ Waiting for 09:15–09:25 NIFTY candle to close "
                f"({remaining:.0f}s remaining)..."
            )
            # Sleep in 5-second ticks so the logger/GUI stays responsive
            while True:
                now = datetime.now()
                if now >= candle_done:
                    break
                left = (candle_done - now).total_seconds()
                tick = min(5.0, left + 1)
                time.sleep(tick)

            self.logger.info("✅ Candle window closed — fetching trend candle now")
            time.sleep(2)  # brief extra buffer for Angel One data propagation

        # ── Phase 2: fetch the completed candle ───────────────────────────
        return self._fetch_and_analyse()

    # ── Internal methods ──────────────────────────────────────────────────
    def _fetch_and_analyse(self) -> Optional[str]:
        """Fetch the 09:15–09:25 candle and determine trend. Retries on AB1004."""
        today     = datetime.now().strftime("%Y-%m-%d")
        from_time = f"{today} {TREND_START}"
        to_time   = f"{today} {TREND_END}"

        self.logger.info(f"📊 Fetching NIFTY 50 candle: {from_time} → {to_time}")

        max_retries = 6
        df = None

        for attempt in range(max_retries):
            api_rate_limiter.wait("getCandleData")
            df = self.api.get_historical_data(
                exchange=NIFTY_50_EXCHANGE,
                symbol=NIFTY_50_SYMBOL,
                token=NIFTY_50_TOKEN,
                interval="TEN_MINUTE",
                from_date=from_time,
                to_date=to_time
            )

            if df is not None and len(df) > 0:
                api_rate_limiter.report_success("getCandleData")
                break

            # AB1004 or empty — backoff and retry
            backoff = api_rate_limiter.report_error("getCandleData", "AB1004")
            self.logger.warning(
                f"⚠️ Candle fetch attempt {attempt+1}/{max_retries} failed — "
                f"retrying in {backoff:.0f}s"
            )
            time.sleep(backoff)

        if df is None or len(df) == 0:
            self.logger.error("❌ Could not fetch NIFTY 50 candle after all retries")
            return None

        # ── Analyse the candle ────────────────────────────────────────────
        candle = df.iloc[0]
        self.candle_data = {
            'timestamp': candle['timestamp'],
            'open':   float(candle['open']),
            'high':   float(candle['high']),
            'low':    float(candle['low']),
            'close':  float(candle['close']),
            'volume': int(candle['volume'])
        }

        is_green  = self.candle_data['close'] > self.candle_data['open']
        self.trend = 'BULLISH' if is_green else 'BEARISH'

        body      = abs(self.candle_data['close'] - self.candle_data['open'])
        body_pct  = (body / self.candle_data['open']) * 100

        # Log to GUI / console
        d = self.candle_data
        self.logger.info(
            f"📊 NIFTY 50 Candle:  O={d['open']:.2f}  H={d['high']:.2f}  "
            f"L={d['low']:.2f}  C={d['close']:.2f}"
        )
        self.logger.info(f"📊 Trend Identified: {self.trend}  (body {body_pct:.2f}%)")

        # Pretty box
        arrow = "🟢 BULLISH — BUY setup on BEST sector" if is_green \
            else "🔴 BEARISH — SELL setup on WORST sector"
        for line in [
            f"╔{'═'*50}╗",
            f"║  NIFTY 50 FIRST 10-MIN CANDLE ({TREND_START}–{TREND_END})",
            f"╠{'═'*50}╣",
            f"║  Open:   {d['open']:>12.2f}",
            f"║  High:   {d['high']:>12.2f}",
            f"║  Low:    {d['low']:>12.2f}",
            f"║  Close:  {d['close']:>12.2f}",
            f"║  Volume: {d['volume']:>12,}",
            f"╠{'═'*50}╣",
            f"║  {arrow}",
            f"╚{'═'*50}╝",
        ]:
            self.logger.info(f"   {line}")

        self.logger.log_event('TREND_IDENTIFIED', {
            'trend':    self.trend,
            'open':     d['open'],
            'close':    d['close'],
            'body_pct': round(body_pct, 2)
        })

        return self.trend

    # ── Accessors ─────────────────────────────────────────────────────────
    def get_trend(self)       -> Optional[str]:  return self.trend
    def get_candle_data(self) -> Optional[Dict]: return self.candle_data
    def is_bullish(self)      -> bool:           return self.trend == 'BULLISH'
    def is_bearish(self)      -> bool:           return self.trend == 'BEARISH'
