"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    SECTOR CONSTITUENTS FETCHER                                ║
║                                                                               ║
║   Fetches accurate stock lists for all NIFTY sectoral indices using          ║
║   multiple sources with automatic fallback                                    ║
║                                                                               ║
║   Sources (in priority order):                                                ║
║   1. niftyindices.com CSV files (Official, most reliable)                    ║
║   2. NSE India API (Real-time but may block requests)                        ║
║   3. nsetools library (Wrapper around NSE API)                               ║
║   4. Hardcoded fallback lists (Always works)                                 ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Usage:
    python fetch_sector_constituents.py
    python fetch_sector_constituents.py --update-config   # Update config.py with results
"""

import requests
import pandas as pd
import json
import time
from io import StringIO
from typing import Dict, List, Optional
import sys

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# Browser-like headers to avoid being blocked
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

# niftyindices.com CSV URL patterns
NIFTY_INDICES_CSV_URLS = {
    "NIFTY 50": "https://niftyindices.com/IndexConstituent/ind_nifty50list.csv",
    "NIFTY BANK": "https://niftyindices.com/IndexConstituent/ind_niftybanklist.csv",
    "NIFTY IT": "https://niftyindices.com/IndexConstituent/ind_niftyitlist.csv",
    "NIFTY PHARMA": "https://niftyindices.com/IndexConstituent/ind_niftypharmalist.csv",
    "NIFTY AUTO": "https://niftyindices.com/IndexConstituent/ind_niftyautolist.csv",
    "NIFTY METAL": "https://niftyindices.com/IndexConstituent/ind_niftymetallist.csv",
    "NIFTY FMCG": "https://niftyindices.com/IndexConstituent/ind_niftyfmcglist.csv",
    "NIFTY REALTY": "https://niftyindices.com/IndexConstituent/ind_niftyrealtylist.csv",
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

# NSE India API index mapping
NSE_API_INDEX_NAMES = {
    "NIFTY 50": "NIFTY 50",
    "NIFTY BANK": "NIFTY BANK",
    "NIFTY IT": "NIFTY IT",
    "NIFTY PHARMA": "NIFTY PHARMA",
    "NIFTY AUTO": "NIFTY AUTO",
    "NIFTY METAL": "NIFTY METAL",
    "NIFTY FMCG": "NIFTY FMCG",
    "NIFTY REALTY": "NIFTY REALTY",
    "NIFTY ENERGY": "NIFTY ENERGY",
    "NIFTY INFRA": "NIFTY INFRA",
    "NIFTY PSU BANK": "NIFTY PSU BANK",
    "NIFTY PVT BANK": "NIFTY PRIVATE BANK",
    "NIFTY MEDIA": "NIFTY MEDIA",
    "NIFTY FIN SERVICE": "NIFTY FINANCIAL SERVICES",
    "NIFTY COMMODITIES": "NIFTY COMMODITIES",
    "NIFTY CONSUMPTION": "NIFTY CONSUMPTION",
    "NIFTY MNC": "NIFTY MNC",
    "NIFTY PSE": "NIFTY PSE",
    "NIFTY SERV SECTOR": "NIFTY SERVICES SECTOR",
    "NIFTY HEALTHCARE": "NIFTY HEALTHCARE INDEX",
    "NIFTY OIL & GAS": "NIFTY OIL & GAS",
}

# Hardcoded fallback (Last resort - update periodically)
FALLBACK_CONSTITUENTS = {
    "NIFTY BANK": ["HDFCBANK", "ICICIBANK", "KOTAKBANK", "AXISBANK", "SBIN", 
                   "INDUSINDBK", "BANKBARODA", "PNB", "FEDERALBNK", "IDFCFIRSTB",
                   "AUBANK", "BANDHANBNK"],
    "NIFTY IT": ["TCS", "INFY", "HCLTECH", "WIPRO", "TECHM", "LTIM", "MPHASIS", 
                 "COFORGE", "PERSISTENT", "LTTS"],
    "NIFTY PHARMA": ["SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB", "APOLLOHOSP",
                     "LUPIN", "AUROPHARMA", "TORNTPHARM", "ZYDUSLIFE", "BIOCON",
                     "ALKEM", "IPCALAB", "GLENMARK", "NATCOPHARM", "LAURUSLABS"],
    "NIFTY AUTO": ["TATAMOTORS", "M&M", "MARUTI", "BAJAJ-AUTO", "HEROMOTOCO",
                   "EICHERMOT", "ASHOKLEY", "TVSMOTOR", "BHARATFORG", "BALKRISIND",
                   "BOSCHLTD", "MOTHERSON", "EXIDEIND", "MRF", "TIINDIA"],
    "NIFTY METAL": ["TATASTEEL", "HINDALCO", "JSWSTEEL", "COALINDIA", "VEDL",
                    "ADANIENT", "NMDC", "SAIL", "NATIONALUM", "JINDALSTEL",
                    "HINDZINC", "APLAPOLLO", "WELCORP", "RATNAMANI", "MOIL"],
    "NIFTY REALTY": ["DLF", "GODREJPROP", "OBEROIRLTY", "PRESTIGE", "PHOENIXLTD",
                     "BRIGADE", "SOBHA", "SUNTECK", "MAHLIFE", "LODHA"],
    "NIFTY FMCG": ["HINDUNILVR", "ITC", "NESTLEIND", "BRITANNIA", "TATACONSUM",
                   "GODREJCP", "DABUR", "MARICO", "COLPAL", "VBL",
                   "EMAMILTD", "MCDOWELL-N", "PGHH", "RADICO", "ZYDUSWELL"],
    "NIFTY ENERGY": ["RELIANCE", "ONGC", "NTPC", "POWERGRID", "ADANIGREEN",
                     "BPCL", "IOC", "GAIL", "TATAPOWER", "ADANIPOWER",
                     "PETRONET", "NHPC", "SJVN", "IGL", "MGL"],
    "NIFTY FIN SERVICE": ["HDFCBANK", "ICICIBANK", "BAJFINANCE", "BAJAJFINSV", "SBILIFE",
                          "HDFCLIFE", "AXISBANK", "SBIN", "KOTAKBANK", "ICICIGI",
                          "HDFCAMC", "SBICARD", "CHOLAFIN", "MUTHOOTFIN", "M&MFIN"],
    "NIFTY PSU BANK": ["SBIN", "BANKBARODA", "PNB", "CANBK", "UNIONBANK",
                       "INDIANB", "IOB", "BANKINDIA", "CENTRALBK", "UCOBANK",
                       "MAHABANK", "BANDHANBNK"],
    "NIFTY PVT BANK": ["HDFCBANK", "ICICIBANK", "KOTAKBANK", "AXISBANK", "INDUSINDBK",
                       "FEDERALBNK", "IDFCFIRSTB", "BANDHANBNK", "RBLBANK", "AUBANK",
                       "YESBANK", "CSBBANK"],
    "NIFTY INFRA": ["LARSEN", "ADANIPORTS", "ULTRACEMCO", "GRASIM", "ADANIENT",
                    "POWERGRID", "NTPC", "BHARTIARTL", "DLF", "SIEMENS",
                    "ABB", "IRCTC", "CONCOR", "GMRINFRA", "IRB"],
    "NIFTY MEDIA": ["ZEEL", "SUNTV", "PVR", "NETWORK18", "TV18BRDCST",
                    "DISHTV", "HATHWAY", "NAZARA", "TIPS", "SAREGAMA"],
    "NIFTY MNC": ["MARUTI", "BRITANNIA", "SIEMENS", "ABBINDIA", "HONAUT",
                  "BOSCHLTD", "GLAXO", "PFIZER", "WHIRLPOOL", "PAGEIND",
                  "PGHH", "3MINDIA", "GILLETTE", "CASTROLIND", "AKZOINDIA"],
    "NIFTY COMMODITIES": ["RELIANCE", "ONGC", "TATASTEEL", "HINDALCO", "COALINDIA",
                          "JSWSTEEL", "NTPC", "POWERGRID", "VEDL", "IOC",
                          "BPCL", "GAIL", "NMDC", "JINDALSTEL", "SAIL"],
    "NIFTY CONSUMPTION": ["HINDUNILVR", "ITC", "TITAN", "MARUTI", "NESTLEIND",
                          "BRITANNIA", "ASIANPAINT", "DABUR", "COLPAL", "MARICO",
                          "TATACONSUM", "GODREJCP", "PIDILITIND", "BERGEPAINT", "VBL"],
    "NIFTY SERV SECTOR": ["HDFCBANK", "ICICIBANK", "INFY", "TCS", "BHARTIARTL",
                          "KOTAKBANK", "AXISBANK", "SBIN", "LT", "BAJFINANCE",
                          "WIPRO", "HCLTECH", "TECHM", "ADANIPORTS", "LTIM"],
    "NIFTY PSE": ["ONGC", "NTPC", "POWERGRID", "COALINDIA", "IOC",
                  "BPCL", "GAIL", "BHEL", "RECLTD", "PFC",
                  "NHPC", "SJVN", "IRFC", "NMDC", "SAIL"],
    "NIFTY HEALTHCARE": ["APOLLOHOSP", "SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB",
                         "FORTIS", "MAXHEALTH", "LALPATHLAB", "METROPOLIS", "YATHARTH"],
    "NIFTY OIL & GAS": ["RELIANCE", "ONGC", "BPCL", "IOC", "GAIL",
                        "PETRONET", "IGL", "MGL", "HINDPETRO", "OIL",
                        "MRPL", "CHENNPETRO", "AEGISCHEM", "GSPL", "ATGL"],
}


class SectorConstituentsFetcher:
    """
    Fetches sector constituents from multiple sources with fallback
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.results = {}
        self.sources_used = {}
    
    # ─────────────────────────────────────────────────────────────────────────
    # Method 1: niftyindices.com CSV files
    # ─────────────────────────────────────────────────────────────────────────
    def fetch_from_niftyindices_csv(self, index_name: str) -> Optional[List[str]]:
        """
        Fetch constituents from niftyindices.com CSV files
        """
        if index_name not in NIFTY_INDICES_CSV_URLS:
            return None
        
        url = NIFTY_INDICES_CSV_URLS[index_name]
        
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                # Parse CSV
                df = pd.read_csv(StringIO(response.text))
                
                # Try to find symbol column
                symbol_cols = ['Symbol', 'symbol', 'SYMBOL', 'Company Symbol', 'Ticker']
                for col in symbol_cols:
                    if col in df.columns:
                        symbols = df[col].dropna().tolist()
                        return [str(s).strip().upper() for s in symbols if s]
                
                # If no symbol column found, try first column
                if len(df.columns) > 0:
                    symbols = df.iloc[:, 0].dropna().tolist()
                    return [str(s).strip().upper() for s in symbols if s and not s.startswith('Company')]
                    
        except Exception as e:
            print(f"   ⚠️ niftyindices.com error for {index_name}: {e}")
        
        return None
    
    # ─────────────────────────────────────────────────────────────────────────
    # Method 2: NSE India API
    # ─────────────────────────────────────────────────────────────────────────
    def fetch_from_nse_api(self, index_name: str) -> Optional[List[str]]:
        """
        Fetch constituents from NSE India API
        """
        if index_name not in NSE_API_INDEX_NAMES:
            return None
        
        nse_index_name = NSE_API_INDEX_NAMES[index_name]
        
        try:
            # First, visit main page to get cookies
            self.session.get("https://www.nseindia.com", timeout=10)
            time.sleep(0.5)
            
            # Then fetch the index data
            url = f"https://www.nseindia.com/api/equity-stockIndices?index={nse_index_name.replace(' ', '%20').replace('&', '%26')}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    symbols = []
                    for stock in data['data']:
                        if 'symbol' in stock and stock['symbol'] != nse_index_name:
                            symbols.append(stock['symbol'])
                    return symbols
                    
        except Exception as e:
            print(f"   ⚠️ NSE API error for {index_name}: {e}")
        
        return None
    
    # ─────────────────────────────────────────────────────────────────────────
    # Method 3: nsetools library
    # ─────────────────────────────────────────────────────────────────────────
    def fetch_from_nsetools(self, index_name: str) -> Optional[List[str]]:
        """
        Fetch constituents using nsetools library
        """
        try:
            from nsetools import Nse
            nse = Nse()
            
            # nsetools uses different index names
            nsetools_name = index_name
            
            # Try to get stocks in index
            stocks = nse.get_stocks_in_index(nsetools_name)
            if stocks and len(stocks) > 0:
                return stocks
                
        except ImportError:
            print("   ⚠️ nsetools not installed. Run: pip install nsetools")
        except Exception as e:
            print(f"   ⚠️ nsetools error for {index_name}: {e}")
        
        return None
    
    # ─────────────────────────────────────────────────────────────────────────
    # Method 4: Fallback hardcoded list
    # ─────────────────────────────────────────────────────────────────────────
    def fetch_from_fallback(self, index_name: str) -> Optional[List[str]]:
        """
        Return hardcoded fallback list
        """
        return FALLBACK_CONSTITUENTS.get(index_name)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Main fetch method with fallback
    # ─────────────────────────────────────────────────────────────────────────
    def fetch_constituents(self, index_name: str, verbose: bool = True) -> List[str]:
        """
        Fetch constituents using multiple methods with fallback
        """
        methods = [
            ("niftyindices.com", self.fetch_from_niftyindices_csv),
            ("NSE API", self.fetch_from_nse_api),
            ("nsetools", self.fetch_from_nsetools),
            ("Fallback", self.fetch_from_fallback),
        ]
        
        for method_name, method_func in methods:
            if verbose:
                print(f"   Trying {method_name}...", end=" ")
            
            try:
                result = method_func(index_name)
                if result and len(result) > 0:
                    if verbose:
                        print(f"✅ Found {len(result)} stocks")
                    self.sources_used[index_name] = method_name
                    return result
                else:
                    if verbose:
                        print("❌ No data")
            except Exception as e:
                if verbose:
                    print(f"❌ Error: {e}")
            
            time.sleep(0.3)  # Rate limiting
        
        self.sources_used[index_name] = "None"
        return []
    
    def fetch_all_sectors(self, sectors: List[str] = None) -> Dict[str, List[str]]:
        """
        Fetch constituents for all sectors
        """
        if sectors is None:
            sectors = list(NSE_API_INDEX_NAMES.keys())
        
        print("\n" + "=" * 70)
        print("   FETCHING SECTOR CONSTITUENTS")
        print("=" * 70 + "\n")
        
        for sector in sectors:
            print(f"\n📊 {sector}:")
            constituents = self.fetch_constituents(sector)
            self.results[sector] = constituents
        
        return self.results
    
    def print_summary(self):
        """
        Print summary of results
        """
        print("\n\n" + "=" * 70)
        print("   SUMMARY")
        print("=" * 70)
        
        print(f"\n{'Sector':<25} {'Stocks':>8} {'Source':<20}")
        print("-" * 55)
        
        for sector, stocks in self.results.items():
            source = self.sources_used.get(sector, "Unknown")
            print(f"{sector:<25} {len(stocks):>8} {source:<20}")
        
        total_sectors = len(self.results)
        successful = sum(1 for stocks in self.results.values() if len(stocks) > 0)
        print("-" * 55)
        print(f"Total: {successful}/{total_sectors} sectors fetched successfully")
    
    def generate_config_code(self) -> str:
        """
        Generate Python code for config.py
        """
        lines = ['SECTOR_CONSTITUENTS = {']
        
        for sector, stocks in sorted(self.results.items()):
            if stocks:
                stock_str = ', '.join([f'"{s}"' for s in stocks])
                lines.append(f'    "{sector}": [{stock_str}],')
        
        lines.append('}')
        return '\n'.join(lines)
    
    def save_to_json(self, filename: str = "sector_constituents.json"):
        """
        Save results to JSON file
        """
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n✅ Saved to {filename}")


