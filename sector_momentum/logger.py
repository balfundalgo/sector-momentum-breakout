"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                            LOGGER UTILITY                                      ║
║                 Handles logging and trade record keeping                       ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import csv
import logging
from datetime import datetime
from typing import Dict, Optional

import sys
sys.path.append('..')
from config import LOG_LEVEL, LOG_TO_FILE, LOG_TO_CONSOLE


class StrategyLogger:
    """
    Logger for strategy execution and trade records
    """
    
    def __init__(self, log_dir: str = "logs"):
        """
        Initialize logger
        
        Args:
            log_dir: Directory for log files
        """
        self.log_dir = log_dir
        self.today = datetime.now().strftime("%Y-%m-%d")
        
        # Create log directory if not exists
        os.makedirs(log_dir, exist_ok=True)
        
        # Setup logging
        self._setup_logging()
        
        # Trade log file
        self.trade_log_file = os.path.join(log_dir, f"trades_{self.today}.csv")
        self._init_trade_log()
    
    def _setup_logging(self):
        """
        Setup Python logging
        """
        self.logger = logging.getLogger("SectorMomentum")
        self.logger.setLevel(getattr(logging, LOG_LEVEL))
        
        # Clear existing handlers
        self.logger.handlers = []
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        if LOG_TO_CONSOLE:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # File handler
        if LOG_TO_FILE:
            log_file = os.path.join(self.log_dir, f"strategy_{self.today}.log")
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def _init_trade_log(self):
        """
        Initialize trade log CSV file
        """
        if not os.path.exists(self.trade_log_file):
            headers = [
                'timestamp', 'trade_id', 'symbol', 'trade_type', 'direction',
                'entry_price', 'stop_loss', 'take_profit', 'quantity',
                'option_symbol', 'option_entry_price', 'option_quantity',
                'future_symbol', 'future_entry_price', 'future_quantity',
                'exit_price', 'exit_time', 'exit_reason', 'pnl', 'status'
            ]
            with open(self.trade_log_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
    
    def info(self, message: str):
        """Log info message"""
        self.logger.info(message)
    
    def debug(self, message: str):
        """Log debug message"""
        self.logger.debug(message)
    
    def warning(self, message: str):
        """Log warning message"""
        self.logger.warning(message)
    
    def error(self, message: str):
        """Log error message"""
        self.logger.error(message)
    
    def log_trade_entry(self, trade: Dict):
        """
        Log a trade entry
        
        Args:
            trade: Dict with trade details
        """
        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            trade.get('trade_id', ''),
            trade.get('symbol', ''),
            trade.get('trade_type', ''),  # BULLISH/BEARISH
            trade.get('direction', ''),    # LONG/SHORT
            trade.get('entry_price', 0),
            trade.get('stop_loss', 0),
            trade.get('take_profit', 0),
            trade.get('quantity', 0),
            trade.get('option_symbol', ''),
            trade.get('option_entry_price', 0),
            trade.get('option_quantity', 0),
            trade.get('future_symbol', ''),
            trade.get('future_entry_price', 0),
            trade.get('future_quantity', 0),
            '',  # exit_price
            '',  # exit_time
            '',  # exit_reason
            '',  # pnl
            'OPEN'
        ]
        
        with open(self.trade_log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(row)
        
        self.info(f"📝 Trade Entry Logged: {trade.get('symbol')} - {trade.get('direction')}")
    
    def log_trade_exit(self, trade_id: str, exit_price: float, exit_reason: str, pnl: float):
        """
        Log trade exit by updating the CSV
        
        Args:
            trade_id: Trade ID to update
            exit_price: Exit price
            exit_reason: Reason for exit (SL/TP/TRAILING/TIME/MANUAL)
            pnl: Profit/Loss amount
        """
        # Read all rows
        rows = []
        with open(self.trade_log_file, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # Find and update the trade
        headers = rows[0]
        trade_id_idx = headers.index('trade_id')
        exit_price_idx = headers.index('exit_price')
        exit_time_idx = headers.index('exit_time')
        exit_reason_idx = headers.index('exit_reason')
        pnl_idx = headers.index('pnl')
        status_idx = headers.index('status')
        
        for i, row in enumerate(rows[1:], 1):
            if row[trade_id_idx] == trade_id:
                rows[i][exit_price_idx] = exit_price
                rows[i][exit_time_idx] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                rows[i][exit_reason_idx] = exit_reason
                rows[i][pnl_idx] = pnl
                rows[i][status_idx] = 'CLOSED'
                break
        
        # Write back
        with open(self.trade_log_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        
        self.info(f"📝 Trade Exit Logged: {trade_id} - {exit_reason} - PnL: {pnl}")
    
    def log_event(self, event_type: str, details: Dict):
        """
        Log a strategy event
        
        Args:
            event_type: Type of event
            details: Event details
        """
        event_file = os.path.join(self.log_dir, f"events_{self.today}.csv")
        
        # Initialize file if not exists
        if not os.path.exists(event_file):
            with open(event_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'event_type', 'details'])
        
        with open(event_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                event_type,
                str(details)
            ])
    
    def get_daily_summary(self) -> Dict:
        """
        Get summary of today's trades
        
        Returns:
            Dict with trade summary
        """
        if not os.path.exists(self.trade_log_file):
            return {'total_trades': 0, 'open_trades': 0, 'closed_trades': 0, 'total_pnl': 0}
        
        total_trades = 0
        open_trades = 0
        closed_trades = 0
        total_pnl = 0
        winners = 0
        losers = 0
        
        with open(self.trade_log_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                total_trades += 1
                if row['status'] == 'OPEN':
                    open_trades += 1
                else:
                    closed_trades += 1
                    pnl = float(row['pnl']) if row['pnl'] else 0
                    total_pnl += pnl
                    if pnl > 0:
                        winners += 1
                    elif pnl < 0:
                        losers += 1
        
        return {
            'total_trades': total_trades,
            'open_trades': open_trades,
            'closed_trades': closed_trades,
            'winners': winners,
            'losers': losers,
            'total_pnl': total_pnl,
            'win_rate': (winners / closed_trades * 100) if closed_trades > 0 else 0
        }
    
    def print_banner(self, text: str, char: str = "═"):
        """
        Print a formatted banner
        """
        print("\n" + char * 80)
        print(f"   {text}")
        print(char * 80)


# Singleton instance
_logger_instance = None

def get_logger() -> StrategyLogger:
    """
    Get singleton logger instance
    """
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = StrategyLogger()
    return _logger_instance
