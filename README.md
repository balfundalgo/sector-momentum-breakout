# 📈 Sector Momentum Breakout Strategy

Automated intraday trading strategy for Indian F&O markets using Angel One SmartAPI.

## 🎯 Strategy Overview

This strategy identifies market trend from the first 10-minute NIFTY 50 candle and trades the strongest/weakest sector using Options + Futures.

### Strategy Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  9:15-9:25  │ Identify trend from NIFTY 50 first 10-min candle  │
├─────────────────────────────────────────────────────────────────┤
│  9:25+      │ Scan all 18 sectoral indices for performance       │
├─────────────────────────────────────────────────────────────────┤
│             │ BULLISH → Select BEST performing sector            │
│             │ BEARISH → Select WORST performing sector           │
├─────────────────────────────────────────────────────────────────┤
│             │ Find best stock in sector (movement ≤ 3%)          │
├─────────────────────────────────────────────────────────────────┤
│  Monitor    │ Wait for 2 consecutive 5-min candles:              │
│             │   • BULLISH: Close above Previous Day High (PDH)   │
│             │   • BEARISH: Close below Previous Day Low (PDL)    │
├─────────────────────────────────────────────────────────────────┤
│  Execute    │ BULLISH: BUY ATM PE + BUY FUTURE                   │
│             │ BEARISH: BUY ATM CE + SHORT FUTURE                 │
├─────────────────────────────────────────────────────────────────┤
│  Manage     │ SL: Candle Low (bullish) / Candle High (bearish)   │
│             │ TP: 2x SL distance                                  │
│             │ Trailing: Move SL to breakeven at 0.5% profit      │
├─────────────────────────────────────────────────────────────────┤
│  3:15 PM    │ Force exit all positions                           │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Features

- **Real-time WebSocket** for LTP data (eliminates rate limit errors)
- **18 Sectoral Indices** scanning and ranking
- **F&O Stock Filtering** - only stocks with futures & options
- **Hybrid Candle Builder** - WebSocket detection + REST API fetch
- **Trailing Stop** management with breakeven protection
- **Paper Trading Mode** for safe testing
- **Comprehensive Logging** with trade records

## 📋 Requirements

- Python 3.10 or higher
- Angel One trading account with API access
- Valid API credentials (Client ID, API Key, MPIN, TOTP Secret)

## 🔧 Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/sector-momentum-strategy.git
cd sector-momentum-strategy

# Install dependencies
pip install -r requirements.txt

# Configure credentials
# Edit config.py with your Angel One API credentials
```

### Pre-built Executables

Download from [Releases](../../releases):
- **Windows**: `SectorMomentumStrategy-Windows.zip`
- **Mac**: `SectorMomentumStrategy-Mac.zip`

## ⚙️ Configuration

Edit `config.py`:

```python
# API Credentials
CLIENT_ID = 'YOUR_CLIENT_ID'
API_KEY = 'YOUR_API_KEY'
MPIN = 'YOUR_MPIN'
TOTP_SECRET = 'YOUR_TOTP_SECRET'

# Strategy Parameters
MAX_STOCK_MOVEMENT_PCT = 3.0    # Skip stocks moving more than 3%
TRAILING_TRIGGER_PCT = 0.5      # Move SL to breakeven at 0.5% profit
RISK_REWARD_RATIO = 2           # 1:2 risk-reward

# Position Limits
MAX_TRADES_PER_DAY = 2
LOTS_PER_TRADE = 1

# Paper Trading (set to False for live)
PAPER_TRADING = True
```

## 🎮 Usage

### Command Line Options

```bash
# Paper trading (default - safe mode)
python main.py

# Live trading (⚠️ real orders!)
python main.py --live

# Force bullish trend
python main.py --trend BULLISH

# Force bearish trend
python main.py --trend BEARISH

# Test sector scanning only
python main.py --test-sectors

# Test stock selection for a sector
python main.py --test-stocks "NIFTY BANK"
```

### Using Executable

```bash
# Windows
SectorMomentumStrategy.exe

# Mac
./SectorMomentumStrategy

# With arguments
SectorMomentumStrategy.exe --live --trend BULLISH
```

## 📊 Output Example

```
════════════════════════════════════════════════════════════════════════════════
   SECTOR MOMENTUM BREAKOUT STRATEGY
   PAPER TRADING MODE
════════════════════════════════════════════════════════════════════════════════

📡 Initializing Angel One API...
   Generated TOTP: 123456
   ✅ Connected successfully!
   ✅ WebSocket ready for real-time LTP

════════════════════════════════════════════════════════════════════════════════
   TREND IDENTIFICATION PHASE
════════════════════════════════════════════════════════════════════════════════

   ╔══════════════════════════════════════════════════════════╗
   ║  NIFTY 50 FIRST 10-MINUTE CANDLE (09:15-09:25)
   ╠══════════════════════════════════════════════════════════╣
   ║  Open:      24150.35
   ║  High:      24185.20
   ║  Low:       24125.10
   ║  Close:     24172.80
   ╠══════════════════════════════════════════════════════════╣
   ║  🟢 BULLISH CANDLE (Close > Open)
   ║  → Strategy: BUY setup on BEST sector
   ╚══════════════════════════════════════════════════════════╝
```

## 📁 Project Structure

```
sector_momentum/
├── main.py                  # Entry point & orchestrator
├── config.py                # Configuration & credentials
├── angel_api.py             # Angel One API wrapper
├── websocket_manager.py     # Real-time WebSocket handler
├── api_rate_limiter.py      # Endpoint-aware rate limiting
├── data_fetcher.py          # Historical data & candles
├── trend_identifier.py      # NIFTY 50 trend analysis
├── sector_scanner.py        # Sector ranking
├── stock_selector.py        # Stock selection
├── entry_monitor.py         # PDH/PDL breakout detection
├── order_executor.py        # Order placement
├── position_monitor.py      # SL/TP management
├── logger.py                # Logging & trade records
├── candle_builder.py        # Hybrid candle builder
└── requirements.txt         # Dependencies
```

## ⚠️ Risk Disclaimer

**IMPORTANT**: 
- This software is for educational purposes only
- Trading in derivatives involves substantial risk of loss
- Past performance does not guarantee future results
- Always test thoroughly in paper trading mode before going live
- Never trade with money you cannot afford to lose

## 📝 License

This project is for personal use. Do not distribute credentials.

## 🤝 Support

For issues or questions, create an issue on GitHub.
