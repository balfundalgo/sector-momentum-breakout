"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                          ENTRY MONITOR MODULE                                  ║
║     Monitors for 2 consecutive candles breaking PDH (bullish) or PDL (bearish)║
║                                                                                ║
║  HYBRID APPROACH (to eliminate AB1004 rate limit errors):                      ║
║  - WebSocket detects 5-minute candle boundaries                                ║
║  - Only fetch candle data ONCE when candle completes                           ║
║  - No continuous polling during entry monitoring                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import time
import threading
import os
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    ENTRY_CUTOFF, MONITORING_CANDLE_MINUTES,
    SECOND_CANDLE_MAX_RANGE_PCT, CANDLE_CHECK_INTERVAL
)


class EntryMonitor:
    """
    Monitors price action for valid entry conditions.
    
    Uses HYBRID APPROACH:
    - WebSocket detects 5-minute candle boundaries
    - Only fetches candle from API once when candle completes
    - Eliminates continuous polling and AB1004 rate limit errors
    """
    
    def __init__(self, api, data_fetcher, logger):
        """
        Initialize entry monitor
        
        Args:
            api: AngelOneAPI instance
            data_fetcher: DataFetcher instance
            logger: StrategyLogger instance
        """
        self.api = api
        self.data_fetcher = data_fetcher
        self.logger = logger
        
        self.stock = None
        self.trend = None
        self.pdh = None  # Previous Day High
        self.pdl = None  # Previous Day Low
        self.prev_close = None
        
        self.candle_history = []
        self.entry_triggered = False
        self.entry_data = None
        
        # HYBRID APPROACH: Track minute boundaries for candle completion
        self._last_minute = None
        self._candle_ready = threading.Event()
        self._latest_candle = None
        self._sync_scheduled = False
        self._stop_monitoring = False
        self.API_SYNC_DELAY = 5  # Seconds to wait after candle close
    
    def setup(self, stock: Dict, trend: str) -> bool:
        """
        Setup the monitor with stock and trend
        
        Args:
            stock: Stock data dict
            trend: 'BULLISH' or 'BEARISH'
            
        Returns:
            True if setup successful
        """
        self.stock = stock
        self.trend = trend
        self.candle_history = []
        self.entry_triggered = False
        self.entry_data = None
        
        self.logger.print_banner("ENTRY MONITORING PHASE")
        self.logger.info(f"📊 Setting up monitor for {stock['symbol']} ({trend})")
        print(f"\n   Setting up entry monitor for {stock['symbol']}...")
        
        # Fetch previous day data (EXACT values required)
        print(f"   📊 Fetching exact PDH/PDL for {stock['symbol']}...")
        prev_day_data = self.data_fetcher.get_previous_day_data(
            stock['symbol'], 
            stock['token']
        )
        
        if not prev_day_data:
            self.logger.error(f"❌ Could not fetch previous day data for {stock['symbol']}")
            print(f"\n   ❌ ERROR: Could not fetch exact PDH/PDL data for {stock['symbol']}")
            print(f"   ❌ Strategy requires exact PDH/PDL values - cannot proceed with estimates")
            print(f"   💡 Try restarting the strategy in a few minutes (API rate limit may have triggered)")
            return False
        
        # CRITICAL: Reject estimated values
        is_estimated = prev_day_data.get('estimated', False)
        if is_estimated:
            self.logger.error(f"❌ Only estimated PDH/PDL available for {stock['symbol']} - REJECTED")
            print(f"\n   ❌ ERROR: Only estimated PDH/PDL available for {stock['symbol']}")
            print(f"   ❌ Strategy requires EXACT PDH/PDL values - cannot use estimates")
            print(f"   💡 Try restarting the strategy in a few minutes (API rate limit may have triggered)")
            return False
        
        self.pdh = prev_day_data.get('high')
        self.pdl = prev_day_data.get('low')
        self.prev_close = prev_day_data.get('close')
        
        print(f"\n   ╔{'═' * 55}╗")
        print(f"   ║  ENTRY MONITORING SETUP")
        print(f"   ╠{'═' * 55}╣")
        print(f"   ║  Stock:          {stock['symbol']:<30}")
        print(f"   ║  Trend:          {trend:<30}")
        print(f"   ║  Previous Day High (PDH): {self.pdh:>15.2f} ✅ EXACT")
        print(f"   ║  Previous Day Low (PDL):  {self.pdl:>15.2f} ✅ EXACT")
        print(f"   ║  Previous Close:          {self.prev_close:>15.2f}")
        print(f"   ╠{'═' * 55}╣")
        
        if trend == 'BULLISH':
            print(f"   ║  🎯 Looking for: 2 consecutive 5-min closes ABOVE PDH")
            print(f"   ║  📏 2nd candle range must be ≤ {SECOND_CANDLE_MAX_RANGE_PCT}%")
        else:
            print(f"   ║  🎯 Looking for: 2 consecutive 5-min closes BELOW PDL")
            print(f"   ║  📏 2nd candle range must be ≤ {SECOND_CANDLE_MAX_RANGE_PCT}%")
        
        print(f"   ║  ⏰ Entry cutoff: {ENTRY_CUTOFF}")
        print(f"   ╚{'═' * 55}╝\n")
        
        self.logger.log_event('ENTRY_MONITOR_SETUP', {
            'symbol': stock['symbol'],
            'trend': trend,
            'pdh': self.pdh,
            'pdl': self.pdl,
            'prev_close': self.prev_close,
            'exact_values': True
        })
        
        return True
    
    def get_current_candle(self, max_retries: int = 3) -> Optional[Dict]:
        """
        Get the current/latest completed 5-minute candle.
        
        HYBRID APPROACH: This is only called ONCE per 5 minutes,
        so we can afford slightly longer delays on retry.
        
        Args:
            max_retries: Number of retry attempts for API calls
            
        Returns:
            Dict with candle data
        """
        now = datetime.now()
        
        # Calculate the last completed 5-minute candle
        minutes = now.minute
        candle_end_minute = (minutes // MONITORING_CANDLE_MINUTES) * MONITORING_CANDLE_MINUTES
        
        candle_end = now.replace(minute=candle_end_minute, second=0, microsecond=0)
        candle_start = candle_end - timedelta(minutes=MONITORING_CANDLE_MINUTES)
        
        from_time = candle_start.strftime("%Y-%m-%d %H:%M")
        to_time = candle_end.strftime("%Y-%m-%d %H:%M")
        
        # Retry logic for API failures
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    # Wait between retries (HYBRID: only called once per 5 min anyway)
                    delay = 3.0 + (attempt * 2.0)  # 3s, 5s, 7s
                    print(f"   ⏳ Retry {attempt}/{max_retries-1} for candle data (waiting {delay}s)...")
                    time.sleep(delay)
                
                df = self.api.get_historical_data(
                    exchange="NSE",
                    symbol=self.stock['symbol'],
                    token=self.stock['token'],
                    interval="FIVE_MINUTE",
                    from_date=from_time,
                    to_date=to_time
                )
                
                if df is not None and len(df) > 0:
                    candle = df.iloc[-1]
                    
                    candle_data = {
                        'timestamp': candle['timestamp'],
                        'open': float(candle['open']),
                        'high': float(candle['high']),
                        'low': float(candle['low']),
                        'close': float(candle['close']),
                        'volume': int(candle['volume']),
                        'range': float(candle['high']) - float(candle['low']),
                        'range_pct': ((float(candle['high']) - float(candle['low'])) / float(candle['close'])) * 100
                    }
                    
                    return candle_data
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    continue  # Retry
                self.logger.error(f"❌ Error fetching candle after {max_retries} attempts: {e}")
        
        return None
    
    def check_entry_condition(self, candle: Dict) -> Tuple[bool, str]:
        """
        Check if the candle meets entry condition
        
        Args:
            candle: Candle data dict
            
        Returns:
            Tuple of (is_valid, reason)
        """
        close = candle['close']
        range_pct = candle['range_pct']
        
        if self.trend == 'BULLISH':
            # For bullish: close must be above PDH
            if close > self.pdh:
                return True, f"Close {close:.2f} > PDH {self.pdh:.2f}"
            else:
                return False, f"Close {close:.2f} <= PDH {self.pdh:.2f}"
        else:
            # For bearish: close must be below PDL
            if close < self.pdl:
                return True, f"Close {close:.2f} < PDL {self.pdl:.2f}"
            else:
                return False, f"Close {close:.2f} >= PDL {self.pdl:.2f}"
    
    def check_second_candle_range(self, candle: Dict) -> Tuple[bool, str]:
        """
        Check if the second candle's range is within limit
        
        Args:
            candle: Candle data dict
            
        Returns:
            Tuple of (is_valid, reason)
        """
        range_pct = candle['range_pct']
        
        if range_pct <= SECOND_CANDLE_MAX_RANGE_PCT:
            return True, f"Range {range_pct:.2f}% <= {SECOND_CANDLE_MAX_RANGE_PCT}%"
        else:
            return False, f"Range {range_pct:.2f}% > {SECOND_CANDLE_MAX_RANGE_PCT}% (too volatile)"
    
    def monitor_for_entry(self) -> Optional[Dict]:
        """
        Monitor continuously for entry condition using HYBRID APPROACH.
        
        HYBRID APPROACH:
        - Wait for 5-minute boundary (calculated from clock)
        - Only fetch candle ONCE after boundary + delay
        - No continuous polling = No AB1004 errors!
        
        Returns:
            Dict with entry data if triggered, None otherwise
        """
        today = datetime.now().strftime("%Y-%m-%d")
        cutoff_time = datetime.strptime(f"{today} {ENTRY_CUTOFF}", "%Y-%m-%d %H:%M")
        
        consecutive_valid_candles = 0
        first_candle = None
        second_candle = None
        last_candle_time = None
        
        self.logger.info(f"🔍 Starting entry monitoring until {ENTRY_CUTOFF}...")
        print(f"   Monitoring 5-minute candles (HYBRID mode - no continuous polling)...")
        print(f"   {'─' * 60}")
        
        # Track the last candle slot we've processed
        last_processed_slot = None
        
        while datetime.now() < cutoff_time:
            current_time = datetime.now()
            
            # Calculate current 5-minute slot
            current_slot = current_time.minute // MONITORING_CANDLE_MINUTES
            
            # Calculate seconds until next candle boundary
            next_boundary_minute = ((current_slot + 1) * MONITORING_CANDLE_MINUTES) % 60
            if next_boundary_minute == 0 and current_time.minute >= 55:
                next_boundary = current_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            else:
                next_boundary = current_time.replace(minute=next_boundary_minute, second=0, microsecond=0)
            
            seconds_to_boundary = (next_boundary - current_time).total_seconds()
            
            # HYBRID: Sleep until candle boundary + delay, then fetch ONCE
            if seconds_to_boundary > 0:
                # Calculate which candle will be complete after boundary
                completed_minute = (current_slot * MONITORING_CANDLE_MINUTES)
                
                # Only wait if we haven't processed this candle yet
                if last_processed_slot == current_slot:
                    # Already processed this candle, wait for next boundary
                    sleep_time = min(seconds_to_boundary + self.API_SYNC_DELAY, 300)
                    mins = int(sleep_time // 60)
                    secs = int(sleep_time % 60)
                    print(f"\r   ⏳ Next candle boundary in {mins}m {secs}s (:{next_boundary_minute:02d}), sleeping...          ", end="", flush=True)
                    
                    # Sleep in 1-second intervals to stay responsive
                    for _ in range(int(sleep_time)):
                        if datetime.now() >= cutoff_time:
                            break
                        time.sleep(1)
                    continue
            
            # Check if we should fetch a new candle
            if last_processed_slot != current_slot or last_processed_slot is None:
                # Wait for API sync delay after boundary
                if seconds_to_boundary < self.API_SYNC_DELAY:
                    wait_remaining = self.API_SYNC_DELAY - abs(seconds_to_boundary)
                    if wait_remaining > 0:
                        print(f"\r   🔔 Candle boundary detected! Fetching in {wait_remaining:.0f}s...          ", end="", flush=True)
                        time.sleep(wait_remaining)
                
                # Fetch the completed candle (ONLY ONCE per 5-minute period)
                print(f"\r   📡 Fetching completed candle...                              ", end="", flush=True)
                candle = self.get_current_candle()
                
                if candle is None:
                    # Failed to fetch, wait a bit and retry once
                    time.sleep(5)
                    candle = self.get_current_candle()
                    
                    if candle is None:
                        print(f"\n   ⚠️ Could not fetch candle, waiting for next...")
                        last_processed_slot = current_slot
                        continue
                
                last_processed_slot = current_slot
                candle_time = candle['timestamp']
                
                # Skip if same candle as last time
                if last_candle_time and candle_time == last_candle_time:
                    time.sleep(5)
                    continue
                
                last_candle_time = candle_time
                
                # Check entry condition
                is_valid, reason = self.check_entry_condition(candle)
                
                # Display candle
                indicator = "✅" if is_valid else "❌"
                print(f"\r   {indicator} Candle {candle_time}: O={candle['open']:.2f} H={candle['high']:.2f} "
                      f"L={candle['low']:.2f} C={candle['close']:.2f} Range={candle['range_pct']:.2f}%")
                print(f"      {reason}")
                
                if is_valid:
                    if consecutive_valid_candles == 0:
                        # First valid candle
                        first_candle = candle
                        consecutive_valid_candles = 1
                        print(f"      📍 First consecutive candle above/below level!")
                        
                    elif consecutive_valid_candles == 1:
                        # Second valid candle - check range
                        range_valid, range_reason = self.check_second_candle_range(candle)
                        print(f"      {range_reason}")
                        
                        if range_valid:
                            # Entry triggered!
                            second_candle = candle
                            consecutive_valid_candles = 2
                            
                            self.entry_triggered = True
                            self.entry_data = {
                                'first_candle': first_candle,
                                'second_candle': second_candle,
                                'entry_price': candle['close'],
                                'stop_loss': candle['low'] if self.trend == 'BULLISH' else candle['high'],
                                'trigger_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            
                            self._display_entry_trigger()
                            
                            self.logger.log_event('ENTRY_TRIGGERED', self.entry_data)
                            
                            return self.entry_data
                        else:
                            # Second candle too volatile, reset
                            print(f"      ⚠️ Second candle too volatile, resetting...")
                            consecutive_valid_candles = 0
                            first_candle = None
                else:
                    # Candle not valid, reset counter
                    if consecutive_valid_candles > 0:
                        print(f"      ⚠️ Sequence broken, resetting...")
                    consecutive_valid_candles = 0
                    first_candle = None
                
                self.candle_history.append(candle)
            time.sleep(CANDLE_CHECK_INTERVAL)
        
        # Cutoff time reached
        self.logger.warning(f"⏰ Entry cutoff reached ({ENTRY_CUTOFF}), no entry triggered")
        print(f"\n   ⏰ Entry cutoff time {ENTRY_CUTOFF} reached. No valid entry found.")
        
        return None
    
    def _display_entry_trigger(self):
        """
        Display entry trigger information
        """
        print(f"\n   ╔{'═' * 60}╗")
        print(f"   ║  🚀 ENTRY TRIGGERED!")
        print(f"   ╠{'═' * 60}╣")
        print(f"   ║  Stock:       {self.stock['symbol']:<40}")
        print(f"   ║  Trend:       {self.trend:<40}")
        print(f"   ║  Entry Price: {self.entry_data['entry_price']:>15.2f}")
        print(f"   ║  Stop Loss:   {self.entry_data['stop_loss']:>15.2f}")
        print(f"   ╠{'═' * 60}╣")
        print(f"   ║  First Candle:")
        print(f"   ║    Time:  {self.entry_data['first_candle']['timestamp']}")
        print(f"   ║    Close: {self.entry_data['first_candle']['close']:.2f}")
        print(f"   ║  Second Candle:")
        print(f"   ║    Time:  {self.entry_data['second_candle']['timestamp']}")
        print(f"   ║    Close: {self.entry_data['second_candle']['close']:.2f}")
        print(f"   ║    Range: {self.entry_data['second_candle']['range_pct']:.2f}%")
        print(f"   ╚{'═' * 60}╝\n")
    
    def get_entry_data(self) -> Optional[Dict]:
        """
        Get entry data if triggered
        
        Returns:
            Dict with entry data or None
        """
        return self.entry_data
    
    def is_entry_triggered(self) -> bool:
        """
        Check if entry has been triggered
        
        Returns:
            True if entry triggered
        """
        return self.entry_triggered
    
    def get_stop_loss(self) -> Optional[float]:
        """
        Get stop loss price
        
        Returns:
            Stop loss price or None
        """
        if self.entry_data:
            return self.entry_data['stop_loss']
        return None
    
    def get_entry_price(self) -> Optional[float]:
        """
        Get entry price
        
        Returns:
            Entry price or None
        """
        if self.entry_data:
            return self.entry_data['entry_price']
        return None
