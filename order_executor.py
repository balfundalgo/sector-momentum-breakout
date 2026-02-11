"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         ORDER EXECUTOR MODULE                                  ║
║            Places Option (PE/CE) and Future orders for the strategy           ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import time
import uuid
from datetime import datetime
from typing import Optional, Dict, List

import sys
import os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    LOTS_PER_TRADE, RISK_REWARD_RATIO, PAPER_TRADING,
    OPTION_EXPIRY, FUTURE_EXPIRY
)


class OrderExecutor:
    """
    Executes trades by placing Option and Future orders
    """
    
    def __init__(self, api, data_fetcher, logger):
        """
        Initialize order executor
        
        Args:
            api: AngelOneAPI instance
            data_fetcher: DataFetcher instance
            logger: StrategyLogger instance
        """
        self.api = api
        self.data_fetcher = data_fetcher
        self.logger = logger
        
        self.active_trades = []
        self.order_history = []
    
    def execute_entry(self, stock: Dict, trend: str, entry_price: float, 
                      stop_loss: float) -> Optional[Dict]:
        """
        Execute entry by placing Option + Future orders
        
        For BULLISH:
            1. BUY ATM PE (Put Option) - First
            2. BUY FUTURE - Second
            
        For BEARISH:
            1. BUY ATM CE (Call Option) - First
            2. SELL/SHORT FUTURE - Second
        
        Args:
            stock: Stock data dict
            trend: 'BULLISH' or 'BEARISH'
            entry_price: Entry price (spot)
            stop_loss: Stop loss level
            
        Returns:
            Dict with trade data or None
        """
        self.logger.print_banner("ORDER EXECUTION PHASE")
        
        symbol = stock['symbol']
        lot_size = stock.get('lot_size', self.data_fetcher.get_lot_size(symbol) or 1)
        quantity = lot_size * LOTS_PER_TRADE
        
        # Calculate ATM strike based on spot price
        strike_interval = self.data_fetcher.get_strike_interval(symbol)
        atm_strike = self.api.get_atm_strike(entry_price, strike_interval)
        
        # Calculate take profit (1:2 risk-reward)
        sl_distance = abs(entry_price - stop_loss)
        
        if trend == 'BULLISH':
            take_profit = entry_price + (sl_distance * RISK_REWARD_RATIO)
        else:
            take_profit = entry_price - (sl_distance * RISK_REWARD_RATIO)
        
        # Generate trade ID
        trade_id = str(uuid.uuid4())[:8].upper()
        
        print(f"\n   ╔{'═' * 60}╗")
        print(f"   ║  EXECUTING {trend} TRADE")
        print(f"   ╠{'═' * 60}╣")
        print(f"   ║  Trade ID:      {trade_id:<40}")
        print(f"   ║  Symbol:        {symbol:<40}")
        print(f"   ║  Entry Price:   {entry_price:>15.2f}")
        print(f"   ║  Stop Loss:     {stop_loss:>15.2f}")
        print(f"   ║  Take Profit:   {take_profit:>15.2f}")
        print(f"   ║  ATM Strike:    {atm_strike:>15.0f}")
        print(f"   ║  Lot Size:      {lot_size:>15}")
        print(f"   ║  Quantity:      {quantity:>15}")
        print(f"   ╠{'═' * 60}╣")
        
        trade_data = {
            'trade_id': trade_id,
            'symbol': symbol,
            'token': stock['token'],
            'trend': trend,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'sl_distance': sl_distance,
            'lot_size': lot_size,
            'quantity': quantity,
            'atm_strike': atm_strike,
            'entry_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'status': 'PENDING',
            'option_order': None,
            'future_order': None
        }
        
        # Step 1: Place Option Order (First Leg)
        option_order = self._place_option_order(stock, trend, atm_strike, quantity)
        
        if option_order:
            trade_data['option_order'] = option_order
            print(f"   ║  ✅ Option Order Placed")
            print(f"   ║     Symbol: {option_order.get('trading_symbol', 'N/A')}")
            print(f"   ║     Order ID: {option_order.get('order_id', 'N/A')}")
        else:
            print(f"   ║  ❌ Option Order Failed")
            trade_data['status'] = 'FAILED'
            return trade_data
        
        time.sleep(0.5)  # Small delay between orders
        
        # Step 2: Place Future Order (Second Leg)
        future_order = self._place_future_order(stock, trend, quantity)
        
        if future_order:
            trade_data['future_order'] = future_order
            print(f"   ║  ✅ Future Order Placed")
            print(f"   ║     Symbol: {future_order.get('trading_symbol', 'N/A')}")
            print(f"   ║     Order ID: {future_order.get('order_id', 'N/A')}")
        else:
            print(f"   ║  ❌ Future Order Failed")
            # TODO: Consider rolling back option order
            trade_data['status'] = 'PARTIAL'
        
        # Update status
        if trade_data['option_order'] and trade_data['future_order']:
            trade_data['status'] = 'OPEN'
            self.active_trades.append(trade_data)
        
        print(f"   ╠{'═' * 60}╣")
        print(f"   ║  Trade Status: {trade_data['status']:<40}")
        print(f"   ╚{'═' * 60}╝\n")
        
        # Log trade entry
        self.logger.log_trade_entry({
            'trade_id': trade_id,
            'symbol': symbol,
            'trade_type': trend,
            'direction': 'LONG' if trend == 'BULLISH' else 'SHORT',
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'quantity': quantity,
            'option_symbol': option_order.get('trading_symbol', '') if option_order else '',
            'option_entry_price': option_order.get('price', 0) if option_order else 0,
            'option_quantity': quantity,
            'future_symbol': future_order.get('trading_symbol', '') if future_order else '',
            'future_entry_price': future_order.get('price', 0) if future_order else 0,
            'future_quantity': quantity
        })
        
        self.order_history.append(trade_data)
        
        return trade_data
    
    def _place_option_order(self, stock: Dict, trend: str, strike: float, 
                           quantity: int) -> Optional[Dict]:
        """
        Place option order
        
        Args:
            stock: Stock data dict
            trend: 'BULLISH' or 'BEARISH'
            strike: Strike price
            quantity: Number of lots
            
        Returns:
            Dict with order details or None
        """
        symbol = stock['symbol']
        option_type = 'PE' if trend == 'BULLISH' else 'CE'
        expiry_type = 'current_week' if OPTION_EXPIRY == 'WEEKLY' else 'current_month'
        
        self.logger.info(f"📝 Placing {option_type} Option order for {symbol} @ {strike}")
        
        # Get option contract
        option_contract = self.api.get_option_contract(
            symbol=symbol,
            strike=strike,
            option_type=option_type,
            expiry_type=expiry_type
        )
        
        if not option_contract:
            self.logger.error(f"❌ Could not find {option_type} contract for {symbol} @ {strike}")
            return None
        
        trading_symbol = option_contract['symbol']
        token = str(option_contract['token'])
        
        if PAPER_TRADING:
            # Simulate order
            self.logger.info(f"📝 [PAPER] BUY {quantity} {trading_symbol}")
            
            # Get current LTP for the option
            ltp_data = self.api.get_ltp('NFO', trading_symbol, token)
            option_price = ltp_data.get('ltp', 0) if ltp_data else 0
            
            return {
                'order_id': f"PAPER_{uuid.uuid4().hex[:8].upper()}",
                'trading_symbol': trading_symbol,
                'token': token,
                'transaction_type': 'BUY',
                'quantity': quantity,
                'price': option_price,
                'status': 'COMPLETE',
                'paper_trade': True
            }
        else:
            # Place real order
            try:
                response = self.api.place_order(
                    variety='NORMAL',
                    tradingsymbol=trading_symbol,
                    symboltoken=token,
                    transactiontype='BUY',
                    exchange='NFO',
                    ordertype='MARKET',
                    producttype='CARRYFORWARD',
                    duration='DAY',
                    price=0,
                    quantity=quantity
                )
                
                if response and response.get('status'):
                    return {
                        'order_id': response.get('data', {}).get('orderid', ''),
                        'trading_symbol': trading_symbol,
                        'token': token,
                        'transaction_type': 'BUY',
                        'quantity': quantity,
                        'status': 'PLACED'
                    }
                else:
                    self.logger.error(f"❌ Option order failed: {response}")
                    return None
                    
            except Exception as e:
                self.logger.error(f"❌ Option order error: {e}")
                return None
    
    def _place_future_order(self, stock: Dict, trend: str, quantity: int) -> Optional[Dict]:
        """
        Place future order
        
        Args:
            stock: Stock data dict
            trend: 'BULLISH' or 'BEARISH'
            quantity: Number of lots
            
        Returns:
            Dict with order details or None
        """
        symbol = stock['symbol']
        transaction_type = 'BUY' if trend == 'BULLISH' else 'SELL'
        expiry_type = 'current_month' if FUTURE_EXPIRY == 'MONTHLY' else 'current_month'
        
        self.logger.info(f"📝 Placing {transaction_type} Future order for {symbol}")
        
        # Get future contract
        future_contract = self.api.get_future_contract(
            symbol=symbol,
            expiry_type=expiry_type
        )
        
        if not future_contract:
            self.logger.error(f"❌ Could not find Future contract for {symbol}")
            return None
        
        trading_symbol = future_contract['symbol']
        token = str(future_contract['token'])
        
        if PAPER_TRADING:
            # Simulate order
            self.logger.info(f"📝 [PAPER] {transaction_type} {quantity} {trading_symbol}")
            
            # Get current LTP for the future
            ltp_data = self.api.get_ltp('NFO', trading_symbol, token)
            future_price = ltp_data.get('ltp', 0) if ltp_data else 0
            
            return {
                'order_id': f"PAPER_{uuid.uuid4().hex[:8].upper()}",
                'trading_symbol': trading_symbol,
                'token': token,
                'transaction_type': transaction_type,
                'quantity': quantity,
                'price': future_price,
                'status': 'COMPLETE',
                'paper_trade': True
            }
        else:
            # Place real order
            try:
                response = self.api.place_order(
                    variety='NORMAL',
                    tradingsymbol=trading_symbol,
                    symboltoken=token,
                    transactiontype=transaction_type,
                    exchange='NFO',
                    ordertype='MARKET',
                    producttype='CARRYFORWARD',
                    duration='DAY',
                    price=0,
                    quantity=quantity
                )
                
                if response and response.get('status'):
                    return {
                        'order_id': response.get('data', {}).get('orderid', ''),
                        'trading_symbol': trading_symbol,
                        'token': token,
                        'transaction_type': transaction_type,
                        'quantity': quantity,
                        'status': 'PLACED'
                    }
                else:
                    self.logger.error(f"❌ Future order failed: {response}")
                    return None
                    
            except Exception as e:
                self.logger.error(f"❌ Future order error: {e}")
                return None
    
    def exit_trade(self, trade: Dict, reason: str) -> bool:
        """
        Exit a trade by closing both Option and Future positions
        
        Args:
            trade: Trade data dict
            reason: Exit reason (SL/TP/TRAILING/TIME/MANUAL)
            
        Returns:
            True if exit successful
        """
        self.logger.info(f"🚪 Exiting trade {trade['trade_id']} - Reason: {reason}")
        
        print(f"\n   ╔{'═' * 60}╗")
        print(f"   ║  EXITING TRADE: {trade['trade_id']}")
        print(f"   ║  Reason: {reason}")
        print(f"   ╠{'═' * 60}╣")
        
        success = True
        
        # Exit Option position
        if trade.get('option_order'):
            option_exit = self._exit_option(trade)
            if option_exit:
                print(f"   ║  ✅ Option Position Closed")
            else:
                print(f"   ║  ❌ Option Exit Failed")
                success = False
        
        # Exit Future position
        if trade.get('future_order'):
            future_exit = self._exit_future(trade)
            if future_exit:
                print(f"   ║  ✅ Future Position Closed")
            else:
                print(f"   ║  ❌ Future Exit Failed")
                success = False
        
        # Calculate P&L (simplified)
        pnl = self._calculate_pnl(trade, reason)
        
        print(f"   ╠{'═' * 60}╣")
        print(f"   ║  P&L: {pnl:>+15.2f}")
        print(f"   ╚{'═' * 60}╝\n")
        
        # Update trade status
        trade['status'] = 'CLOSED'
        trade['exit_reason'] = reason
        trade['exit_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        trade['pnl'] = pnl
        
        # Log exit
        self.logger.log_trade_exit(
            trade_id=trade['trade_id'],
            exit_price=trade.get('exit_price', 0),
            exit_reason=reason,
            pnl=pnl
        )
        
        # Remove from active trades
        if trade in self.active_trades:
            self.active_trades.remove(trade)
        
        return success
    
    def _exit_option(self, trade: Dict) -> bool:
        """
        Exit option position
        """
        option_order = trade['option_order']
        trading_symbol = option_order['trading_symbol']
        token = option_order['token']
        quantity = option_order['quantity']
        
        if PAPER_TRADING:
            self.logger.info(f"📝 [PAPER] SELL {quantity} {trading_symbol}")
            return True
        else:
            try:
                response = self.api.place_order(
                    variety='NORMAL',
                    tradingsymbol=trading_symbol,
                    symboltoken=token,
                    transactiontype='SELL',
                    exchange='NFO',
                    ordertype='MARKET',
                    producttype='CARRYFORWARD',
                    duration='DAY',
                    price=0,
                    quantity=quantity
                )
                return response and response.get('status')
            except Exception as e:
                self.logger.error(f"❌ Option exit error: {e}")
                return False
    
    def _exit_future(self, trade: Dict) -> bool:
        """
        Exit future position
        """
        future_order = trade['future_order']
        trading_symbol = future_order['trading_symbol']
        token = future_order['token']
        quantity = future_order['quantity']
        
        # Reverse the original transaction
        exit_type = 'SELL' if future_order['transaction_type'] == 'BUY' else 'BUY'
        
        if PAPER_TRADING:
            self.logger.info(f"📝 [PAPER] {exit_type} {quantity} {trading_symbol}")
            return True
        else:
            try:
                response = self.api.place_order(
                    variety='NORMAL',
                    tradingsymbol=trading_symbol,
                    symboltoken=token,
                    transactiontype=exit_type,
                    exchange='NFO',
                    ordertype='MARKET',
                    producttype='CARRYFORWARD',
                    duration='DAY',
                    price=0,
                    quantity=quantity
                )
                return response and response.get('status')
            except Exception as e:
                self.logger.error(f"❌ Future exit error: {e}")
                return False
    
    def _calculate_pnl(self, trade: Dict, reason: str) -> float:
        """
        Calculate P&L for a trade (simplified)
        """
        # In paper trading, estimate P&L based on exit reason
        entry_price = trade['entry_price']
        sl_distance = trade['sl_distance']
        quantity = trade['quantity']
        
        if reason == 'TP':
            # Hit take profit
            points = sl_distance * RISK_REWARD_RATIO
        elif reason == 'SL':
            # Hit stop loss
            points = -sl_distance
        elif reason == 'TRAILING':
            # Trailing stop (breakeven or better)
            points = 0
        else:
            # Time exit or manual - assume small loss/gain
            points = 0
        
        # Adjust for direction
        if trade['trend'] == 'BEARISH':
            points = -points
        
        # Calculate P&L (simplified - actual would need option premium)
        # For futures: points × quantity
        pnl = points * quantity
        
        return pnl
    
    def get_active_trades(self) -> List[Dict]:
        """
        Get list of active trades
        
        Returns:
            List of active trade dicts
        """
        return self.active_trades
    
    def get_trade_count(self) -> int:
        """
        Get number of trades executed today
        
        Returns:
            Number of trades
        """
        return len(self.order_history)
