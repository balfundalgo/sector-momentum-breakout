"""
Data Fetcher — historical candles, LTP, instrument lookup.
Uses api_rate_limiter with exponential backoff for AB1004 errors.
"""

import time
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import sys
sys.path.append('..')
from config import INSTRUMENT_MASTER_URL
from api_rate_limiter import api_rate_limiter


class DataFetcher:

    def __init__(self, api):
        self.api = api
        self.instrument_df = None
        self._cache = {}

    def load_instrument_master(self):
        if self.instrument_df is None:
            self.instrument_df = self.api.download_instrument_master()
        return self.instrument_df

    # ── internal helper with retry + backoff ───────────────────────────────
    def _get_historical_with_retry(self, exchange, symbol, token,
                                   interval, from_date, to_date,
                                   max_retries=5) -> Optional[pd.DataFrame]:
        """
        Wraps api.get_historical_data with rate-limit wait, AB1004 backoff,
        and up to max_retries attempts.
        """
        for attempt in range(max_retries):
            api_rate_limiter.wait("getCandleData")
            df = self.api.get_historical_data(
                exchange=exchange, symbol=symbol, token=token,
                interval=interval, from_date=from_date, to_date=to_date
            )

            if df is not None and len(df) > 0:
                api_rate_limiter.report_success("getCandleData")
                return df

            # Detect AB1004 — the SmartAPI library logs it but doesn't raise;
            # a None result after a wait is our signal.
            if df is None:
                backoff = api_rate_limiter.report_error("getCandleData", "AB1004")
                print(f"   ⏳ Waiting {backoff:.0f}s before retry "
                      f"({attempt + 1}/{max_retries}) for {symbol}...")
                time.sleep(backoff)
            else:
                # Empty dataframe — no data for this period, no point retrying
                break

        return None

    # ── public methods ─────────────────────────────────────────────────────
    def get_nifty_50_candle(self, from_time: str, to_time: str,
                             interval: str = "TEN_MINUTE") -> Optional[Dict]:
        from config import NIFTY_50_TOKEN, NIFTY_50_SYMBOL, NIFTY_50_EXCHANGE
        df = self._get_historical_with_retry(
            NIFTY_50_EXCHANGE, NIFTY_50_SYMBOL, NIFTY_50_TOKEN,
            interval, from_time, to_time
        )
        if df is not None and len(df) > 0:
            c = df.iloc[0]
            return {
                'timestamp': c['timestamp'],
                'open': c['open'], 'high': c['high'],
                'low': c['low'],   'close': c['close'],
                'volume': c['volume'],
                'is_green': c['close'] > c['open']
            }
        return None

    def get_stock_candles(self, symbol: str, token: str,
                          from_time: str, to_time: str,
                          interval: str = "FIVE_MINUTE") -> Optional[pd.DataFrame]:
        df = self._get_historical_with_retry(
            "NSE", symbol, token, interval, from_time, to_time
        )
        if df is not None and len(df) > 0:
            df['range']     = df['high'] - df['low']
            df['range_pct'] = (df['range'] / df['close']) * 100
            df['is_green']  = df['close'] > df['open']
        return df

    def get_previous_day_data(self, symbol: str, token: str,
                               max_retries: int = 5) -> Optional[Dict]:
        """
        Fetch PDH/PDL with full backoff retry. Returns None if unavailable.
        """
        today     = datetime.now()
        from_date = (today - timedelta(days=10)).strftime("%Y-%m-%d 09:15")
        to_date   = (today - timedelta(days=1)).strftime("%Y-%m-%d 15:30")

        # Method 1: Daily candles
        df = self._get_historical_with_retry(
            "NSE", symbol, token, "ONE_DAY",
            from_date, to_date, max_retries=max_retries
        )
        if df is not None and len(df) > 0:
            c = df.iloc[-1]
            print(f"   ✅ PDH/PDL from daily candle for {symbol}")
            return {
                'date':      str(c['timestamp'])[:10],
                'open':      float(c['open']),
                'high':      float(c['high']),
                'low':       float(c['low']),
                'close':     float(c['close']),
                'volume':    int(c['volume']) if 'volume' in c else 0,
                'estimated': False
            }

        # Method 2: Intraday 15-min candles from previous trading day
        prev_day = today - timedelta(days=1)
        while prev_day.weekday() >= 5:
            prev_day -= timedelta(days=1)

        df = self._get_historical_with_retry(
            "NSE", symbol, token, "FIFTEEN_MINUTE",
            prev_day.strftime("%Y-%m-%d 09:15"),
            prev_day.strftime("%Y-%m-%d 15:30"),
            max_retries=max_retries
        )
        if df is not None and len(df) > 0:
            print(f"   ✅ PDH/PDL from 15-min candles for {symbol}")
            return {
                'date':      prev_day.strftime("%Y-%m-%d"),
                'open':      float(df.iloc[0]['open']),
                'high':      float(df['high'].max()),
                'low':       float(df['low'].min()),
                'close':     float(df.iloc[-1]['close']),
                'volume':    int(df['volume'].sum()) if 'volume' in df.columns else 0,
                'estimated': False
            }

        print(f"   ❌ Could not get PDH/PDL for {symbol}")
        return None

    def get_stock_ltp_with_change(self, symbol: str, token: str) -> Optional[Dict]:
        ltp_data = self.api.get_ltp("NSE", symbol, token)
        if ltp_data:
            ltp   = ltp_data.get('ltp', 0)
            close = ltp_data.get('close', 0)
            if close > 0:
                change     = ltp - close
                change_pct = (change / close) * 100
            else:
                change = change_pct = 0
            return {
                'symbol': symbol, 'token': token,
                'ltp': ltp, 'prev_close': close,
                'change': change, 'change_pct': change_pct
            }
        return None

    def get_stock_intraday_movement(self, symbol: str, token: str) -> Optional[Dict]:
        return self.get_stock_ltp_with_change(symbol, token)

    def get_sector_constituents_from_nse(self, index_name: str) -> List[str]:
        index_map = {
            "NIFTY BANK":       "NIFTY%20BANK",
            "NIFTY IT":         "NIFTY%20IT",
            "NIFTY PHARMA":     "NIFTY%20PHARMA",
            "NIFTY AUTO":       "NIFTY%20AUTO",
            "NIFTY METAL":      "NIFTY%20METAL",
            "NIFTY REALTY":     "NIFTY%20REALTY",
            "NIFTY FMCG":       "NIFTY%20FMCG",
            "NIFTY MEDIA":      "NIFTY%20MEDIA",
            "NIFTY ENERGY":     "NIFTY%20ENERGY",
            "NIFTY INFRA":      "NIFTY%20INFRA",
            "NIFTY PSU BANK":   "NIFTY%20PSU%20BANK",
            "NIFTY FIN SERVICE":"NIFTY%20FINANCIAL%20SERVICES",
            "NIFTY PVT BANK":   "NIFTY%20PRIVATE%20BANK",
            "NIFTY COMMODITIES":"NIFTY%20COMMODITIES",
            "NIFTY CONSUMPTION":"NIFTY%20CONSUMPTION",
            "NIFTY MNC":        "NIFTY%20MNC",
        }
        try:
            encoded = index_map.get(index_name, index_name.replace(" ", "%20"))
            url     = f"https://www.nseindia.com/api/equity-stockIndices?index={encoded}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Accept': 'application/json',
            }
            session = requests.Session()
            session.get("https://www.nseindia.com", headers=headers, timeout=10)
            resp = session.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if 'data' in data:
                    return [item['symbol'] for item in data['data']
                            if item.get('symbol') and not item['symbol'].startswith('NIFTY')]
        except Exception as e:
            print(f"   ⚠️ NSE fetch failed for {index_name}: {e}")
        return []

    def find_stock_token(self, symbol: str) -> Optional[str]:
        if self.instrument_df is None:
            self.load_instrument_master()
        if self.instrument_df is None:
            return None
        m = self.instrument_df[
            (self.instrument_df['exch_seg'] == 'NSE') &
            (self.instrument_df['symbol'].str.upper() == symbol.upper()) &
            (self.instrument_df['instrumenttype'] == '')
        ]
        if len(m) > 0:
            return str(m.iloc[0]['token'])
        m = self.instrument_df[
            (self.instrument_df['exch_seg'] == 'NSE') &
            (self.instrument_df['symbol'].str.upper() == f"{symbol.upper()}-EQ")
        ]
        return str(m.iloc[0]['token']) if len(m) > 0 else None

    def get_futures_available(self, symbol: str) -> bool:
        if self.instrument_df is None:
            self.load_instrument_master()
        if self.instrument_df is None:
            return False
        return len(self.instrument_df[
            (self.instrument_df['exch_seg'] == 'NFO') &
            (self.instrument_df['instrumenttype'] == 'FUTSTK') &
            (self.instrument_df['name'].str.upper() == symbol.upper())
        ]) > 0

    def get_options_available(self, symbol: str) -> bool:
        if self.instrument_df is None:
            self.load_instrument_master()
        if self.instrument_df is None:
            return False
        return len(self.instrument_df[
            (self.instrument_df['exch_seg'] == 'NFO') &
            (self.instrument_df['instrumenttype'] == 'OPTSTK') &
            (self.instrument_df['name'].str.upper() == symbol.upper())
        ]) > 0

    def get_lot_size(self, symbol: str) -> Optional[int]:
        if self.instrument_df is None:
            self.load_instrument_master()
        if self.instrument_df is None:
            return None
        f = self.instrument_df[
            (self.instrument_df['exch_seg'] == 'NFO') &
            (self.instrument_df['instrumenttype'] == 'FUTSTK') &
            (self.instrument_df['name'].str.upper() == symbol.upper())
        ]
        return int(f.iloc[0]['lotsize']) if len(f) > 0 else None

    def get_strike_interval(self, symbol: str) -> float:
        if self.instrument_df is None:
            self.load_instrument_master()
        if self.instrument_df is None:
            return 50
        opts = self.instrument_df[
            (self.instrument_df['exch_seg'] == 'NFO') &
            (self.instrument_df['instrumenttype'] == 'OPTSTK') &
            (self.instrument_df['name'].str.upper() == symbol.upper())
        ]
        if len(opts) >= 2:
            strikes = sorted(opts['strike'].astype(float).unique())
            if len(strikes) >= 2:
                return (strikes[1] - strikes[0]) / 100
        return 50
