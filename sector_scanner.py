"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                          SECTOR SCANNER MODULE                                 ║
║              Scans all sectors and ranks by performance                        ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import time
import sys
import os
from datetime import datetime
from typing import Optional, Dict, List, Tuple

# Add script's directory to path for flat structure
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import SECTORAL_INDICES


class SectorScanner:
    """
    Scans and ranks all NIFTY sectoral indices by performance
    """
    
    def __init__(self, api, logger):
        """
        Initialize sector scanner
        
        Args:
            api: AngelOneAPI instance
            logger: StrategyLogger instance
        """
        self.api = api
        self.logger = logger
        self.sector_data = {}
        self.ranked_sectors = []
    
    def scan_all_sectors(self) -> List[Dict]:
        """
        Scan all sectoral indices and calculate performance
        
        Returns:
            List of sector data sorted by change percentage
        """
        self.logger.print_banner("SECTOR SCANNING PHASE")
        self.logger.info("📊 Scanning all sectoral indices...")
        print("\n   Scanning sectoral indices...\n")
        
        results = []
        
        for sector_name, (symbol, token, exchange) in SECTORAL_INDICES.items():
            try:
                # Fetch LTP data
                data = self.api.get_ltp(exchange, symbol, token)
                
                if data and data.get('ltp'):
                    ltp = float(data.get('ltp', 0))
                    close = float(data.get('close', 0))  # Previous close
                    
                    # Skip invalid data - need both LTP and previous close for change calc
                    if ltp < 100:
                        self.logger.warning(f"⚠️ Invalid LTP for {sector_name}: LTP={ltp}")
                        continue
                    if close == 0:
                        self.logger.warning(f"⚠️ Missing previous close for {sector_name}: LTP={ltp}, close=0")
                        continue
                    
                    # Calculate change (NSE standard formula)
                    change = ltp - close
                    change_pct = (change / close) * 100
                    
                    sector_info = {
                        'name': sector_name,
                        'symbol': symbol,
                        'token': token,
                        'exchange': exchange,
                        'ltp': ltp,
                        'prev_close': close,
                        'change': change,
                        'change_pct': change_pct
                    }
                    
                    results.append(sector_info)
                    self.sector_data[sector_name] = sector_info
                    
                    # Display progress
                    indicator = "🟢" if change_pct > 0 else "🔴" if change_pct < 0 else "⚪"
                    print(f"   {indicator} {sector_name:<25} {ltp:>10.2f} ({change_pct:>+6.2f}%)")
                    
                else:
                    self.logger.warning(f"⚠️ No data for {sector_name}")
                    
            except Exception as e:
                self.logger.error(f"❌ Error scanning {sector_name}: {e}")
            
            # Rate limiting is now handled by api_rate_limiter in angel_api.py
        
        # Sort by change percentage (descending)
        self.ranked_sectors = sorted(results, key=lambda x: x['change_pct'], reverse=True)
        
        self.logger.info(f"📊 Scanned {len(results)} sectors successfully")
        
        return self.ranked_sectors
    
    def get_best_sector(self) -> Optional[Dict]:
        """
        Get the best performing sector
        
        Returns:
            Dict with best sector data or None
        """
        if not self.ranked_sectors:
            self.scan_all_sectors()
        
        if self.ranked_sectors:
            best = self.ranked_sectors[0]
            self.logger.info(f"🏆 Best Sector: {best['name']} ({best['change_pct']:+.2f}%)")
            return best
        
        return None
    
    def get_worst_sector(self) -> Optional[Dict]:
        """
        Get the worst performing sector
        
        Returns:
            Dict with worst sector data or None
        """
        if not self.ranked_sectors:
            self.scan_all_sectors()
        
        if self.ranked_sectors:
            worst = self.ranked_sectors[-1]
            self.logger.info(f"📉 Worst Sector: {worst['name']} ({worst['change_pct']:+.2f}%)")
            return worst
        
        return None
    
    def select_sector_for_trend(self, trend: str) -> Optional[Dict]:
        """
        Select sector based on trend
        
        Args:
            trend: 'BULLISH' or 'BEARISH'
            
        Returns:
            Dict with selected sector data
        """
        if trend == 'BULLISH':
            sector = self.get_best_sector()
            direction = "BEST"
        else:
            sector = self.get_worst_sector()
            direction = "WORST"
        
        if sector:
            print(f"\n   ╔{'═' * 50}╗")
            print(f"   ║  SELECTED SECTOR ({direction} PERFORMER)")
            print(f"   ╠{'═' * 50}╣")
            print(f"   ║  Sector:     {sector['name']:<30}")
            print(f"   ║  LTP:        {sector['ltp']:>15.2f}")
            print(f"   ║  Change:     {sector['change_pct']:>+14.2f}%")
            print(f"   ╚{'═' * 50}╝\n")
            
            self.logger.log_event('SECTOR_SELECTED', {
                'trend': trend,
                'sector': sector['name'],
                'change_pct': sector['change_pct']
            })
        
        return sector
    
    def display_sector_ranking(self):
        """
        Display full sector ranking
        """
        if not self.ranked_sectors:
            self.scan_all_sectors()
        
        print(f"\n   {'═' * 70}")
        print(f"   {'Rank':<6}{'Sector':<30}{'LTP':>12}{'Change':>12}{'Change %':>10}")
        print(f"   {'─' * 70}")
        
        for i, sector in enumerate(self.ranked_sectors, 1):
            indicator = "🟢" if sector['change_pct'] > 0 else "🔴" if sector['change_pct'] < 0 else "⚪"
            print(f"   {i:<6}{sector['name']:<30}{sector['ltp']:>12.2f}"
                  f"{sector['change']:>+12.2f}{sector['change_pct']:>+9.2f}% {indicator}")
        
        print(f"   {'═' * 70}\n")
        
        # Top gainers and losers
        gainers = [s for s in self.ranked_sectors if s['change_pct'] > 0]
        losers = [s for s in self.ranked_sectors if s['change_pct'] < 0]
        
        if gainers:
            print("   🏆 TOP GAINERS:")
            for s in gainers[:3]:
                print(f"      {s['name']}: {s['change_pct']:+.2f}%")
        
        if losers:
            print("\n   📉 TOP LOSERS:")
            for s in losers[-3:][::-1]:
                print(f"      {s['name']}: {s['change_pct']:+.2f}%")
        
        print()
    
    def get_sector_by_name(self, name: str) -> Optional[Dict]:
        """
        Get sector data by name
        
        Args:
            name: Sector name
            
        Returns:
            Dict with sector data or None
        """
        return self.sector_data.get(name)
    
    def get_all_sectors(self) -> List[Dict]:
        """
        Get all sector data
        
        Returns:
            List of all sector data
        """
        return self.ranked_sectors
