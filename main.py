"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    SECTOR MOMENTUM BREAKOUT STRATEGY                          ║
║                           Main Entry Point                                     ║
║                                                                               ║
║  Strategy Flow:                                                               ║
║  1. Identify trend from first 10-min NIFTY 50 candle (9:15-9:25)             ║
║  2. Select best/worst sector based on trend                                   ║
║  3. Find best stock in sector (movement <= 3%)                               ║
║  4. Monitor for 2 consecutive candles above PDH / below PDL                  ║
║  5. Execute: BUY PE + BUY FUTURE (bullish) or BUY CE + SHORT FUTURE (bearish)║
║  6. Monitor: SL (candle low), TP (2x SL), Trailing (0.5% -> BE)             ║
║  7. Force exit at 3:15 PM                                                    ║
║                                                                               ║
║  Max 2 trades per day                                                        ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import sys
import os
import time
import argparse
import traceback
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# PATH SETUP — works both as .py script AND as PyInstaller EXE
# ─────────────────────────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    # Running as compiled EXE — use the folder where the EXE lives
    EXE_DIR = os.path.dirname(sys.executable)
    SCRIPT_DIR = sys._MEIPASS  # bundled modules live here
else:
    # Running as normal .py script
    EXE_DIR = os.path.dirname(os.path.abspath(__file__))
    SCRIPT_DIR = EXE_DIR

# Add both paths so imports resolve correctly
sys.path.insert(0, SCRIPT_DIR)
sys.path.insert(0, EXE_DIR)

LOG_FILE = os.path.join(EXE_DIR, 'crash.log')


def log_crash(msg: str):
    """Write crash details to crash.log so the user can read them after the window closes."""
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass


def pause_exit(code: int = 1):
    """Keep the console window open so the user can read the error."""
    print("\n" + "─" * 60)
    print(f"  Check '{LOG_FILE}' for full error details.")
    print("─" * 60)
    input("\n  Press ENTER to close this window...")
    sys.exit(code)


# ─────────────────────────────────────────────────────────────────────────────
# VERIFY config.py IS PRESENT NEXT TO THE EXE BEFORE IMPORTING
# ─────────────────────────────────────────────────────────────────────────────
config_path = os.path.join(EXE_DIR, 'config.py')
if not os.path.exists(config_path):
    msg = (
        f"config.py not found!\n"
        f"Expected location: {config_path}\n\n"
        f"Please make sure 'config.py' is in the same folder as the EXE.\n"
        f"Edit config.py with your Angel One credentials before running."
    )
    print("\n❌  ERROR: " + msg)
    log_crash("STARTUP ERROR: " + msg)
    pause_exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# IMPORTS
# ─────────────────────────────────────────────────────────────────────────────
try:
    from config import (
        MAX_TRADES_PER_DAY, PAPER_TRADING, ENTRY_CUTOFF, FORCE_EXIT_TIME
    )
    from angel_api import AngelOneAPI, get_api
    from data_fetcher import DataFetcher
    from logger import StrategyLogger, get_logger
    from trend_identifier import TrendIdentifier
    from sector_scanner import SectorScanner
    from stock_selector import StockSelector
    from entry_monitor import EntryMonitor
    from order_executor import OrderExecutor
    from position_monitor import PositionMonitor
except ImportError as e:
    msg = f"Import error: {e}\n{traceback.format_exc()}"
    print(f"\n❌  ERROR: {msg}")
    log_crash(msg)
    pause_exit(1)