def main():
    """
    Main function
    """
    fetcher = SectorConstituentsFetcher()
    
    # Define sectors to fetch
    sectors = [
        "NIFTY BANK",
        "NIFTY IT",
        "NIFTY PHARMA",
        "NIFTY AUTO",
        "NIFTY METAL",
        "NIFTY REALTY",
        "NIFTY FMCG",
        "NIFTY ENERGY",
        "NIFTY FIN SERVICE",
        "NIFTY PSU BANK",
        "NIFTY PVT BANK",
        "NIFTY INFRA",
        "NIFTY MEDIA",
        "NIFTY MNC",
        "NIFTY COMMODITIES",
        "NIFTY CONSUMPTION",
        "NIFTY SERV SECTOR",
        "NIFTY PSE",
    ]
    
    # Fetch all sectors
    fetcher.fetch_all_sectors(sectors)
    
    # Print summary
    fetcher.print_summary()
    
    # Save to JSON
    fetcher.save_to_json()
    
    # Generate config code
    print("\n\n" + "=" * 70)
    print("   PYTHON CODE FOR config.py")
    print("=" * 70 + "\n")
    print(fetcher.generate_config_code())
    
    # Check if --update-config flag is passed
    if "--update-config" in sys.argv:
        print("\n⚠️ Config update not implemented. Copy the code above manually.")


if __name__ == "__main__":
    main()
