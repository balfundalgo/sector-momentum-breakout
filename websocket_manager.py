"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         WEBSOCKET MANAGER                                      ║
║              Real-time LTP data via Angel One WebSocket                        ║
║                                                                               ║
║  Benefits over REST API:                                                       ║
║  - No rate limits (AB1004 errors eliminated)                                   ║
║  - Real-time updates (<10ms latency)                                          ║
║  - Push-based (no polling overhead)                                           ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import threading
import time
from datetime import datetime
from typing import Dict, Optional, List, Callable
from SmartApi.smartWebSocketV2 import SmartWebSocketV2

import sys
sys.path.append('..')
from config import CLIENT_ID, API_KEY


class WebSocketManager:
    """
    Manages WebSocket connection for real-time market data.
    
    Usage:
        ws_manager = WebSocketManager(auth_token, feed_token)
        ws_manager.connect()
        ws_manager.subscribe_symbols([
            {"exchange": "NSE", "token": "99926000"},  # NIFTY 50
            {"exchange": "NSE", "token": "99926009"},  # NIFTY BANK
        ])
        
        # Get latest LTP
        ltp = ws_manager.get_ltp("NSE", "99926000")
    """
    
    # Exchange type mapping for WebSocket
    EXCHANGE_MAP = {
        "NSE": 1,
        "NFO": 2,
        "BSE": 3,
        "MCX": 5,
        "CDS": 13
    }
    
    # Subscription modes
    MODE_LTP = 1
    MODE_QUOTE = 2
    MODE_SNAP_QUOTE = 3
    
    def __init__(self, auth_token: str, feed_token: str, api_key: str = None):
        """
        Initialize WebSocket manager.
        
        Args:
            auth_token: JWT token from login
            feed_token: Feed token for WebSocket
            api_key: API key (optional, uses config default)
        """
        self.auth_token = auth_token
        self.feed_token = feed_token
        self.api_key = api_key or API_KEY
        self.client_id = CLIENT_ID
        
        self.sws = None
        self.is_connected = False
        self.is_running = False
        
        # Thread-safe price storage
        self._lock = threading.Lock()
        self._prices: Dict[str, Dict] = {}  # key: "exchange_token" -> {ltp, open, high, low, close, volume, timestamp}
        
        # Subscribed tokens
        self._subscribed_tokens: List[Dict] = []
        
        # Callbacks
        self._on_price_update: Optional[Callable] = None
        self._on_connect: Optional[Callable] = None
        self._on_error: Optional[Callable] = None
        
    def set_callbacks(self, on_price_update: Callable = None, 
                      on_connect: Callable = None, 
                      on_error: Callable = None):
        """Set callback functions for WebSocket events."""
        self._on_price_update = on_price_update
        self._on_connect = on_connect
        self._on_error = on_error
        
    def connect(self) -> bool:
        """
        Establish WebSocket connection.
        
        Returns:
            True if connection successful
        """
        try:
            print("\n🔌 Connecting to WebSocket...")
            
            # Create WebSocket object
            self.sws = SmartWebSocketV2(
                self.auth_token,
                self.api_key,
                self.client_id,
                self.feed_token
            )
            
            # Set up event handlers
            self.sws.on_open = self._on_open
            self.sws.on_data = self._on_data
            self.sws.on_error = self._on_ws_error
            self.sws.on_close = self._on_close
            
            # Connect in a separate thread
            self.is_running = True
            self._ws_thread = threading.Thread(target=self._run_websocket, daemon=True)
            self._ws_thread.start()
            
            # Wait for connection (with timeout)
            timeout = 10
            start = time.time()
            while not self.is_connected and time.time() - start < timeout:
                time.sleep(0.1)
            
            if self.is_connected:
                print("   ✅ WebSocket connected!")
                return True
            else:
                print("   ❌ WebSocket connection timeout")
                return False
                
        except Exception as e:
            print(f"   ❌ WebSocket connection error: {e}")
            return False
    
    def _run_websocket(self):
        """Run WebSocket in separate thread."""
        try:
            self.sws.connect()
        except Exception as e:
            print(f"   ❌ WebSocket thread error: {e}")
            self.is_connected = False
            self.is_running = False
    
    def _on_open(self, wsapp):
        """Called when WebSocket connection opens."""
        self.is_connected = True
        print("   📡 WebSocket connection opened")
        
        # Re-subscribe to tokens if any
        if self._subscribed_tokens:
            self._do_subscribe(self._subscribed_tokens)
        
        if self._on_connect:
            self._on_connect()
    
    def _on_data(self, wsapp, message):
        """Called when data is received from WebSocket."""
        try:
            if isinstance(message, dict):
                # Extract data from message
                token = str(message.get('token', ''))
                exchange_type = message.get('exchange_type', 1)
                
                # Map exchange type back to string
                exchange = 'NSE'
                for ex, ex_type in self.EXCHANGE_MAP.items():
                    if ex_type == exchange_type:
                        exchange = ex
                        break
                
                key = f"{exchange}_{token}"
                
                # Extract price data
                price_data = {
                    'ltp': message.get('last_traded_price', 0) / 100,  # Convert from paise
                    'open': message.get('open_price_of_the_day', 0) / 100,
                    'high': message.get('high_price_of_the_day', 0) / 100,
                    'low': message.get('low_price_of_the_day', 0) / 100,
                    'close': message.get('closed_price', 0) / 100,
                    'volume': message.get('volume_trade_for_the_day', 0),
                    'timestamp': datetime.now(),
                    'exchange': exchange,
                    'token': token
                }
                
                # Store price data thread-safely
                with self._lock:
                    self._prices[key] = price_data
                
                # Call user callback if set
                if self._on_price_update:
                    self._on_price_update(price_data)
                    
        except Exception as e:
            print(f"   ⚠️ WebSocket data parsing error: {e}")
    
    def _on_ws_error(self, wsapp, error):
        """Called on WebSocket error."""
        print(f"   ⚠️ WebSocket error: {error}")
        if self._on_error:
            self._on_error(error)
    
    def _on_close(self, wsapp, close_status_code, close_msg):
        """Called when WebSocket connection closes."""
        self.is_connected = False
        print(f"   📡 WebSocket closed: {close_msg}")
    
    def subscribe_symbols(self, symbols: List[Dict], mode: int = None) -> bool:
        """
        Subscribe to symbols for real-time data.
        
        Args:
            symbols: List of {"exchange": "NSE", "token": "99926000"}
            mode: Subscription mode (default: MODE_LTP)
            
        Returns:
            True if subscription successful
        """
        if mode is None:
            mode = self.MODE_QUOTE  # Use QUOTE mode for more data
        
        # Store for re-subscription on reconnect
        self._subscribed_tokens = symbols
        
        if self.is_connected:
            return self._do_subscribe(symbols, mode)
        else:
            print("   ⚠️ WebSocket not connected, will subscribe on connect")
            return True
    
    def _do_subscribe(self, symbols: List[Dict], mode: int = None) -> bool:
        """Actually perform the subscription."""
        if mode is None:
            mode = self.MODE_QUOTE
            
        try:
            # Build token list in required format
            # Format: [{"exchangeType": 1, "tokens": ["99926000", "99926009"]}]
            exchange_tokens = {}
            
            for symbol in symbols:
                exchange = symbol.get('exchange', 'NSE')
                token = str(symbol.get('token', ''))
                
                exchange_type = self.EXCHANGE_MAP.get(exchange, 1)
                
                if exchange_type not in exchange_tokens:
                    exchange_tokens[exchange_type] = []
                exchange_tokens[exchange_type].append(token)
            
            # Convert to required format
            token_list = [
                {"exchangeType": ex_type, "tokens": tokens}
                for ex_type, tokens in exchange_tokens.items()
            ]
            
            # Subscribe
            self.sws.subscribe("correlation_id", mode, token_list)
            print(f"   ✅ Subscribed to {len(symbols)} symbols")
            return True
            
        except Exception as e:
            print(f"   ❌ Subscription error: {e}")
            return False
    
    def unsubscribe_symbols(self, symbols: List[Dict]) -> bool:
        """Unsubscribe from symbols."""
        try:
            # Build token list
            exchange_tokens = {}
            
            for symbol in symbols:
                exchange = symbol.get('exchange', 'NSE')
                token = str(symbol.get('token', ''))
                exchange_type = self.EXCHANGE_MAP.get(exchange, 1)
                
                if exchange_type not in exchange_tokens:
                    exchange_tokens[exchange_type] = []
                exchange_tokens[exchange_type].append(token)
            
            token_list = [
                {"exchangeType": ex_type, "tokens": tokens}
                for ex_type, tokens in exchange_tokens.items()
            ]
            
            self.sws.unsubscribe("correlation_id", self.MODE_QUOTE, token_list)
            
            # Remove from subscribed list
            for symbol in symbols:
                if symbol in self._subscribed_tokens:
                    self._subscribed_tokens.remove(symbol)
            
            return True
            
        except Exception as e:
            print(f"   ❌ Unsubscribe error: {e}")
            return False
    
    def get_ltp(self, exchange: str, token: str) -> Optional[float]:
        """
        Get latest LTP for a symbol.
        
        Args:
            exchange: Exchange (NSE, NFO, etc.)
            token: Instrument token
            
        Returns:
            LTP or None if not available
        """
        key = f"{exchange}_{token}"
        with self._lock:
            data = self._prices.get(key)
            if data:
                return data.get('ltp')
        return None
    
    def get_quote(self, exchange: str, token: str) -> Optional[Dict]:
        """
        Get full quote data for a symbol.
        
        Args:
            exchange: Exchange (NSE, NFO, etc.)
            token: Instrument token
            
        Returns:
            Dict with ltp, open, high, low, close, volume or None
        """
        key = f"{exchange}_{token}"
        with self._lock:
            return self._prices.get(key)
    
    def get_all_prices(self) -> Dict[str, Dict]:
        """Get all cached prices."""
        with self._lock:
            return self._prices.copy()
    
    def is_price_available(self, exchange: str, token: str) -> bool:
        """Check if price data is available for a symbol."""
        key = f"{exchange}_{token}"
        with self._lock:
            return key in self._prices
    
    def wait_for_price(self, exchange: str, token: str, timeout: float = 5.0) -> Optional[float]:
        """
        Wait for price to become available.
        
        Args:
            exchange: Exchange
            token: Token
            timeout: Maximum wait time in seconds
            
        Returns:
            LTP or None if timeout
        """
        key = f"{exchange}_{token}"
        start = time.time()
        
        while time.time() - start < timeout:
            with self._lock:
                if key in self._prices:
                    return self._prices[key].get('ltp')
            time.sleep(0.1)
        
        return None
    
    def disconnect(self):
        """Close WebSocket connection."""
        try:
            self.is_running = False
            if self.sws:
                self.sws.close_connection()
            self.is_connected = False
            print("   ✅ WebSocket disconnected")
        except Exception as e:
            print(f"   ⚠️ WebSocket disconnect error: {e}")


# Singleton instance
_ws_manager: Optional[WebSocketManager] = None


def get_websocket_manager() -> Optional[WebSocketManager]:
    """Get the global WebSocket manager instance."""
    return _ws_manager


def init_websocket_manager(auth_token: str, feed_token: str) -> WebSocketManager:
    """Initialize the global WebSocket manager."""
    global _ws_manager
    _ws_manager = WebSocketManager(auth_token, feed_token)
    return _ws_manager