class SectorMomentumStrategy:
    """
    Main strategy orchestrator
    """

    def __init__(self, paper_trading=True, force_trend=None):
        self.paper_trading = paper_trading
        self.force_trend = force_trend
        self.trade_count = 0

        self.api = None
        self.logger = None
        self.data_fetcher = None

        self.trend_identifier = None
        self.sector_scanner = None
        self.stock_selector = None
        self.entry_monitor = None
        self.order_executor = None
        self.position_monitor = None

        self.trend = None
        self.selected_sector = None
        self.selected_stock = None

    def initialize(self):
        """Initialize API connection and strategy components"""
        print("\n" + "=" * 80)
        print("   SECTOR MOMENTUM BREAKOUT STRATEGY")
        print("   " + ("PAPER TRADING MODE" if self.paper_trading else "⚠️  LIVE TRADING MODE"))
        print("=" * 80)

        print("\n📡 Initializing Angel One API...")
        self.api = get_api()

        if not self.api:
            print("   ❌ Failed to create API instance")
            return False

        if not self.api.is_connected:
            if not self.api.connect():
                print("   ❌ Failed to connect to API")
                return False

        print("   ✅ API connection established")

        self._subscribe_sector_indices()

        self.logger = get_logger()
        self.logger.info("Strategy initialized")

        self.data_fetcher = DataFetcher(self.api)

        self.trend_identifier = TrendIdentifier(self.api, self.logger)
        self.sector_scanner = SectorScanner(self.api, self.logger)
        self.stock_selector = StockSelector(self.api, self.data_fetcher, self.logger)
        self.entry_monitor = EntryMonitor(self.api, self.data_fetcher, self.logger)
        self.order_executor = OrderExecutor(self.api, self.data_fetcher, self.logger)
        self.position_monitor = PositionMonitor(
            self.api, self.data_fetcher, self.order_executor, self.logger
        )

        return True

    def _subscribe_sector_indices(self):
        from config import SECTORAL_INDICES

        if not self.api.ws_manager:
            print("   ⚠️ WebSocket not available, will use REST API for LTP")
            return

        print("\n📡 Subscribing to sector indices via WebSocket...")

        symbols = [{'exchange': 'NSE', 'token': '99926000'}]
        for sector_name, (symbol, token, exchange) in SECTORAL_INDICES.items():
            symbols.append({'exchange': exchange, 'token': token})

        if self.api.subscribe_symbols(symbols):
            print(f"   ✅ Subscribed to {len(symbols)} indices (NIFTY 50 + 18 sectors)")
        else:
            print("   ⚠️ WebSocket subscription failed, will use REST API")

        time.sleep(2)

    def subscribe_stock_symbols(self, stocks: list):
        if not self.api.ws_manager:
            return
        symbols = [{'exchange': s.get('exchange', 'NSE'), 'token': s['token']} for s in stocks]
        self.api.subscribe_symbols(symbols)
        time.sleep(1)

    def run(self):
        """Main strategy execution loop"""
        if not self.initialize():
            return

        self.logger.print_banner("STRATEGY STARTED")

        try:
            if self.force_trend:
                self.trend = self.force_trend
                self.logger.info(f"🎯 Using forced trend: {self.trend}")
                print(f"\n🎯 Using forced trend: {self.trend}")
            else:
                self.trend = self.trend_identifier.identify_trend()

            if not self.trend:
                self.logger.error("❌ Could not identify trend. Exiting.")
                return

            self.sector_scanner.scan_all_sectors()
            self.sector_scanner.display_sector_ranking()

            while self.trade_count < MAX_TRADES_PER_DAY:
                now = datetime.now()
                entry_cutoff_time = datetime.strptime(ENTRY_CUTOFF, "%H:%M").time()
                if now.time() >= entry_cutoff_time:
                    self.logger.info("⏰ Entry cutoff time reached. No more entries.")
                    break

                if not self.selected_sector:
                    self.selected_sector = self.sector_scanner.select_sector_for_trend(self.trend)

                if not self.selected_sector:
                    self.logger.error("❌ Could not select sector. Exiting.")
                    break

                self.selected_stock = self.stock_selector.select_best_stock(
                    self.selected_sector['name'], self.trend
                )

                if not self.selected_stock:
                    self.logger.warning("⚠️ No suitable stock found. Trying next sector...")
                    break

                self.subscribe_stock_symbols([self.selected_stock])

                if not self.entry_monitor.setup(self.selected_stock, self.trend):
                    self.logger.error("❌ Entry monitor setup failed")
                    break

                entry_data = self.entry_monitor.monitor_for_entry()

                if entry_data:
                    order_result = self.order_executor.execute_entry(
                        self.selected_stock,
                        self.trend,
                        entry_data['entry_price'],
                        entry_data['stop_loss']
                    )

                    if order_result:
                        self.trade_count += 1
                        self.logger.info(f"✅ Trade {self.trade_count} executed successfully!")
                        self.position_monitor.start_monitoring()
                        self.selected_sector = None
                        self.selected_stock = None
                    else:
                        self.logger.warning("⚠️ Order execution failed")
                        break
                else:
                    self.logger.info("📊 Entry conditions not met")
                    break

        except KeyboardInterrupt:
            self.logger.info("🛑 Strategy stopped by user")
        except Exception as e:
            err = f"Strategy error: {e}\n{traceback.format_exc()}"
            self.logger.error(f"❌ {err}")
            log_crash(err)
            print(f"\n❌ UNEXPECTED ERROR: {e}")
        finally:
            self._cleanup()

    def _cleanup(self):
        if self.logger:
            self.logger.print_banner("STRATEGY ENDED")
            self.logger.info(f"Total trades: {self.trade_count}")
        if self.position_monitor:
            self.position_monitor.stop_monitoring()
        if self.api and self.api.ws_manager:
            self.api.ws_manager.disconnect()


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='Sector Momentum Breakout Strategy')
    parser.add_argument('--live', action='store_true', help='Enable live trading (default: paper)')
    parser.add_argument('--trend', choices=['BULLISH', 'BEARISH'], help='Force trend direction')
    parser.add_argument('--test-sectors', action='store_true', help='Test sector scanning only')
    parser.add_argument('--test-stocks', type=str, help='Test stock selection for a sector')

    args = parser.parse_args()

    if args.test_sectors:
        test_sector_scanning()
        return

    if args.test_stocks:
        test_stock_selection(args.test_stocks)
        return

    paper_trading = not args.live

    if not paper_trading:
        print("\n" + "!" * 80)
        print("   ⚠️  WARNING: LIVE TRADING MODE ENABLED")
        print("   ⚠️  Real orders will be placed!")
        print("!" * 80)
        confirm = input("\nType 'CONFIRM' to proceed with live trading: ")
        if confirm != 'CONFIRM':
            print("Live trading cancelled.")
            return

    strategy = SectorMomentumStrategy(paper_trading=paper_trading, force_trend=args.trend)
    strategy.run()


