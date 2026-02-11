"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                          STOCK SELECTOR MODULE                                 ║
║        Selects the best stock within a sector based on movement criteria       ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import time
import requests
from datetime import datetime
from typing import Optional, Dict, List

import sys
import os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    MAX_STOCK_MOVEMENT_PCT, MIN_STOCK_MOVEMENT_PCT,
    SECTOR_CONSTITUENTS_FALLBACK, SECTOR_CACHE_FILE
)


def _load_sector_cache() -> dict:
    """Load cached sector constituents from JSON file"""
    import json, os
    cache_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), SECTOR_CACHE_FILE)
    try:
        if os.path.exists(cache_path):
            with open(cache_path, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_sector_cache(sector_name: str, stocks: list):
    """Save successful live fetch to JSON cache for future fallback"""
    import json, os
    cache_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), SECTOR_CACHE_FILE)
    try:
        cache = {}
        if os.path.exists(cache_path):
            with open(cache_path, 'r') as f:
                cache = json.load(f)
        cache[sector_name] = stocks
        with open(cache_path, 'w') as f:
            json.dump(cache, f, indent=2)
    except Exception:
        pass  # Non-critical, don't crash if cache write fails


class StockSelector:
    """
    Selects the best tradeable stock within a sector
    """
    
    def __init__(self, api, data_fetcher, logger):
        """
        Initialize stock selector
        
        Args:
            api: AngelOneAPI instance
            data_fetcher: DataFetcher instance
            logger: StrategyLogger instance
        """
        self.api = api
        self.data_fetcher = data_fetcher
        self.logger = logger
        self.sector_stocks = {}
        self.selected_stock = None
    
    def _subscribe_stocks_to_websocket(self, symbols: List[str]):
        """
        Subscribe stock symbols to WebSocket for real-time LTP.
        This speeds up scanning by avoiding REST API rate limits.
        
        Args:
            symbols: List of stock symbols
        """
        if not self.api.ws_manager or not self.api.ws_manager.is_connected:
            return  # WebSocket not available, will use REST API
        
        # Find tokens for all symbols
        ws_symbols = []
        for symbol in symbols:
            token = self.data_fetcher.find_stock_token(symbol)
            if token:
                ws_symbols.append({"exchange": "NSE", "token": str(token)})
        
        if ws_symbols:
            self.api.subscribe_symbols(ws_symbols)
            # Wait briefly for initial data
            time.sleep(0.5)
    
    def get_sector_constituents(self, sector_name: str) -> List[str]:
        """
        Get list of stocks in a sector
        
        Args:
            sector_name: Name of the sector (e.g., "NIFTY BANK")
            
        Returns:
            List of stock symbols
        """
        self.logger.info(f"📋 Fetching constituents for {sector_name}...")
        print(f"\n   Fetching stocks in {sector_name}...")
        
        # Try to fetch from NSE dynamically
        stocks = self._fetch_nse_constituents(sector_name)
        
        if stocks:
            self.logger.info(f"   ✅ Fetched {len(stocks)} stocks from NSE")
            print(f"   ✅ Found {len(stocks)} stocks from NSE")
            # Save to cache for future fallback
            _save_sector_cache(sector_name, stocks)
            return stocks
        
        # Try cached data from previous successful fetch
        cache = _load_sector_cache()
        if sector_name in cache and cache[sector_name]:
            stocks = cache[sector_name]
            self.logger.info(f"   ⚠️ Using cached list: {len(stocks)} stocks")
            print(f"   ⚠️ Using cached list: {len(stocks)} stocks")
            return stocks
        
        # Last resort: hardcoded fallback
        if sector_name in SECTOR_CONSTITUENTS_FALLBACK:
            stocks = SECTOR_CONSTITUENTS_FALLBACK[sector_name]
            self.logger.info(f"   ⚠️ Using fallback list: {len(stocks)} stocks")
            print(f"   ⚠️ Using fallback list: {len(stocks)} stocks")
            return stocks
        
        self.logger.warning(f"   ❌ No constituents found for {sector_name}")
        return []
    
    def _fetch_nse_constituents(self, sector_name: str) -> List[str]:
        """
        Fetch sector constituents from multiple sources with fallback
        
        Sources (in priority order):
        1. niftyindices.com CSV files (Most reliable)
        2. NSE India API (May be blocked)
        
        Args:
            sector_name: Name of the sector
            
        Returns:
            List of stock symbols
        """
        # Method 1: Try niftyindices.com CSV (most reliable)
        stocks = self._fetch_from_niftyindices_csv(sector_name)
        if stocks:
            return stocks
        
        # Method 2: Try NSE India API
        stocks = self._fetch_from_nse_api(sector_name)
        if stocks:
            return stocks
        
        return []
    
    def _fetch_from_niftyindices_csv(self, sector_name: str) -> List[str]:
        """
        Fetch constituents from niftyindices.com CSV files
        """
        import pandas as pd
        from io import StringIO
        
        # CSV URL mapping
        csv_urls = {
            "NIFTY BANK": "https://niftyindices.com/IndexConstituent/ind_niftybanklist.csv",
            "NIFTY IT": "https://niftyindices.com/IndexConstituent/ind_niftyitlist.csv",
            "NIFTY PHARMA": "https://niftyindices.com/IndexConstituent/ind_niftypharmalist.csv",
            "NIFTY AUTO": "https://niftyindices.com/IndexConstituent/ind_niftyautolist.csv",
            "NIFTY METAL": "https://niftyindices.com/IndexConstituent/ind_niftymetallist.csv",
            "NIFTY REALTY": "https://niftyindices.com/IndexConstituent/ind_niftyrealtylist.csv",
            "NIFTY FMCG": "https://niftyindices.com/IndexConstituent/ind_niftyfmcglist.csv",
            "NIFTY ENERGY": "https://niftyindices.com/IndexConstituent/ind_niftyenergylist.csv",
            "NIFTY INFRA": "https://niftyindices.com/IndexConstituent/ind_niftyinfralist.csv",
            "NIFTY PSU BANK": "https://niftyindices.com/IndexConstituent/ind_niftypsubanklist.csv",
            "NIFTY PVT BANK": "https://niftyindices.com/IndexConstituent/ind_niftypvtbanklist.csv",
            "NIFTY MEDIA": "https://niftyindices.com/IndexConstituent/ind_niftymedialist.csv",
            "NIFTY FIN SERVICE": "https://niftyindices.com/IndexConstituent/ind_niftyfinservicelist.csv",
            "NIFTY COMMODITIES": "https://niftyindices.com/IndexConstituent/ind_niftycommoditieslist.csv",
            "NIFTY CONSUMPTION": "https://niftyindices.com/IndexConstituent/ind_niftyconsumptionlist.csv",
            "NIFTY MNC": "https://niftyindices.com/IndexConstituent/ind_niftymnclist.csv",
            "NIFTY PSE": "https://niftyindices.com/IndexConstituent/ind_niftypselist.csv",
            "NIFTY SERV SECTOR": "https://niftyindices.com/IndexConstituent/ind_niftyservicesectorlist.csv",
            "NIFTY HEALTHCARE": "https://niftyindices.com/IndexConstituent/ind_niftyhealthcarelist.csv",
            "NIFTY OIL & GAS": "https://niftyindices.com/IndexConstituent/ind_niftyoilandgaslist.csv",
        }
        
        if sector_name not in csv_urls:
            return []
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(csv_urls[sector_name], headers=headers, timeout=10)
            
            if response.status_code == 200:
                df = pd.read_csv(StringIO(response.text))
                
                # Find symbol column
                symbol_cols = ['Symbol', 'symbol', 'SYMBOL', 'Company Symbol']
                for col in symbol_cols:
                    if col in df.columns:
                        symbols = df[col].dropna().tolist()
                        symbols = [str(s).strip().upper() for s in symbols if s]
                        if symbols:
                            self.logger.info(f"   ✅ niftyindices.com: {len(symbols)} stocks")
                            return symbols
                
        except Exception as e:
            self.logger.warning(f"   ⚠️ niftyindices.com error: {e}")
        
        return []
    
    def _fetch_from_nse_api(self, sector_name: str) -> List[str]:
        """
        Fetch sector constituents from NSE India API
        """
        # NSE index name mapping
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
            "NIFTY PSE": "NIFTY%20PSE",
            "NIFTY SERV SECTOR": "NIFTY%20SERVICES%20SECTOR",
        }
        
        try:
            encoded_name = index_map.get(sector_name, sector_name.replace(" ", "%20"))
            url = f"https://www.nseindia.com/api/equity-stockIndices?index={encoded_name}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://www.nseindia.com/',
            }
            
            # Create session with cookies
            session = requests.Session()
            
            # First hit the main page to get cookies
            session.get("https://www.nseindia.com", headers=headers, timeout=10)
            time.sleep(0.5)
            
            # Now fetch the API
            response = session.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    # Extract symbols, exclude the index itself
                    symbols = [
                        item['symbol'] for item in data['data'] 
                        if item.get('symbol') and not item['symbol'].startswith('NIFTY')
                    ]
                    if symbols:
                        self.logger.info(f"   ✅ NSE API: {len(symbols)} stocks")
                    return symbols
            
        except Exception as e:
            self.logger.warning(f"   ⚠️ NSE API error: {e}")
        
        return []
    
    def scan_sector_stocks(self, sector_name: str, trend: str) -> List[Dict]:
        """
        Scan all stocks in a sector and calculate their movement
        
        Args:
            sector_name: Name of the sector
            trend: 'BULLISH' or 'BEARISH'
            
        Returns:
            List of stock data sorted by movement
        """
        stocks = self.get_sector_constituents(sector_name)
        
        if not stocks:
            return []
        
        self.logger.info(f"📊 Scanning {len(stocks)} stocks in {sector_name}...")
        print(f"\n   Scanning stocks for movement...\n")
        
        # Pre-subscribe stocks to WebSocket for faster LTP fetching
        self._subscribe_stocks_to_websocket(stocks)
        
        results = []
        
        for symbol in stocks:
            try:
                # Find token for the stock
                token = self.data_fetcher.find_stock_token(symbol)
                
                if not token:
                    continue
                
                # Get LTP and calculate change from previous close
                stock_data = self.data_fetcher.get_stock_ltp_with_change(symbol, token)
                
                if not stock_data:
                    continue
                
                ltp = stock_data['ltp']
                prev_close = stock_data['prev_close']
                change_pct = stock_data['change_pct']
                
                # Check if F&O available
                has_futures = self.data_fetcher.get_futures_available(symbol)
                has_options = self.data_fetcher.get_options_available(symbol)
                
                if not (has_futures and has_options):
                    self.logger.debug(f"   ⚠️ {symbol}: No F&O available, skipping")
                    continue
                
                # Get lot size
                lot_size = self.data_fetcher.get_lot_size(symbol)
                
                stock_info = {
                    'symbol': symbol,
                    'token': token,
                    'ltp': ltp,
                    'prev_close': prev_close,
                    'change': stock_data['change'],
                    'change_pct': change_pct,
                    'abs_change_pct': abs(change_pct),
                    'has_futures': has_futures,
                    'has_options': has_options,
                    'lot_size': lot_size or 1
                }
                
                results.append(stock_info)
                
                # Display progress
                indicator = "🟢" if change_pct > 0 else "🔴" if change_pct < 0 else "⚪"
                print(f"   {indicator} {symbol:<15} LTP: {ltp:>10.2f}  Change: {change_pct:>+6.2f}%  F&O: ✅")
                
            except Exception as e:
                self.logger.debug(f"   ⚠️ Error scanning {symbol}: {e}")
            
            # Rate limiting is now handled by api_rate_limiter in angel_api.py
        
        # Sort based on trend
        if trend == 'BULLISH':
            # For bullish, sort by positive change (highest first)
            results = sorted(results, key=lambda x: x['change_pct'], reverse=True)
        else:
            # For bearish, sort by negative change (most negative first)
            results = sorted(results, key=lambda x: x['change_pct'])
        
        self.sector_stocks[sector_name] = results
        
        self.logger.info(f"📊 Found {len(results)} F&O stocks in {sector_name}")
        
        return results
    
    def select_best_stock(self, sector_name: str, trend: str) -> Optional[Dict]:
        """
        Select the best stock based on movement criteria
        
        Criteria:
        - For BULLISH: Highest positive movement <= 3%
        - For BEARISH: Most negative movement >= -3%
        - Stock must have F&O available
        
        Args:
            sector_name: Name of the sector
            trend: 'BULLISH' or 'BEARISH'
            
        Returns:
            Dict with selected stock data or None
        """
        self.logger.print_banner("STOCK SELECTION PHASE")
        
        stocks = self.scan_sector_stocks(sector_name, trend)
        
        if not stocks:
            self.logger.error(f"❌ No tradeable stocks found in {sector_name}")
            print(f"\n   ❌ No tradeable stocks found in {sector_name}")
            return None
        
        # Filter by movement criteria
        max_movement = MAX_STOCK_MOVEMENT_PCT
        min_movement = MIN_STOCK_MOVEMENT_PCT
        
        selected = None
        
        for stock in stocks:
            change_pct = stock['change_pct']
            
            if trend == 'BULLISH':
                # For bullish: positive movement, not more than max
                if min_movement < change_pct <= max_movement:
                    selected = stock
                    break
                elif change_pct > max_movement:
                    # Stock moved too much, continue to next
                    self.logger.info(f"   ⚠️ {stock['symbol']} moved {change_pct:.2f}% (> {max_movement}%), skipping")
                    continue
            else:
                # For bearish: negative movement, not more than -max
                if -max_movement <= change_pct < -min_movement:
                    selected = stock
                    break
                elif change_pct < -max_movement:
                    # Stock moved too much, continue to next
                    self.logger.info(f"   ⚠️ {stock['symbol']} moved {change_pct:.2f}% (< -{max_movement}%), skipping")
                    continue
        
        if selected:
            self.selected_stock = selected
            
            print(f"\n   ╔{'═' * 55}╗")
            print(f"   ║  SELECTED STOCK FOR {trend} TRADE")
            print(f"   ╠{'═' * 55}╣")
            print(f"   ║  Symbol:       {selected['symbol']:<35}")
            print(f"   ║  LTP:          {selected['ltp']:>15.2f}")
            print(f"   ║  Prev Close:   {selected['prev_close']:>15.2f}")
            print(f"   ║  Change:       {selected['change_pct']:>+14.2f}%")
            print(f"   ║  Lot Size:     {selected['lot_size']:>15}")
            print(f"   ╚{'═' * 55}╝\n")
            
            self.logger.log_event('STOCK_SELECTED', {
                'sector': sector_name,
                'trend': trend,
                'symbol': selected['symbol'],
                'change_pct': selected['change_pct']
            })
            
            return selected
        else:
            self.logger.warning(f"⚠️ No stock met the criteria (movement between {min_movement}% and {max_movement}%)")
            print(f"\n   ⚠️ No stock found with movement between {min_movement}% and {max_movement}%")
            return None
    
    def get_selected_stock(self) -> Optional[Dict]:
        """
        Get the currently selected stock
        
        Returns:
            Dict with stock data or None
        """
        return self.selected_stock
    
    def display_stock_ranking(self, sector_name: str):
        """
        Display all scanned stocks with their rankings
        
        Args:
            sector_name: Name of the sector
        """
        stocks = self.sector_stocks.get(sector_name, [])
        
        if not stocks:
            print(f"   No stocks scanned for {sector_name}")
            return
        
        print(f"\n   {'═' * 75}")
        print(f"   STOCKS IN {sector_name}")
        print(f"   {'─' * 75}")
        print(f"   {'Rank':<6}{'Symbol':<15}{'LTP':>12}{'Change':>12}{'Change %':>12}{'Status':>15}")
        print(f"   {'─' * 75}")
        
        for i, stock in enumerate(stocks, 1):
            change_pct = stock['change_pct']
            
            # Check if within criteria
            if abs(change_pct) <= MAX_STOCK_MOVEMENT_PCT:
                status = "✅ Eligible"
            else:
                status = f"❌ > {MAX_STOCK_MOVEMENT_PCT}%"
            
            indicator = "🟢" if change_pct > 0 else "🔴" if change_pct < 0 else "⚪"
            
            print(f"   {i:<6}{stock['symbol']:<15}{stock['ltp']:>12.2f}"
                  f"{stock['change']:>+12.2f}{change_pct:>+11.2f}% {indicator} {status}")
        
        print(f"   {'═' * 75}\n")
