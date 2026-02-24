"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    SECTOR MOMENTUM BREAKOUT STRATEGY                          ║
║                         Configuration File                                     ║
║                                                                               ║
║         *** ALL TOKENS VERIFIED FROM INSTRUMENT MASTER 2026-01-28 ***         ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

# ═══════════════════════════════════════════════════════════════════════════════
# API CREDENTIALS (Angel One)
# ═══════════════════════════════════════════════════════════════════════════════
CLIENT_ID = 'AACA771307'
API_KEY = 'pCnorR60'
MPIN = '8802'
TOTP_SECRET = 'WQRUXDVZV2VTOR6VOBSIOWKORA'

# ═══════════════════════════════════════════════════════════════════════════════
# INSTRUMENT MASTER URL
# ═══════════════════════════════════════════════════════════════════════════════
INSTRUMENT_MASTER_URL = 'https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json'

# ═══════════════════════════════════════════════════════════════════════════════
# STRATEGY PARAMETERS
# ═══════════════════════════════════════════════════════════════════════════════

# Candle Settings
TREND_CANDLE_MINUTES = 10           # First candle duration for trend (9:15-9:25)
MONITORING_CANDLE_MINUTES = 5       # Entry monitoring candle size

# Stock Selection
MAX_STOCK_MOVEMENT_PCT = 3.0        # Skip stocks moving more than this %
MIN_STOCK_MOVEMENT_PCT = 0.0        # Minimum movement required

# Entry Conditions
SECOND_CANDLE_MAX_RANGE_PCT = 1.0   # 2nd consecutive candle (H-L)/Close <= this %

# Risk Management
TRAILING_TRIGGER_PCT = 0.5          # Move SL to breakeven after stock moves this %
RISK_REWARD_RATIO = 2               # 1:2 risk-reward (TP = 2x SL distance)

# ═══════════════════════════════════════════════════════════════════════════════
# TIME WINDOWS
# ═══════════════════════════════════════════════════════════════════════════════
MARKET_OPEN = "09:15"
TREND_START = "09:15"
TREND_END = "09:25"
ENTRY_CUTOFF = "15:00"              # *** 3:00 PM FOR TESTING (change to 10:30 for live) ***
FORCE_EXIT_TIME = "15:15"           # Square off all positions
MARKET_CLOSE = "15:30"

# ═══════════════════════════════════════════════════════════════════════════════
# POSITION LIMITS
# ═══════════════════════════════════════════════════════════════════════════════
MAX_TRADES_PER_DAY = 2              # Maximum stocks to trade per day
LOTS_PER_TRADE = 1                  # Number of lots per trade (editable)

# ═══════════════════════════════════════════════════════════════════════════════
# EXPIRY SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════
OPTION_EXPIRY = "WEEKLY"            # Current week expiry for options
FUTURE_EXPIRY = "MONTHLY"           # Current month expiry for futures

# ═══════════════════════════════════════════════════════════════════════════════
# NIFTY 50 INDEX CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════
NIFTY_50_TOKEN = "99926000"
NIFTY_50_SYMBOL = "Nifty 50"
NIFTY_50_EXCHANGE = "NSE"