def test_sector_scanning():
    print("\n" + "=" * 60)
    print("   SECTOR SCANNING TEST")
    print("=" * 60)

    api = get_api()
    if not api or not (api.is_connected or api.connect()):
        print("❌ Failed to connect to API")
        return

    logger = get_logger()
    sector_scanner = SectorScanner(api, logger)
    sectors = sector_scanner.scan_all_sectors()
    print(f"   Scanned {len(sectors)} sectors")

    best = sector_scanner.get_best_sector()
    worst = sector_scanner.get_worst_sector()
    if best:
        print(f"\n   🏆 Best: {best['name']} ({best['change_pct']:+.2f}%)")
    if worst:
        print(f"   📉 Worst: {worst['name']} ({worst['change_pct']:+.2f}%)")

    sector_scanner.display_sector_ranking()


def test_stock_selection(sector_name: str):
    print("\n" + "=" * 60)
    print(f"   STOCK SELECTION TEST: {sector_name}")
    print("=" * 60)

    api = get_api()
    if not api or not (api.is_connected or api.connect()):
        print("❌ Failed to connect to API")
        return

    logger = get_logger()
    data_fetcher = DataFetcher(api)
    selector = StockSelector(api, data_fetcher, logger)

    print("\n📈 Testing BULLISH selection...")
    stock = selector.select_best_stock(sector_name, 'BULLISH')
    if stock:
        print(f"   Selected: {stock['symbol']} ({stock.get('change_pct', 0):+.2f}%)")
    else:
        print("   No suitable stock found")

    print("\n📉 Testing BEARISH selection...")
    stock = selector.select_best_stock(sector_name, 'BEARISH')
    if stock:
        print(f"   Selected: {stock['symbol']} ({stock.get('change_pct', 0):+.2f}%)")
    else:
        print("   No suitable stock found")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        err = f"FATAL ERROR: {e}\n{traceback.format_exc()}"
        print(f"\n❌ {err}")
        log_crash(err)
        pause_exit(1)
