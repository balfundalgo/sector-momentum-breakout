"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         TREND IDENTIFIER MODULE                                ║
║          Analyzes first 10-minute NIFTY 50 candle to determine trend          ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

from datetime import datetime, timedelta
from typing import Optional, Dict
import time

import sys
import os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    TREND_START, TREND_END, TREND_CANDLE_MINUTES,
    NIFTY_50_TOKEN, NIFTY_50_SYMBOL, NIFTY_50_EXCHANGE
)


class TrendIdentifier:
    """
    Identifies market trend based on first 10-minute NIFTY 50 candle
    """
    
    def __init__(self, api, logger):
        """
        Initialize trend identifier
        
        Args:
            api: AngelOneAPI instance
            logger: StrategyLogger instance
        """
        self.api = api
        self.logger = logger
        self.trend = None
        self.candle_data = None
    
    def wait_for_trend_candle(self) -> Optional[str]:
        """
        Wait for the trend candle to complete and identify trend
        
        Returns:
            'BULLISH', 'BEARISH', or None if error
        """
        self.logger.print_banner("TREND IDENTIFICATION PHASE")
        
        today = datetime.now().strftime("%Y-%m-%d")
        trend_end_time = datetime.strptime(f"{today} {TREND_END}", "%Y-%m-%d %H:%M")
        
        current_time = datetime.now()
        
        # Check if market has started
        market_start = datetime.strptime(f"{today} {TREND_START}", "%Y-%m-%d %H:%M")
        if current_time < market_start:
            wait_seconds = (market_start - current_time).total_seconds()
            self.logger.info(f"⏰ Waiting for market to open... ({wait_seconds:.0f} seconds)")
            print(f"\n   Waiting for market to open at {TREND_START}...")
            time.sleep(wait_seconds)
        
        # Check if we need to wait for candle completion
        if current_time < trend_end_time:
            wait_seconds = (trend_end_time - current_time).total_seconds() + 5  # Add buffer
            self.logger.info(f"⏰ Waiting for trend candle to complete... ({wait_seconds:.0f} seconds)")
            print(f"\n   Waiting for 10-minute candle to close at {TREND_END}...")
            print(f"   Time remaining: {wait_seconds:.0f} seconds")
            time.sleep(wait_seconds)
        
        # Fetch the trend candle
        return self.identify_trend()
    
    def identify_trend(self) -> Optional[str]:
        """
        Fetch and analyze the first 10-minute candle
        
        Returns:
            'BULLISH', 'BEARISH', or None if error
        """
        today = datetime.now().strftime("%Y-%m-%d")
        from_time = f"{today} {TREND_START}"
        to_time = f"{today} {TREND_END}"
        
        self.logger.info(f"📊 Fetching NIFTY 50 candle: {from_time} to {to_time}")
        print(f"\n   Fetching NIFTY 50 10-minute candle...")
        
        # Retry logic for API failures (AB1004 errors)
        max_retries = 5
        df = None
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    # Progressive delay after error
                    delay = 3.0 + (attempt * 2.0)  # 3s, 5s, 7s, 9s
                    print(f"   ⏳ Retry {attempt}/{max_retries-1} for trend candle (waiting {delay}s)...")
                    time.sleep(delay)
                
                # Fetch historical candle data
                df = self.api.get_historical_data(
                    exchange=NIFTY_50_EXCHANGE,
                    symbol=NIFTY_50_SYMBOL,
                    token=NIFTY_50_TOKEN,
                    interval="TEN_MINUTE",
                    from_date=from_time,
                    to_date=to_time
                )
                
                if df is not None and len(df) > 0:
                    break  # Success!
                    
            except Exception as e:
                self.logger.warning(f"⚠️ Attempt {attempt+1} failed: {e}")
                if attempt == max_retries - 1:
                    self.logger.error("❌ All retries exhausted for trend candle")
        
        if df is None or len(df) == 0:
            self.logger.error("❌ Could not fetch NIFTY 50 candle data")
            print("   ❌ Error: Could not fetch candle data after retries")
            return None
        
        # Get the first candle
        candle = df.iloc[0]
        
        self.candle_data = {
            'timestamp': candle['timestamp'],
            'open': float(candle['open']),
            'high': float(candle['high']),
            'low': float(candle['low']),
            'close': float(candle['close']),
            'volume': int(candle['volume'])
        }
        
        # Determine trend
        is_green = self.candle_data['close'] > self.candle_data['open']
        self.trend = 'BULLISH' if is_green else 'BEARISH'
        
        # Calculate candle metrics
        body = abs(self.candle_data['close'] - self.candle_data['open'])
        range_total = self.candle_data['high'] - self.candle_data['low']
        body_pct = (body / self.candle_data['open']) * 100
        
        # Log results
        self.logger.info(f"📊 NIFTY 50 Candle: O={self.candle_data['open']:.2f}, "
                       f"H={self.candle_data['high']:.2f}, L={self.candle_data['low']:.2f}, "
                       f"C={self.candle_data['close']:.2f}")
        self.logger.info(f"📊 Trend Identified: {self.trend}")
        
        # Display to console
        print(f"\n   ╔{'═' * 50}╗")
        print(f"   ║  NIFTY 50 FIRST 10-MINUTE CANDLE ({TREND_START}-{TREND_END})")
        print(f"   ╠{'═' * 50}╣")
        print(f"   ║  Open:   {self.candle_data['open']:>12.2f}")
        print(f"   ║  High:   {self.candle_data['high']:>12.2f}")
        print(f"   ║  Low:    {self.candle_data['low']:>12.2f}")
        print(f"   ║  Close:  {self.candle_data['close']:>12.2f}")
        print(f"   ║  Volume: {self.candle_data['volume']:>12,}")
        print(f"   ╠{'═' * 50}╣")
        
        if is_green:
            print(f"   ║  🟢 BULLISH CANDLE (Close > Open)")
            print(f"   ║  → Strategy: BUY setup on BEST sector")
        else:
            print(f"   ║  🔴 BEARISH CANDLE (Close < Open)")
            print(f"   ║  → Strategy: SELL setup on WORST sector")
        
        print(f"   ╚{'═' * 50}╝\n")
        
        # Log event
        self.logger.log_event('TREND_IDENTIFIED', {
            'trend': self.trend,
            'candle': self.candle_data,
            'body_pct': body_pct
        })
        
        return self.trend
    
    def get_trend(self) -> Optional[str]:
        """
        Get the identified trend
        
        Returns:
            'BULLISH', 'BEARISH', or None
        """
        return self.trend
    
    def get_candle_data(self) -> Optional[Dict]:
        """
        Get the trend candle data
        
        Returns:
            Dict with candle OHLCV
        """
        return self.candle_data
    
    def is_bullish(self) -> bool:
        """Check if trend is bullish"""
        return self.trend == 'BULLISH'
    
    def is_bearish(self) -> bool:
        """Check if trend is bearish"""
        return self.trend == 'BEARISH'
