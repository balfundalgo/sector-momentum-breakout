"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                           DATA FETCHER UTILITY                                 ║
║              Handles historical data, candles, and live quotes                 ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import time
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import sys
sys.path.append('..')
from config import INSTRUMENT_MASTER_URL


class DataFetcher:
    """
    Utility class for fetching market data
    """
    
    def __init__(self, api):
        """
        Initialize with API instance
        
        Args:
            api: AngelOneAPI instance
        """
        self.api = api
        self.instrument_df = None
        self._cache = {}
    
    def load_instrument_master(self):
        """
        Load instrument master from Angel One
        """
        if self.instrument_df is None:
            self.instrument_df = self.api.download_instrument_master()
        return self.instrument_df
    
    def get_nifty_50_candle(self, from_time: str, to_time: str, interval: str = "TEN_MINUTE") -> Optional[Dict]:
        """
        Get NIFTY 50 candle data
        
        Args:
            from_time: Start time "YYYY-MM-DD HH:MM"
            to_time: End time "YYYY-MM-DD HH:MM"
            interval: Candle interval
            
        Returns:
            Dict with candle data or None
        """
        from config import NIFTY_50_TOKEN, NIFTY_50_SYMBOL, NIFTY_50_EXCHANGE
        
        df = self.api.get_historical_data(
            exchange=NIFTY_50_EXCHANGE,
            symbol=NIFTY_50_SYMBOL,
            token=NIFTY_50_TOKEN,
            interval=interval,
            from_date=from_time,
            to_date=to_time
        )
        
        if df is not None and len(df) > 0:
            candle = df.iloc[0]
            return {
                'timestamp': candle['timestamp'],
                'open': candle['open'],
                'high': candle['high'],
                'low': candle['low'],
                'close': candle['close'],
                'volume': candle['volume'],
                'is_green': candle['close'] > candle['open']
            }
        return None
    
    def get_stock_candles(self, symbol: str, token: str, from_time: str, 
                          to_time: str, interval: str = "FIVE_MINUTE") -> Optional[pd.DataFrame]:
        """
        Get stock candle data
        
        Args:
            symbol: Stock symbol
            token: Instrument token
            from_time: Start time
            to_time: End time
            interval: Candle interval
            
        Returns:
            DataFrame with candle data
        """
        df = self.api.get_historical_data(
            exchange="NSE",
            symbol=symbol,
            token=token,
            interval=interval,
            from_date=from_time,
            to_date=to_time
        )
        
        if df is not None and len(df) > 0:
            # Add calculated fields
            df['range'] = df['high'] - df['low']
            df['range_pct'] = (df['range'] / df['close']) * 100
            df['is_green'] = df['close'] > df['open']
        
        return df
    
    def get_previous_day_data(self, symbol: str, token: str, max_retries: int = 3) -> Optional[Dict]:
        """
        Get previous trading day's OHLC data (EXACT values only, no estimates)
        
        Args:
            symbol: Stock symbol
            token: Instrument token
            max_retries: Number of retry attempts for API calls
            
        Returns:
            Dict with previous day high, low, close OR None if exact data unavailable
        """
        today = datetime.now()
        
        # Go back several days to ensure we get data (handles weekends/holidays)
        from_date = (today - timedelta(days=10)).strftime("%Y-%m-%d 09:15")
        to_date = (today - timedelta(days=1)).strftime("%Y-%m-%d 15:30")
        
        # Method 1: Try to get daily candles (with retry logic)
        # Note: api_rate_limiter handles the pacing between calls
        for attempt in range(max_retries):
            if attempt > 0:
                # Longer delay after API error - needs recovery time
                delay = 3.0 + (attempt * 2.0)  # 3s, 5s, 7s...
                print(f"   ⏳ Retry {attempt}/{max_retries-1} for daily data (waiting {delay}s)...")
                time.sleep(delay)
            
            df = self.api.get_historical_data(
                exchange="NSE",
                symbol=symbol,
                token=token,
                interval="ONE_DAY",
                from_date=from_date,
                to_date=to_date
            )
            
            if df is not None and len(df) > 0:
                candle = df.iloc[-1]
                print(f"   ✅ Got exact PDH/PDL from daily candle")
                return {
                    'date': str(candle['timestamp'])[:10] if 'timestamp' in candle else to_date[:10],
                    'open': float(candle['open']),
                    'high': float(candle['high']),
                    'low': float(candle['low']),
                    'close': float(candle['close']),
                    'volume': int(candle['volume']) if 'volume' in candle else 0,
                    'estimated': False
                }
        
        # Method 2: Try getting intraday candles from previous day
        prev_day = today - timedelta(days=1)
        while prev_day.weekday() >= 5:  # Skip weekends
            prev_day -= timedelta(days=1)
        
        intraday_from = prev_day.strftime("%Y-%m-%d 09:15")
        intraday_to = prev_day.strftime("%Y-%m-%d 15:30")
        
        print(f"   📊 Trying intraday candles for PDH/PDL...")
        for attempt in range(max_retries):
            if attempt > 0:
                # Longer delay after API error
                delay = 3.0 + (attempt * 2.0)
                print(f"   ⏳ Retry {attempt}/{max_retries-1} for intraday data (waiting {delay}s)...")
                time.sleep(delay)
            
            df = self.api.get_historical_data(
                exchange="NSE",
                symbol=symbol,
                token=token,
                interval="FIFTEEN_MINUTE",
                from_date=intraday_from,
                to_date=intraday_to
            )
            
            if df is not None and len(df) > 0:
                print(f"   ✅ Got exact PDH/PDL from intraday candles")
                return {
                    'date': prev_day.strftime("%Y-%m-%d"),
                    'open': float(df.iloc[0]['open']),
                    'high': float(df['high'].max()),
                    'low': float(df['low'].min()),
                    'close': float(df.iloc[-1]['close']),
                    'volume': int(df['volume'].sum()) if 'volume' in df.columns else 0,
                    'estimated': False
                }
        
        # NO FALLBACK TO ESTIMATED VALUES - return None
        print(f"   ❌ Could not get exact PDH/PDL for {symbol} after {max_retries*2} attempts")
        return None
    
    def get_stock_ltp_with_change(self, symbol: str, token: str) -> Optional[Dict]:
        """
        Get stock LTP with percentage change from previous close
        
        Args:
            symbol: Stock symbol
            token: Instrument token
            
        Returns:
            Dict with LTP, previous close, and change percentage
        """
        ltp_data = self.api.get_ltp("NSE", symbol, token)
        
        if ltp_data:
            ltp = ltp_data.get('ltp', 0)
            close = ltp_data.get('close', 0)  # Previous close
            
            if close > 0:
                change = ltp - close
                change_pct = (change / close) * 100
            else:
                change = 0
                change_pct = 0
            
            return {
                'symbol': symbol,
                'token': token,
                'ltp': ltp,
                'prev_close': close,
                'change': change,
                'change_pct': change_pct
            }
        
        return None
    
    def get_stock_intraday_movement(self, symbol: str, token: str) -> Optional[Dict]:
        """
        Get stock's intraday movement (LTP vs Previous Close)
        
        This is the standard NSE calculation for gainers/losers:
        % Change = (LTP - Previous Close) / Previous Close × 100
        
        Args:
            symbol: Stock symbol
            token: Instrument token
            
        Returns:
            Dict with movement data
        """
        return self.get_stock_ltp_with_change(symbol, token)
    
    def get_sector_constituents_from_nse(self, index_name: str) -> List[str]:
        """
        Fetch sector constituents dynamically from NSE
        
        Args:
            index_name: Name of the index (e.g., "NIFTY BANK")
            
        Returns:
            List of stock symbols
        """
        # NSE Index constituents URL pattern
        index_map = {
            "NIFTY BANK": "NIFTY%20BANK",
            "NIFTY IT": "NIFTY%20IT",
            "NIFTY PHARMA": "NIFTY%20PHARMA",
            "NIFTY AUTO": "NIFTY%20AUTO",
            "NIFTY METAL": "NIFTY%20METAL",
            "NIFTY REALTY": "NIFTY%20REALTY",
            "NIFTY FMCG": "NIFTY%20FMCG",
            "NIFTY MEDIA": "NIFTY%20MEDIA",
            "NIFTY ENERGY": "NIFTY%20ENERGY",
            "NIFTY INFRA": "NIFTY%20INFRA",
            "NIFTY PSU BANK": "NIFTY%20PSU%20BANK",
            "NIFTY FIN SERVICE": "NIFTY%20FINANCIAL%20SERVICES",
            "NIFTY PVT BANK": "NIFTY%20PRIVATE%20BANK",
            "NIFTY COMMODITIES": "NIFTY%20COMMODITIES",
            "NIFTY CONSUMPTION": "NIFTY%20CONSUMPTION",
            "NIFTY HEALTHCARE": "NIFTY%20HEALTHCARE%20INDEX",
            "NIFTY OIL & GAS": "NIFTY%20OIL%20%26%20GAS",
            "NIFTY MNC": "NIFTY%20MNC",
        }
        
        try:
            encoded_name = index_map.get(index_name, index_name.replace(" ", "%20"))
            url = f"https://www.nseindia.com/api/equity-stockIndices?index={encoded_name}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.9',
            }
            
            # Create session with cookies
            session = requests.Session()
            session.get("https://www.nseindia.com", headers=headers, timeout=10)
            
            response = session.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    # Extract symbols, exclude the index itself
                    symbols = [item['symbol'] for item in data['data'] 
                              if item.get('symbol') and not item['symbol'].startswith('NIFTY')]
                    return symbols
            
        except Exception as e:
            print(f"   ⚠️ Could not fetch constituents for {index_name}: {e}")
        
        return []
    
    def find_stock_token(self, symbol: str) -> Optional[str]:
        """
        Find instrument token for a stock symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Token string or None
        """
        if self.instrument_df is None:
            self.load_instrument_master()
        
        if self.instrument_df is None:
            return None
        
        # Search in NSE equity segment
        matches = self.instrument_df[
            (self.instrument_df['exch_seg'] == 'NSE') &
            (self.instrument_df['symbol'].str.upper() == symbol.upper()) &
            (self.instrument_df['instrumenttype'] == '')  # Empty for equity
        ]
        
        if len(matches) > 0:
            return str(matches.iloc[0]['token'])
        
        # Try with -EQ suffix
        matches = self.instrument_df[
            (self.instrument_df['exch_seg'] == 'NSE') &
            (self.instrument_df['symbol'].str.upper() == f"{symbol.upper()}-EQ")
        ]
        
        if len(matches) > 0:
            return str(matches.iloc[0]['token'])
        
        return None
    
    def get_futures_available(self, symbol: str) -> bool:
        """
        Check if futures are available for a stock
        
        Args:
            symbol: Stock symbol
            
        Returns:
            True if futures available
        """
        if self.instrument_df is None:
            self.load_instrument_master()
        
        if self.instrument_df is None:
            return False
        
        futures = self.instrument_df[
            (self.instrument_df['exch_seg'] == 'NFO') &
            (self.instrument_df['instrumenttype'] == 'FUTSTK') &
            (self.instrument_df['name'].str.upper() == symbol.upper())
        ]
        
        return len(futures) > 0
    
    def get_options_available(self, symbol: str) -> bool:
        """
        Check if options are available for a stock
        
        Args:
            symbol: Stock symbol
            
        Returns:
            True if options available
        """
        if self.instrument_df is None:
            self.load_instrument_master()
        
        if self.instrument_df is None:
            return False
        
        options = self.instrument_df[
            (self.instrument_df['exch_seg'] == 'NFO') &
            (self.instrument_df['instrumenttype'] == 'OPTSTK') &
            (self.instrument_df['name'].str.upper() == symbol.upper())
        ]
        
        return len(options) > 0
    
    def get_lot_size(self, symbol: str) -> Optional[int]:
        """
        Get lot size for F&O stock
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Lot size or None
        """
        if self.instrument_df is None:
            self.load_instrument_master()
        
        if self.instrument_df is None:
            return None
        
        # Get from futures contract
        futures = self.instrument_df[
            (self.instrument_df['exch_seg'] == 'NFO') &
            (self.instrument_df['instrumenttype'] == 'FUTSTK') &
            (self.instrument_df['name'].str.upper() == symbol.upper())
        ]
        
        if len(futures) > 0:
            return int(futures.iloc[0]['lotsize'])
        
        return None
    
    def get_strike_interval(self, symbol: str) -> float:
        """
        Get strike interval for a stock's options
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Strike interval
        """
        if self.instrument_df is None:
            self.load_instrument_master()
        
        if self.instrument_df is None:
            return 50  # Default
        
        # Get options for the symbol
        options = self.instrument_df[
            (self.instrument_df['exch_seg'] == 'NFO') &
            (self.instrument_df['instrumenttype'] == 'OPTSTK') &
            (self.instrument_df['name'].str.upper() == symbol.upper())
        ]
        
        if len(options) >= 2:
            # Get unique strikes and find interval
            strikes = sorted(options['strike'].astype(float).unique())
            if len(strikes) >= 2:
                # Strike is stored in paise (×100)
                interval = (strikes[1] - strikes[0]) / 100
                return interval
        
        # Default intervals based on typical ranges
        return 50  # Most stocks have 50 interval
