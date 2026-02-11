"""
candle_builder.py - HYBRID OHLC BUILDER for 5-Minute Candles

GOAL:
- Use WebSocket to detect 5-minute candle boundaries
- Only call getCandleData ONCE when candle completes (not continuous polling)
- This eliminates AB1004 rate limit errors during entry monitoring

HYBRID APPROACH:
----------------
1. WebSocket receives ticks → detect minute boundary crossing
2. When minute % 5 == 0 (candle close), schedule REST API fetch after delay
3. Fallback polling every 5 minutes if WebSocket misses boundary

RESULT:
- Only ~1 API call per 5 minutes instead of continuous polling
- No AB1004 errors during entry monitoring
- Exact broker OHLC values (not approximated from ticks)

Adapted from working VWAP strategy's make_data.py
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable, Any
from logger import Logger


class CandleBuilder:
    """
    Hybrid 5-minute candle builder using WebSocket boundary detection + REST API.
    
    Usage:
        builder = CandleBuilder(api, logger, on_candle_complete_callback)
        builder.start_monitoring(symbol, token)
        # ... WebSocket will call builder.on_tick() for each price update
        # When 5-min candle completes, callback is called with candle data
    """
    
    def __init__(self, api, logger: Logger, on_candle_complete: Optional[Callable] = None):
        """
        Initialize candle builder.
        
        Args:
            api: AngelAPI instance for REST calls
            logger: Logger instance
            on_candle_complete: Callback function(candle_data: Dict) called when candle closes
        """
        self.api = api
        self.logger = logger
        self.on_candle_complete = on_candle_complete
        
        # Per-token tracking
        self.last_minute: Dict[str, int] = {}  # Track last seen minute per token
        self.sync_scheduled: Dict[str, bool] = {}  # Track if sync is scheduled
        self.latest_candles: Dict[str, Dict] = {}  # Store latest candle per token
        self.monitoring_tokens: Dict[str, Dict] = {}  # token -> {symbol, exchange}
        
        # Configuration
        self.CANDLE_MINUTES = 5
        self.API_SYNC_DELAY = 5  # Seconds to wait after boundary before API fetch
        
        # Thread control
        self._stop_event = threading.Event()
        self._fallback_threads: Dict[str, threading.Thread] = {}
    
    def start_monitoring(self, symbol: str, token: str, exchange: str = "NSE"):
        """
        Start monitoring a token for 5-minute candles.
        
        Args:
            symbol: Trading symbol (e.g., 'JINDALSTEL')
            token: Symbol token
            exchange: Exchange code (default: 'NSE')
        """
        token_str = str(token)
        
        # Store monitoring info
        self.monitoring_tokens[token_str] = {
            'symbol': symbol,
            'exchange': exchange
        }
        
        # Initialize tracking
        self.last_minute[token_str] = datetime.now().minute
        self.sync_scheduled[token_str] = False
        
        # Start fallback thread (backup in case WebSocket misses boundary)
        self._start_fallback_thread(token_str)
        
        self.logger.info(f"📡 Candle builder started for {symbol} (token: {token_str})")
    
    def stop_monitoring(self, token: str = None):
        """
        Stop monitoring.
        
        Args:
            token: Specific token to stop, or None to stop all
        """
        self._stop_event.set()
        
        if token:
            token_str = str(token)
            if token_str in self.monitoring_tokens:
                del self.monitoring_tokens[token_str]
        else:
            self.monitoring_tokens.clear()
    
    def on_tick(self, token: str, ltp: float, timestamp: datetime = None):
        """
        Called for each WebSocket tick. Detects candle boundaries.
        
        Args:
            token: Symbol token
            ltp: Last traded price
            timestamp: Tick timestamp (optional, uses now() if not provided)
        """
        token_str = str(token)
        
        if token_str not in self.monitoring_tokens:
            return
        
        now = timestamp or datetime.now()
        current_minute = now.minute
        
        # Check for candle boundary crossing
        if token_str in self.last_minute:
            prev_minute = self.last_minute[token_str]
            
            # Detect 5-minute boundary crossing
            # E.g., 14:44:59 → 14:45:00 means 14:40 candle is complete
            prev_candle_slot = prev_minute // self.CANDLE_MINUTES
            curr_candle_slot = current_minute // self.CANDLE_MINUTES
            
            if prev_candle_slot != curr_candle_slot:
                # Candle boundary detected!
                if not self.sync_scheduled.get(token_str, False):
                    self.sync_scheduled[token_str] = True
                    
                    # Calculate the completed candle's start time
                    completed_minute = prev_candle_slot * self.CANDLE_MINUTES
                    
                    symbol = self.monitoring_tokens[token_str]['symbol']
                    self.logger.info(
                        f"🔔 [HYBRID] {symbol}: Candle :{completed_minute:02d} boundary detected, "
                        f"syncing in {self.API_SYNC_DELAY}s..."
                    )
                    
                    # Schedule API fetch after delay
                    threading.Timer(
                        self.API_SYNC_DELAY, 
                        self._trigger_api_sync, 
                        args=(token_str,)
                    ).start()
        
        # Update last seen minute
        self.last_minute[token_str] = current_minute
    
    def _trigger_api_sync(self, token: str):
        """
        Called after API_SYNC_DELAY when candle boundary is detected.
        Fetches the completed candle from REST API.
        """
        token_str = str(token)
        
        try:
            candle = self._fetch_latest_candle(token_str)
            
            if candle:
                self.latest_candles[token_str] = candle
                symbol = self.monitoring_tokens.get(token_str, {}).get('symbol', token_str)
                
                self.logger.info(
                    f"✅ [HYBRID] {symbol}: Candle synced | "
                    f"{candle['timestamp']} | O={candle['open']:.2f} H={candle['high']:.2f} "
                    f"L={candle['low']:.2f} C={candle['close']:.2f}"
                )
                
                # Call callback if registered
                if self.on_candle_complete:
                    self.on_candle_complete(candle)
            else:
                symbol = self.monitoring_tokens.get(token_str, {}).get('symbol', token_str)
                self.logger.warning(f"⚠️ [HYBRID] {symbol}: API sync returned no data")
                
        except Exception as e:
            symbol = self.monitoring_tokens.get(token_str, {}).get('symbol', token_str)
            self.logger.warning(f"⚠️ [HYBRID] {symbol}: API sync error: {e}")
        finally:
            self.sync_scheduled[token_str] = False
    
    def _fetch_latest_candle(self, token: str) -> Optional[Dict]:
        """
        Fetch the latest completed 5-minute candle from REST API.
        
        Returns:
            Candle dict with keys: timestamp, open, high, low, close, volume, range_pct
        """
        token_str = str(token)
        info = self.monitoring_tokens.get(token_str)
        
        if not info:
            return None
        
        now = datetime.now()
        
        # Calculate the most recently completed candle's time range
        # If it's 14:47, the last complete candle is 14:40-14:45
        current_slot = now.minute // self.CANDLE_MINUTES
        candle_end_minute = current_slot * self.CANDLE_MINUTES
        candle_start_minute = candle_end_minute - self.CANDLE_MINUTES
        
        # Handle hour rollover
        if candle_start_minute < 0:
            candle_start_minute = 60 + candle_start_minute
            candle_start = now.replace(minute=candle_start_minute, second=0, microsecond=0) - timedelta(hours=1)
        else:
            candle_start = now.replace(minute=candle_start_minute, second=0, microsecond=0)
        
        candle_end = candle_start + timedelta(minutes=self.CANDLE_MINUTES)
        
        from_time = candle_start.strftime("%Y-%m-%d %H:%M")
        to_time = candle_end.strftime("%Y-%m-%d %H:%M")
        
        try:
            df = self.api.get_historical_data(
                exchange=info['exchange'],
                symbol=info['symbol'],
                token=token_str,
                interval="FIVE_MINUTE",
                from_date=from_time,
                to_date=to_time
            )
            
            if df is not None and len(df) > 0:
                candle = df.iloc[-1]
                
                candle_data = {
                    'token': token_str,
                    'symbol': info['symbol'],
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
            self.logger.error(f"Error fetching candle for {token_str}: {e}")
        
        return None
    
    def _start_fallback_thread(self, token: str):
        """
        Start fallback thread that syncs every 5 minutes in case WebSocket misses.
        """
        token_str = str(token)
        
        def fallback_loop():
            # Initial sync after 5 seconds
            time.sleep(5)
            if not self._stop_event.is_set():
                self._trigger_api_sync(token_str)
            
            while not self._stop_event.is_set():
                try:
                    # Sleep until next 5-minute mark + 10 seconds
                    now = datetime.now()
                    current_slot = now.minute // self.CANDLE_MINUTES
                    next_slot = current_slot + 1
                    next_minute = (next_slot * self.CANDLE_MINUTES) % 60
                    
                    next_time = now.replace(minute=next_minute, second=10, microsecond=0)
                    if next_time <= now:
                        next_time = next_time + timedelta(hours=1)
                    
                    sleep_seconds = (next_time - now).total_seconds()
                    
                    # Sleep in small intervals to check stop event
                    for _ in range(int(sleep_seconds)):
                        if self._stop_event.is_set():
                            return
                        time.sleep(1)
                    
                    # Only sync if WebSocket didn't already trigger it
                    if not self.sync_scheduled.get(token_str, False):
                        symbol = self.monitoring_tokens.get(token_str, {}).get('symbol', token_str)
                        self.logger.info(f"🔄 [FALLBACK] {symbol}: WebSocket missed boundary, syncing...")
                        self._trigger_api_sync(token_str)
                    
                except Exception as e:
                    self.logger.error(f"[FALLBACK] Error for {token_str}: {e}")
                    time.sleep(60)
        
        thread = threading.Thread(target=fallback_loop, daemon=True)
        thread.start()
        self._fallback_threads[token_str] = thread
    
    def get_latest_candle(self, token: str) -> Optional[Dict]:
        """
        Get the latest cached candle for a token.
        
        Returns:
            Candle dict or None
        """
        return self.latest_candles.get(str(token))
    
    def force_sync(self, token: str) -> Optional[Dict]:
        """
        Force an immediate sync for a token (bypasses boundary detection).
        
        Returns:
            Candle dict or None
        """
        token_str = str(token)
        candle = self._fetch_latest_candle(token_str)
        if candle:
            self.latest_candles[token_str] = candle
        return candle