# ═══════════════════════════════════════════════════════════════════════════════
# SECTORAL INDICES CONFIGURATION
# *** ALL TOKENS VERIFIED FROM INSTRUMENT MASTER - discover_tokens.py output ***
#
# Format: "Display Name": ("Symbol", "Token", "Exchange")
#
# From discover_tokens.py run on 2026-01-28:
# Token        Symbol                  Name in Instrument Master
# ─────────────────────────────────────────────────────────────
# 99926008     Nifty IT                NIFTY IT
# 99926009     Nifty Bank              BANKNIFTY
# 99926018     Nifty Realty            NIFTY REALTY
# 99926019     Nifty Infra             NIFTY INFRA
# 99926020     Nifty Energy            NIFTY ENERGY
# 99926021     Nifty FMCG              NIFTY FMCG
# 99926022     Nifty MNC               NIFTY MNC
# 99926023     Nifty Pharma            NIFTY PHARMA
# 99926024     Nifty PSE               NIFTY PSE
# 99926025     Nifty PSU Bank          NIFTY PSU BANK
# 99926026     Nifty Serv Sector       NIFTY SERV SECTOR
# 99926029     Nifty Auto              NIFTY AUTO
# 99926030     Nifty Metal             NIFTY METAL
# 99926031     Nifty Media             NIFTY MEDIA
# 99926035     Nifty Commodities       NIFTY COMMODITIES
# 99926036     Nifty Consumption       NIFTY CONSUMPTION
# 99926037     Nifty Fin Service       FINNIFTY
# 99926047     Nifty Pvt Bank          NIFTY PVT BANK
# ═══════════════════════════════════════════════════════════════════════════════
SECTORAL_INDICES = {
    "NIFTY BANK": ("Nifty Bank", "99926009", "NSE"),
    "NIFTY IT": ("Nifty IT", "99926008", "NSE"),
    "NIFTY REALTY": ("Nifty Realty", "99926018", "NSE"),
    "NIFTY INFRA": ("Nifty Infra", "99926019", "NSE"),
    "NIFTY ENERGY": ("Nifty Energy", "99926020", "NSE"),
    "NIFTY FMCG": ("Nifty FMCG", "99926021", "NSE"),
    "NIFTY MNC": ("Nifty MNC", "99926022", "NSE"),
    "NIFTY PHARMA": ("Nifty Pharma", "99926023", "NSE"),
    "NIFTY PSE": ("Nifty PSE", "99926024", "NSE"),
    "NIFTY PSU BANK": ("Nifty PSU Bank", "99926025", "NSE"),
    "NIFTY SERV SECTOR": ("Nifty Serv Sector", "99926026", "NSE"),
    "NIFTY AUTO": ("Nifty Auto", "99926029", "NSE"),
    "NIFTY METAL": ("Nifty Metal", "99926030", "NSE"),
    "NIFTY MEDIA": ("Nifty Media", "99926031", "NSE"),
    "NIFTY COMMODITIES": ("Nifty Commodities", "99926035", "NSE"),
    "NIFTY CONSUMPTION": ("Nifty Consumption", "99926036", "NSE"),
    "NIFTY FIN SERVICE": ("Nifty Fin Service", "99926037", "NSE"),
    "NIFTY PVT BANK": ("Nifty Pvt Bank", "99926047", "NSE"),
}

# ═══════════════════════════════════════════════════════════════════════════════
# SECTOR CONSTITUENTS (Stock symbols in each sector)
# Will be fetched dynamically, but keeping common ones as fallback
# ═══════════════════════════════════════════════════════════════════════════════
# Path to cached sector constituents (auto-saved from successful live fetches)
SECTOR_CACHE_FILE = "sector_constituents_cache.json"

