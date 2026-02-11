"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                        POSITION MONITOR MODULE                                 ║
║         Monitors open positions for SL, TP, Trailing, and Time exits          ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import time
from datetime import datetime
from typing import Optional, Dict, List

import sys
import os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    FORCE_EXIT_TIME, TRAILING_TRIGGER_PCT,
    LTP_REFRESH_INTERVAL
)


class PositionMonitor:
    """
    Monitors open positions and handles exits
    """
    
    def __init__(self, api, data_fetcher, order_executor, logger):
        """
        Initialize position monitor
        
        Args:
            api: AngelOneAPI instance
            data_fetcher: DataFetcher instance
            order_executor: OrderExecutor instance
            logger: StrategyLogger instance
        """
        self.api = api
        self.data_fetcher = data_fetcher
        self.order_executor = order_executor
        self.logger = logger
        
        self.is_running = False
        self.trailing_triggered = {}  # Track which trades have trailing triggered
    
    def start_monitoring(self):
        """
        Start monitoring all active positions
        """
        self.logger.print_banner("POSITION MONITORING PHASE")
        
        today = datetime.now().strftime("%Y-%m-%d")
        force_exit_time = datetime.strptime(f"{today} {FORCE_EXIT_TIME}", "%Y-%m-%d %H:%M")
        
        self.is_running = True
        
        self.logger.info(f"👁️ Starting position monitoring until {FORCE_EXIT_TIME}")
        print(f"\n   Monitoring active positions...")
        print(f"   Force exit time: {FORCE_EXIT_TIME}")
        print(f"   {'─' * 60}")
        
        while self.is_running and datetime.now() < force_exit_time:
            active_trades = self.order_executor.get_active_trades()
            
            if not active_trades:
                self.logger.info("📭 No active trades to monitor")
                print("\n   No active trades to monitor.")
                break
            
            for trade in active_trades[:]:  # Use slice to allow removal during iteration
                exit_reason = self._check_trade_conditions(trade)
                
                if exit_reason:
                    self.order_executor.exit_trade(trade, exit_reason)
            
            # Check remaining trades
            if not self.order_executor.get_active_trades():
                self.logger.info("📭 All trades closed")
                print("\n   All trades have been closed.")
                break
            
            time.sleep(LTP_REFRESH_INTERVAL)
        
        # Force exit remaining positions at end of day
        if datetime.now() >= force_exit_time:
            self._force_exit_all()
        
        self.is_running = False
    
    def _check_trade_conditions(self, trade: Dict) -> Optional[str]:
        """
        Check all exit conditions for a trade
        
        Args:
            trade: Trade data dict
            
        Returns:
            Exit reason or None
        """
        symbol = trade['symbol']
        token = trade['token']
        trend = trade['trend']
        entry_price = trade['entry_price']
        stop_loss = trade['stop_loss']
        take_profit = trade['take_profit']
        
        # Get current LTP
        ltp_data = self.api.get_ltp('NSE', symbol, token)
        
        if not ltp_data:
            return None
        
        current_price = ltp_data.get('ltp', 0)
        
        if current_price <= 0:
            return None
        
        # Calculate current P&L percentage
        if trend == 'BULLISH':
            price_change = current_price - entry_price
            price_change_pct = (price_change / entry_price) * 100
        else:
            price_change = entry_price - current_price
            price_change_pct = (price_change / entry_price) * 100
        
        # Display status
        status_indicator = "🟢" if price_change > 0 else "🔴" if price_change < 0 else "⚪"
        print(f"\r   {status_indicator} {symbol}: {current_price:.2f} | "
              f"Entry: {entry_price:.2f} | SL: {stop_loss:.2f} | "
              f"TP: {take_profit:.2f} | P&L: {price_change_pct:+.2f}%", end="")
        
        # Check Stop Loss
        if self._check_stop_loss(trade, current_price):
            print()  # New line after status
            return 'SL'
        
        # Check Take Profit
        if self._check_take_profit(trade, current_price):
            print()
            return 'TP'
        
        # Check Trailing Stop
        trailing_result = self._check_trailing_stop(trade, current_price)
        if trailing_result:
            print()
            return trailing_result
        
        return None
    
    def _check_stop_loss(self, trade: Dict, current_price: float) -> bool:
        """
        Check if stop loss is hit
        
        Args:
            trade: Trade data dict
            current_price: Current LTP
            
        Returns:
            True if SL hit
        """
        trend = trade['trend']
        stop_loss = trade['stop_loss']
        trade_id = trade['trade_id']
        
        # Check if trailing has moved SL to breakeven
        if self.trailing_triggered.get(trade_id):
            stop_loss = trade['entry_price']  # Breakeven
        
        if trend == 'BULLISH':
            # For long: SL hit if price falls below stop loss
            if current_price <= stop_loss:
                self.logger.info(f"🛑 SL Hit for {trade['symbol']}: {current_price:.2f} <= {stop_loss:.2f}")
                return True
        else:
            # For short: SL hit if price rises above stop loss
            if current_price >= stop_loss:
                self.logger.info(f"🛑 SL Hit for {trade['symbol']}: {current_price:.2f} >= {stop_loss:.2f}")
                return True
        
        return False
    
    def _check_take_profit(self, trade: Dict, current_price: float) -> bool:
        """
        Check if take profit is hit
        
        Args:
            trade: Trade data dict
            current_price: Current LTP
            
        Returns:
            True if TP hit
        """
        trend = trade['trend']
        take_profit = trade['take_profit']
        
        if trend == 'BULLISH':
            # For long: TP hit if price rises above take profit
            if current_price >= take_profit:
                self.logger.info(f"🎯 TP Hit for {trade['symbol']}: {current_price:.2f} >= {take_profit:.2f}")
                return True
        else:
            # For short: TP hit if price falls below take profit
            if current_price <= take_profit:
                self.logger.info(f"🎯 TP Hit for {trade['symbol']}: {current_price:.2f} <= {take_profit:.2f}")
                return True
        
        return False
    
    def _check_trailing_stop(self, trade: Dict, current_price: float) -> Optional[str]:
        """
        Check and update trailing stop
        
        Trailing triggers when price moves 0.5% in profit direction
        Once triggered, SL moves to breakeven (entry price)
        
        Args:
            trade: Trade data dict
            current_price: Current LTP
            
        Returns:
            'TRAILING' if trailing SL hit, None otherwise
        """
        trade_id = trade['trade_id']
        trend = trade['trend']
        entry_price = trade['entry_price']
        
        # Calculate price move percentage from entry
        if trend == 'BULLISH':
            move_pct = ((current_price - entry_price) / entry_price) * 100
        else:
            move_pct = ((entry_price - current_price) / entry_price) * 100
        
        # Check if trailing should be triggered
        if not self.trailing_triggered.get(trade_id):
            if move_pct >= TRAILING_TRIGGER_PCT:
                self.trailing_triggered[trade_id] = True
                self.logger.info(f"📈 Trailing triggered for {trade['symbol']}: "
                               f"Move {move_pct:.2f}% >= {TRAILING_TRIGGER_PCT}%")
                print(f"\n   📈 Trailing SL activated for {trade['symbol']}! SL moved to breakeven ({entry_price:.2f})")
        
        # Check if trailing SL (breakeven) is hit
        if self.trailing_triggered.get(trade_id):
            if trend == 'BULLISH':
                if current_price <= entry_price:
                    self.logger.info(f"🔄 Trailing SL (BE) hit for {trade['symbol']}: "
                                   f"{current_price:.2f} <= {entry_price:.2f}")
                    return 'TRAILING'
            else:
                if current_price >= entry_price:
                    self.logger.info(f"🔄 Trailing SL (BE) hit for {trade['symbol']}: "
                                   f"{current_price:.2f} >= {entry_price:.2f}")
                    return 'TRAILING'
        
        return None
    
    def _force_exit_all(self):
        """
        Force exit all remaining positions (end of day)
        """
        active_trades = self.order_executor.get_active_trades()
        
        if not active_trades:
            return
        
        self.logger.info(f"⏰ Force exiting {len(active_trades)} positions at {FORCE_EXIT_TIME}")
        print(f"\n   ⏰ Force exit time ({FORCE_EXIT_TIME}) reached!")
        print(f"   Closing {len(active_trades)} remaining positions...")
        
        for trade in active_trades[:]:
            self.order_executor.exit_trade(trade, 'TIME')
    
    def stop_monitoring(self):
        """
        Stop the monitoring loop
        """
        self.is_running = False
        self.logger.info("🛑 Position monitoring stopped")
    
    def get_position_status(self, trade: Dict) -> Dict:
        """
        Get current status of a position
        
        Args:
            trade: Trade data dict
            
        Returns:
            Dict with position status
        """
        symbol = trade['symbol']
        token = trade['token']
        
        ltp_data = self.api.get_ltp('NSE', symbol, token)
        current_price = ltp_data.get('ltp', 0) if ltp_data else 0
        
        entry_price = trade['entry_price']
        stop_loss = trade['stop_loss']
        take_profit = trade['take_profit']
        trend = trade['trend']
        
        # Calculate unrealized P&L
        if trend == 'BULLISH':
            unrealized_pnl = (current_price - entry_price) * trade['quantity']
            unrealized_pct = ((current_price - entry_price) / entry_price) * 100
        else:
            unrealized_pnl = (entry_price - current_price) * trade['quantity']
            unrealized_pct = ((entry_price - current_price) / entry_price) * 100
        
        # Check if trailing is active
        trailing_active = self.trailing_triggered.get(trade['trade_id'], False)
        effective_sl = entry_price if trailing_active else stop_loss
        
        return {
            'trade_id': trade['trade_id'],
            'symbol': symbol,
            'trend': trend,
            'entry_price': entry_price,
            'current_price': current_price,
            'stop_loss': effective_sl,
            'take_profit': take_profit,
            'unrealized_pnl': unrealized_pnl,
            'unrealized_pct': unrealized_pct,
            'trailing_active': trailing_active,
            'status': trade['status']
        }
    
    def display_all_positions(self):
        """
        Display status of all active positions
        """
        active_trades = self.order_executor.get_active_trades()
        
        if not active_trades:
            print("\n   No active positions.")
            return
        
        print(f"\n   {'═' * 80}")
        print(f"   ACTIVE POSITIONS")
        print(f"   {'─' * 80}")
        print(f"   {'Symbol':<12}{'Trend':<10}{'Entry':>10}{'Current':>10}{'SL':>10}{'TP':>10}{'P&L %':>10}{'Trail':>8}")
        print(f"   {'─' * 80}")
        
        total_pnl = 0
        
        for trade in active_trades:
            status = self.get_position_status(trade)
            
            indicator = "🟢" if status['unrealized_pct'] > 0 else "🔴" if status['unrealized_pct'] < 0 else "⚪"
            trail_status = "✅" if status['trailing_active'] else "❌"
            
            print(f"   {status['symbol']:<12}{status['trend']:<10}"
                  f"{status['entry_price']:>10.2f}{status['current_price']:>10.2f}"
                  f"{status['stop_loss']:>10.2f}{status['take_profit']:>10.2f}"
                  f"{status['unrealized_pct']:>+9.2f}% {indicator} {trail_status}")
            
            total_pnl += status['unrealized_pnl']
        
        print(f"   {'─' * 80}")
        print(f"   Total Unrealized P&L: {total_pnl:>+.2f}")
        print(f"   {'═' * 80}\n")
