"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         ANGEL ONE API WRAPPER                                  ║
║                    Handles all API interactions                                ║
║                    Now with WebSocket for real-time LTP                        ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import time
import pyotp
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from SmartApi import SmartConnect
from SmartApi.smartWebSocketV2 import SmartWebSocketV2

import sys
sys.path.append('..')
from config import (
    CLIENT_ID, API_KEY, MPIN, TOTP_SECRET,
    INSTRUMENT_MASTER_URL
)

# Import API rate limiter to prevent AB1004 errors
from api_rate_limiter import api_rate_limiter


class AngelOneAPI:
    """
    Wrapper class for Angel One SmartAPI with WebSocket support for real-time LTP
    """
    
    def __init__(self, use_websocket: bool = True):
        """
        Initialize API wrapper.
        
        Args:
            use_websocket: If True, use WebSocket for LTP data (recommended)
        """
        self.client_id = CLIENT_ID
        self.api_key = API_KEY
        self.mpin = MPIN
        self.totp_secret = TOTP_SECRET
        
        self.obj = None
        self.auth_token = None
        self.refresh_token = None
        self.feed_token = None
        
        self.instrument_df = None
        self.is_connected = False
        
        # WebSocket for real-time data
        self.use_websocket = use_websocket
        self.ws_manager = None
        
    def connect(self):
        """
        Establish connection to Angel One API and optionally WebSocket
        """
        try:
            print("\n🔌 Connecting to Angel One API...")
            
            # Generate TOTP
            totp = pyotp.TOTP(self.totp_secret).now()
            print(f"   Generated TOTP: {totp}")
            
            # Create SmartConnect object
            self.obj = SmartConnect(api_key=self.api_key)
            
            # Generate session
            data = self.obj.generateSession(self.client_id, self.mpin, totp)
            
            if data.get('status'):
                self.auth_token = data['data']['jwtToken']
                self.refresh_token = data['data']['refreshToken']
                self.feed_token = self.obj.getfeedToken()
                self.is_connected = True
                print(f"   ✅ Connected successfully!")
                print(f"   Client: {self.client_id}")
                
                # Initialize WebSocket if enabled
                if self.use_websocket:
                    self._init_websocket()
                
                return True
            else:
                print(f"   ❌ Connection failed: {data.get('message')}")
                return False
                
        except Exception as e:
            print(f"   ❌ Connection error: {e}")
            return False
    
    def _init_websocket(self):
        """Initialize WebSocket connection for real-time data."""
        try:
            from websocket_manager import WebSocketManager
            self.ws_manager = WebSocketManager(self.auth_token, self.feed_token, self.api_key)
            if self.ws_manager.connect():
                print("   ✅ WebSocket ready for real-time LTP")
            else:
                print("   ⚠️ WebSocket failed, will use REST API for LTP")
                self.ws_manager = None
        except Exception as e:
            print(f"   ⚠️ WebSocket init error: {e}, will use REST API")
            self.ws_manager = None
    
    def subscribe_symbols(self, symbols: List[Dict]) -> bool:
        """
        Subscribe to symbols for real-time data via WebSocket.
        
        Args:
            symbols: List of {"exchange": "NSE", "token": "99926000"}
            
        Returns:
            True if successful
        """
        if self.ws_manager and self.ws_manager.is_connected:
            return self.ws_manager.subscribe_symbols(symbols)
        return False
    
    def disconnect(self):
        """
        Logout from API and close WebSocket
        """
        try:
            # Close WebSocket first
            if self.ws_manager:
                self.ws_manager.disconnect()
                self.ws_manager = None
            
            if self.obj:
                self.obj.terminateSession(self.client_id)
                print("   ✅ Disconnected from Angel One API")
        except Exception as e:
            print(f"   ⚠️ Disconnect error: {e}")
    
    def download_instrument_master(self):
        """
        Download and cache instrument master
        """
        try:
            print("\n📥 Downloading instrument master...")
            self.instrument_df = pd.read_json(INSTRUMENT_MASTER_URL)
            print(f"   ✅ Downloaded {len(self.instrument_df)} instruments")
            return self.instrument_df
        except Exception as e:
            print(f"   ❌ Error downloading instrument master: {e}")
            return None
    
    def get_ltp(self, exchange, symbol, token):
        """
        Get Last Traded Price for a symbol.
        Uses WebSocket if available AND has valid close, else falls back to REST API.
        
        Note: WebSocket for indices may not provide 'closed_price' (previous close),
        so we need REST API to calculate percentage change.
        """
        ws_data = None
        
        # Try WebSocket first (no rate limits, real-time)
        if self.ws_manager and self.ws_manager.is_connected:
            quote = self.ws_manager.get_quote(exchange, str(token))
            if quote is not None and quote.get('ltp'):
                ws_close = quote.get('close', 0)
                
                # Only use WebSocket if we have valid close (needed for change calc)
                if ws_close and ws_close > 0:
                    return {
                        'ltp': quote.get('ltp'),
                        'close': ws_close,  # Previous close
                        'open': quote.get('open', 0),
                        'high': quote.get('high', 0),
                        'low': quote.get('low', 0),
                        'exchange': exchange,
                        'tradingsymbol': symbol,
                        'symboltoken': token
                    }
                else:
                    # Store WebSocket LTP for use with REST close
                    ws_data = quote
        
        # Fallback to REST API (needed for indices that don't have close in WebSocket)
        try:
            api_rate_limiter.wait("ltpData")  # Rate limit
            data = self.obj.ltpData(exchange, symbol, token)
            if data.get('status') and data.get('data'):
                rest_data = data['data']
                
                # If we have WebSocket LTP, use it (more real-time) with REST close
                if ws_data and ws_data.get('ltp'):
                    rest_data['ltp'] = ws_data['ltp']
                
                return rest_data
            return None
        except Exception as e:
            print(f"   ❌ LTP Error for {symbol}: {e}")
            return None
    
    def get_quote(self, exchange, symbol, token):
        """
        Get full quote data including OHLC.
        Uses WebSocket if available AND has valid close, else falls back to REST API.
        """
        ws_data = None
        
        # Try WebSocket first (has OHLC data in QUOTE mode)
        if self.ws_manager and self.ws_manager.is_connected:
            quote = self.ws_manager.get_quote(exchange, str(token))
            if quote is not None:
                ws_close = quote.get('close', 0)
                
                # Only use WebSocket if we have valid close
                if ws_close and ws_close > 0:
                    return {
                        'ltp': quote.get('ltp'),
                        'open': quote.get('open'),
                        'high': quote.get('high'),
                        'low': quote.get('low'),
                        'close': ws_close,
                        'exchange': exchange,
                        'tradingsymbol': symbol,
                        'symboltoken': token
                    }
                else:
                    # Store WebSocket data for hybrid use
                    ws_data = quote
        
        # Fallback to REST API
        try:
            api_rate_limiter.wait("ltpData")  # Rate limit
            data = self.obj.ltpData(exchange, symbol, token)
            if data.get('status') and data.get('data'):
                rest_data = data['data']
                
                # If we have WebSocket LTP, use it (more real-time)
                if ws_data and ws_data.get('ltp'):
                    rest_data['ltp'] = ws_data['ltp']
                
                return rest_data
            return None
        except Exception as e:
            print(f"   ❌ Quote Error for {symbol}: {e}")
            return None
    
    def get_historical_data(self, exchange, symbol, token, interval, from_date, to_date):
        """
        Get historical candle data
        
        Args:
            exchange: NSE, NFO, etc.
            symbol: Trading symbol
            token: Instrument token
            interval: ONE_MINUTE, FIVE_MINUTE, TEN_MINUTE, FIFTEEN_MINUTE, 
                     THIRTY_MINUTE, ONE_HOUR, ONE_DAY
            from_date: Start datetime string "YYYY-MM-DD HH:MM"
            to_date: End datetime string "YYYY-MM-DD HH:MM"
        """
        try:
            api_rate_limiter.wait("getCandleData")  # Rate limit - crucial for AB1004 prevention
            
            params = {
                "exchange": exchange,
                "symboltoken": token,
                "interval": interval,
                "fromdate": from_date,
                "todate": to_date
            }
            
            data = self.obj.getCandleData(params)
            
            if data.get('status') and data.get('data'):
                # Convert to DataFrame
                df = pd.DataFrame(data['data'], 
                                  columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                return df
            return None
            
        except Exception as e:
            print(f"   ❌ Historical data error for {symbol}: {e}")
            return None
    
    def place_order(self, variety, tradingsymbol, symboltoken, transactiontype,
                    exchange, ordertype, producttype, duration, price, quantity,
                    squareoff=0, stoploss=0, triggerprice=0):
        """
        Place an order
        
        Args:
            variety: NORMAL, STOPLOSS, AMO, ROBO
            tradingsymbol: Trading symbol
            symboltoken: Instrument token
            transactiontype: BUY, SELL
            exchange: NSE, NFO, BSE, MCX
            ordertype: MARKET, LIMIT, STOPLOSS_LIMIT, STOPLOSS_MARKET
            producttype: DELIVERY, CARRYFORWARD, MARGIN, INTRADAY, BO
            duration: DAY, IOC
            price: Price for LIMIT orders
            quantity: Number of shares/lots
            squareoff: Target price for bracket orders
            stoploss: Stoploss for bracket orders
            triggerprice: Trigger price for SL orders
        """
        try:
            api_rate_limiter.wait("placeOrder")  # Rate limit
            
            order_params = {
                "variety": variety,
                "tradingsymbol": tradingsymbol,
                "symboltoken": symboltoken,
                "transactiontype": transactiontype,
                "exchange": exchange,
                "ordertype": ordertype,
                "producttype": producttype,
                "duration": duration,
                "price": price,
                "quantity": quantity,
                "squareoff": squareoff,
                "stoploss": stoploss,
                "triggerprice": triggerprice
            }
            
            response = self.obj.placeOrder(order_params)
            return response
            
        except Exception as e:
            print(f"   ❌ Order placement error: {e}")
            return None
    
    def modify_order(self, order_id, variety, tradingsymbol, symboltoken,
                     exchange, ordertype, producttype, duration, price, quantity,
                     triggerprice=0):
        """
        Modify an existing order
        """
        try:
            api_rate_limiter.wait("modifyOrder")  # Rate limit
            
            modify_params = {
                "variety": variety,
                "orderid": order_id,
                "tradingsymbol": tradingsymbol,
                "symboltoken": symboltoken,
                "exchange": exchange,
                "ordertype": ordertype,
                "producttype": producttype,
                "duration": duration,
                "price": price,
                "quantity": quantity,
                "triggerprice": triggerprice
            }
            
            response = self.obj.modifyOrder(modify_params)
            return response
            
        except Exception as e:
            print(f"   ❌ Order modification error: {e}")
            return None
    
    def cancel_order(self, order_id, variety):
        """
        Cancel an order
        """
        try:
            api_rate_limiter.wait("cancelOrder")  # Rate limit
            response = self.obj.cancelOrder(order_id, variety)
            return response
        except Exception as e:
            print(f"   ❌ Order cancellation error: {e}")
            return None
    
    def get_order_book(self):
        """
        Get all orders for the day
        """
        try:
            api_rate_limiter.wait("orderBook")  # Rate limit
            return self.obj.orderBook()
        except Exception as e:
            print(f"   ❌ Order book error: {e}")
            return None
    
    def get_positions(self):
        """
        Get current positions
        """
        try:
            api_rate_limiter.wait("position")  # Rate limit
            return self.obj.position()
        except Exception as e:
            print(f"   ❌ Position error: {e}")
            return None
    
    def get_holdings(self):
        """
        Get holdings
        """
        try:
            return self.obj.holding()
        except Exception as e:
            print(f"   ❌ Holdings error: {e}")
            return None
    
    def search_instrument(self, exchange, search_text, instrument_type=None):
        """
        Search for instruments in the master
        """
        if self.instrument_df is None:
            self.download_instrument_master()
        
        if self.instrument_df is None:
            return []
        
        df = self.instrument_df
        
        # Filter by exchange
        df = df[df['exch_seg'] == exchange]
        
        # Filter by instrument type if provided
        if instrument_type:
            df = df[df['instrumenttype'] == instrument_type]
        
        # Search by symbol or name
        mask = (df['symbol'].str.upper().str.contains(search_text.upper(), na=False) |
                df['name'].str.upper().str.contains(search_text.upper(), na=False))
        
        return df[mask].to_dict('records')
    
    def get_option_chain(self, symbol, expiry_date=None):
        """
        Get option chain for a symbol
        """
        if self.instrument_df is None:
            self.download_instrument_master()
        
        if self.instrument_df is None:
            return None
        
        df = self.instrument_df
        
        # Filter for NFO exchange and the symbol
        nfo = df[(df['exch_seg'] == 'NFO') & 
                 (df['name'].str.upper() == symbol.upper())]
        
        if expiry_date:
            nfo = nfo[nfo['expiry'] == expiry_date]
        
        return nfo
    
    def get_future_contract(self, symbol, expiry_type='current_month'):
        """
        Get future contract for a symbol
        
        Args:
            symbol: Stock symbol
            expiry_type: 'current_month' or 'next_month'
        """
        if self.instrument_df is None:
            self.download_instrument_master()
        
        if self.instrument_df is None:
            return None
        
        df = self.instrument_df
        
        # Filter for NFO exchange, FUTSTK instrument type
        futures = df[(df['exch_seg'] == 'NFO') & 
                     (df['instrumenttype'] == 'FUTSTK') &
                     (df['name'].str.upper() == symbol.upper())]
        
        if futures.empty:
            return None
        
        # Sort by expiry
        futures = futures.sort_values('expiry')
        
        if expiry_type == 'current_month':
            return futures.iloc[0].to_dict() if len(futures) > 0 else None
        elif expiry_type == 'next_month':
            return futures.iloc[1].to_dict() if len(futures) > 1 else None
        
        return None
    
    def get_option_contract(self, symbol, strike, option_type, expiry_type='current_week'):
        """
        Get option contract for a symbol
        
        Args:
            symbol: Stock symbol
            strike: Strike price
            option_type: 'CE' or 'PE'
            expiry_type: 'current_week' or 'current_month'
        """
        if self.instrument_df is None:
            self.download_instrument_master()
        
        if self.instrument_df is None:
            return None
        
        df = self.instrument_df
        
        # Filter for NFO exchange, OPTSTK instrument type
        options = df[(df['exch_seg'] == 'NFO') & 
                     (df['instrumenttype'] == 'OPTSTK') &
                     (df['name'].str.upper() == symbol.upper()) &
                     (df['strike'].astype(float) == float(strike) * 100) &  # Strike stored as paise
                     (df['symbol'].str.endswith(option_type))]
        
        if options.empty:
            return None
        
        # Sort by expiry
        options = options.sort_values('expiry')
        
        if expiry_type == 'current_week':
            return options.iloc[0].to_dict() if len(options) > 0 else None
        elif expiry_type == 'current_month':
            # Find monthly expiry (usually last Thursday)
            for _, row in options.iterrows():
                expiry = pd.to_datetime(row['expiry'])
                # Check if it's a monthly expiry (last expiry of the month)
                if expiry.month != (expiry + timedelta(days=7)).month:
                    return row.to_dict()
            return options.iloc[0].to_dict() if len(options) > 0 else None
        
        return None
    
    def get_atm_strike(self, spot_price, strike_interval=50):
        """
        Calculate ATM strike price
        
        Args:
            spot_price: Current spot price
            strike_interval: Strike interval (50 for most stocks, 100 for indices)
        """
        return round(spot_price / strike_interval) * strike_interval


# Singleton instance
_api_instance = None

def get_api():
    """
    Get singleton API instance
    """
    global _api_instance
    if _api_instance is None:
        _api_instance = AngelOneAPI()
    return _api_instance