# Comprehensive fallback lists (Last resort if both live fetch AND cache fail)
# Updated Feb 2026 from NSE niftyindices.com data
# NOTE: "LARSEN" was wrong, correct symbol is "LT"
SECTOR_CONSTITUENTS_FALLBACK = {
    # ── NIFTY BANK (14 stocks) ── Verified from smart-investing.in Jan 2026
    "NIFTY BANK": ["HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK",
                   "BANKBARODA", "CANBK", "PNB", "UNIONBANK", "INDUSINDBK",
                   "FEDERALBNK", "IDFCFIRSTB", "AUBANK", "YESBANK"],

    # ── NIFTY IT (10 stocks) ── Verified from NSE factsheet + smart-investing.in Jan 2026
    "NIFTY IT": ["TCS", "INFY", "HCLTECH", "WIPRO", "TECHM", "LTIM",
                 "PERSISTENT", "COFORGE", "MPHASIS", "OFSS"],

    # ── NIFTY PHARMA (20 stocks) ── From NSE factsheet
    "NIFTY PHARMA": ["SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB", "APOLLOHOSP",
                     "LUPIN", "AUROPHARMA", "TORNTPHARM", "ZYDUSLIFE", "BIOCON",
                     "MAXHEALTH", "ALKEM", "IPCALAB", "GLENMARK", "NATCOPHARM",
                     "LAURUSLABS", "LALPATHLAB", "GRANULES", "ABBOTINDIA", "SYNGENE"],

    # ── NIFTY AUTO (15 stocks) ── Verified from smart-investing.in Jan 2026
    "NIFTY AUTO": ["M&M", "MARUTI", "BAJAJ-AUTO", "EICHERMOT", "TVSMOTOR",
                   "TATAMOTORS", "MOTHERSON", "ASHOKLEY", "HEROMOTOCO", "BOSCHLTD",
                   "BHARATFORG", "UNOMINDA", "TIINDIA", "SONACOMS", "EXIDEIND"],

    # ── NIFTY METAL (15 stocks) ── From NSE factsheet
    "NIFTY METAL": ["TATASTEEL", "HINDALCO", "JSWSTEEL", "COALINDIA", "VEDL",
                    "ADANIENT", "NMDC", "SAIL", "NATIONALUM", "JINDALSTEL",
                    "HINDZINC", "APLAPOLLO", "WELCORP", "RATNAMANI", "MOIL"],

    # ── NIFTY REALTY (10 stocks) ── From NSE factsheet
    "NIFTY REALTY": ["DLF", "GODREJPROP", "OBEROIRLTY", "PRESTIGE", "PHOENIXLTD",
                     "BRIGADE", "SOBHA", "SUNTECK", "LODHA", "MAHLIFE"],

    # ── NIFTY FMCG (15 stocks) ── From NSE factsheet
    "NIFTY FMCG": ["HINDUNILVR", "ITC", "NESTLEIND", "BRITANNIA", "TATACONSUM",
                   "GODREJCP", "DABUR", "MARICO", "COLPAL", "VBL",
                   "EMAMILTD", "MCDOWELL-N", "PGHH", "RADICO", "ZYDUSWELL"],

    # ── NIFTY ENERGY (10 stocks) ── From NSE factsheet
    "NIFTY ENERGY": ["RELIANCE", "ONGC", "NTPC", "POWERGRID", "BPCL",
                     "IOC", "GAIL", "TATAPOWER", "ADANIGREEN", "ADANIPOWER"],

    # ── NIFTY FIN SERVICE (20 stocks) ── From NSE factsheet
    "NIFTY FIN SERVICE": ["HDFCBANK", "ICICIBANK", "BAJFINANCE", "BAJAJFINSV", "SBILIFE",
                          "HDFCLIFE", "AXISBANK", "SBIN", "KOTAKBANK", "ICICIGI",
                          "HDFCAMC", "SBICARD", "CHOLAFIN", "MUTHOOTFIN", "M&MFIN",
                          "SHRIRAMFIN", "LICHSGFIN", "JIOFIN", "PFC", "RECLTD"],

    # ── NIFTY PSU BANK (12 stocks) ── From NSE factsheet
    "NIFTY PSU BANK": ["SBIN", "BANKBARODA", "PNB", "CANBK", "UNIONBANK",
                       "INDIANB", "IOB", "BANKINDIA", "CENTRALBK", "UCOBANK",
                       "MAHABANK", "PSB"],

    # ── NIFTY PVT BANK (10 stocks) ── From NSE factsheet
    "NIFTY PVT BANK": ["HDFCBANK", "ICICIBANK", "KOTAKBANK", "AXISBANK", "INDUSINDBK",
                       "FEDERALBNK", "IDFCFIRSTB", "AUBANK", "YESBANK", "BANDHANBNK",
                       "RBLBANK", "CSBBANK"],

    # ── NIFTY INFRA (30 stocks) ── VERIFIED from live run 02-Feb-2026
    "NIFTY INFRA": ["RELIANCE", "BHARTIARTL", "LT", "ULTRACEMCO", "ADANIPORTS",
                    "NTPC", "ONGC", "POWERGRID", "IOC", "INDIGO",
                    "GRASIM", "DLF", "ADANIGREEN", "BPCL", "AMBUJACEM",
                    "MOTHERSON", "TATAPOWER", "CUMMINSIND", "GAIL", "INDUSTOWER",
                    "APOLLOHOSP", "ASHOKLEY", "BHARATFORG", "CGPOWER", "GODREJPROP",
                    "HINDPETRO", "INDHOTEL", "MAXHEALTH", "SHREECEM", "SUZLON"],

    # ── NIFTY MEDIA (10-15 stocks) ── From NSE factsheet
    "NIFTY MEDIA": ["ZEEL", "SUNTV", "PVR", "NETWORK18", "TV18BRDCST",
                    "DISHTV", "HATHWAY", "NAZARA", "TIPS", "SAREGAMA"],

    # ── NIFTY MNC (30 stocks) ── From NSE factsheet
    "NIFTY MNC": ["MARUTI", "BRITANNIA", "SIEMENS", "ABB", "BOSCHLTD",
                  "HONAUT", "PAGEIND", "PGHH", "GLAXO", "PFIZER",
                  "WHIRLPOOL", "3MINDIA", "GILLETTE", "CASTROLIND", "AKZOINDIA",
                  "COLPAL", "NESTLEIND", "CUMMINSIND", "ABBOTINDIA", "SCHAEFFLER"],

    # ── NIFTY COMMODITIES (30 stocks) ── From NSE factsheet
    "NIFTY COMMODITIES": ["RELIANCE", "ONGC", "TATASTEEL", "HINDALCO", "COALINDIA",
                          "JSWSTEEL", "NTPC", "POWERGRID", "VEDL", "IOC",
                          "BPCL", "GAIL", "NMDC", "JINDALSTEL", "SAIL",
                          "HINDZINC", "ADANIGREEN", "ADANIENT", "NATIONALUM", "ULTRACEMCO",
                          "GRASIM", "AMBUJACEM", "SHREECEM", "TATAPOWER", "ADANIPOWER",
                          "PETRONET", "HINDPETRO", "APLAPOLLO", "IGL", "MGL"],

    # ── NIFTY CONSUMPTION (30 stocks) ── From NSE factsheet
    "NIFTY CONSUMPTION": ["HINDUNILVR", "ITC", "TITAN", "MARUTI", "NESTLEIND",
                          "BRITANNIA", "ASIANPAINT", "DABUR", "COLPAL", "MARICO",
                          "TATACONSUM", "GODREJCP", "PIDILITIND", "BERGEPAINT", "VBL",
                          "EMAMILTD", "MCDOWELL-N", "PAGEIND", "DMART", "TRENT",
                          "INDIGO", "M&M", "BAJAJ-AUTO", "HEROMOTOCO", "VOLTAS",
                          "HAVELLS", "CROMPTON", "JUBLFOOD", "BATAINDIA", "RELAXO"],

    # ── NIFTY SERV SECTOR (30 stocks) ── From NSE factsheet
    "NIFTY SERV SECTOR": ["HDFCBANK", "ICICIBANK", "INFY", "TCS", "BHARTIARTL",
                          "KOTAKBANK", "AXISBANK", "SBIN", "LT", "BAJFINANCE",
                          "WIPRO", "HCLTECH", "TECHM", "ADANIPORTS", "LTIM",
                          "SBILIFE", "HDFCLIFE", "BAJAJFINSV", "ICICIGI", "HDFCAMC",
                          "SBICARD", "JIOFIN", "INDUSINDBK", "FEDERALBNK", "AUBANK",
                          "MPHASIS", "COFORGE", "PERSISTENT", "INDUSTOWER", "INDIGO"],

    # ── NIFTY PSE (20 stocks) ── From NSE factsheet
    "NIFTY PSE": ["ONGC", "NTPC", "POWERGRID", "COALINDIA", "IOC",
                  "BPCL", "GAIL", "BHEL", "RECLTD", "PFC",
                  "NHPC", "SJVN", "IRFC", "NMDC", "SAIL",
                  "SBIN", "BANKBARODA", "CONCOR", "IRCTC", "NATIONALUM"],
}

# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════
LOG_LEVEL = "INFO"
LOG_TO_FILE = True
LOG_TO_CONSOLE = True

# ═══════════════════════════════════════════════════════════════════════════════
# PAPER TRADING MODE (Set to True for testing without real orders)
# ═══════════════════════════════════════════════════════════════════════════════
PAPER_TRADING = True

# ═══════════════════════════════════════════════════════════════════════════════
# DATA REFRESH INTERVALS (in seconds)
# ═══════════════════════════════════════════════════════════════════════════════
LTP_REFRESH_INTERVAL = 1            # How often to check LTP for monitoring
CANDLE_CHECK_INTERVAL = 5           # How often to check for new candles
