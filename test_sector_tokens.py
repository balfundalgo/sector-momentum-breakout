"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                      TEST SECTOR TOKENS - LIVE VERIFICATION                   ║
║              Connects to Angel One and tests each sector token                ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Usage: python test_sector_tokens.py

This will connect to Angel One API and test all configured sector tokens
to verify they return valid LTP data.
"""

import sys
import time
import pyotp
from SmartApi import SmartConnect

# Configuration
CLIENT_ID = 'AABY083324'
API_KEY = 'Ce0Jc3hq'
MPIN = '2825'
TOTP_SECRET = 'VRIVIHGYF3KIYNWNXO7EXYCXQI'

# Sector tokens to test - ALL VERIFIED FROM INSTRUMENT MASTER (discover_tokens.py)
SECTORS_TO_TEST = {
    "NIFTY 50": ("Nifty 50", "99926000"),
    "NIFTY BANK": ("Nifty Bank", "99926009"),
    "NIFTY IT": ("Nifty IT", "99926008"),
    "NIFTY REALTY": ("Nifty Realty", "99926018"),
    "NIFTY INFRA": ("Nifty Infra", "99926019"),
    "NIFTY ENERGY": ("Nifty Energy", "99926020"),
    "NIFTY FMCG": ("Nifty FMCG", "99926021"),
    "NIFTY MNC": ("Nifty MNC", "99926022"),
    "NIFTY PHARMA": ("Nifty Pharma", "99926023"),
    "NIFTY PSE": ("Nifty PSE", "99926024"),
    "NIFTY PSU BANK": ("Nifty PSU Bank", "99926025"),
    "NIFTY SERV SECTOR": ("Nifty Serv Sector", "99926026"),
    "NIFTY AUTO": ("Nifty Auto", "99926029"),
    "NIFTY METAL": ("Nifty Metal", "99926030"),
    "NIFTY MEDIA": ("Nifty Media", "99926031"),
    "NIFTY COMMODITIES": ("Nifty Commodities", "99926035"),
    "NIFTY CONSUMPTION": ("Nifty Consumption", "99926036"),
    "NIFTY FIN SERVICE": ("Nifty Fin Service", "99926037"),
    "NIFTY PVT BANK": ("Nifty Pvt Bank", "99926047"),
}

# Alternative tokens to try if main ones fail
ALTERNATIVE_TOKENS = {
    "NIFTY ENERGY": [
        ("Nifty Energy", "99926027"),
        ("NIFTY ENERGY", "99926027"),
        ("Nifty Energy", "99926017"),  # Old token (India VIX - wrong)
    ],
    "NIFTY INFRA": [
        ("Nifty Infra", "99926028"),
        ("NIFTY INFRA", "99926028"),
        ("Nifty Infrastructure", "99926028"),
    ],
    "NIFTY FIN SERVICE": [
        ("Nifty Fin Service", "99926034"),
        ("Nifty Financial Services", "99926034"),
        ("NIFTY FIN SERVICE", "99926034"),
        ("Nifty Serv Sector", "99926026"),
    ],
}


def test_sector_tokens():
    """
    Test all sector tokens against live API
    """
    print("\n" + "=" * 80)
    print("   TESTING SECTOR TOKENS AGAINST ANGEL ONE API")
    print("=" * 80)
    
    # Connect to API
    print("\n🔌 Connecting to Angel One API...")
    try:
        totp = pyotp.TOTP(TOTP_SECRET).now()
        print(f"   Generated TOTP: {totp}")
        
        obj = SmartConnect(api_key=API_KEY)
        data = obj.generateSession(CLIENT_ID, MPIN, totp)
        
        if not data.get('status'):
            print(f"   ❌ Connection failed: {data.get('message')}")
            return
        
        print(f"   ✅ Connected successfully!")
        print(f"   Client: {CLIENT_ID}\n")
        
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
        return
    
    # Test each sector
    print("=" * 90)
    print(f"{'Sector':<25} {'Symbol':<25} {'Token':<12} {'LTP':>12} {'Status':<10}")
    print("-" * 90)
    
    working = []
    failing = []
    
    for sector_name, (symbol, token) in SECTORS_TO_TEST.items():
        try:
            result = obj.ltpData("NSE", symbol, token)
            
            if result.get('status') and result.get('data'):
                ltp = result['data'].get('ltp', 0)
                close = result['data'].get('close', 0)
                
                # Validate LTP is reasonable (not India VIX which is around 10-20)
                if ltp > 100:  # Most indices are > 100
                    status = "✅ OK"
                    working.append(sector_name)
                else:
                    status = f"⚠️ LTP={ltp}"
                    failing.append((sector_name, symbol, token, f"Low LTP: {ltp}"))
            else:
                ltp = "N/A"
                status = "❌ Failed"
                failing.append((sector_name, symbol, token, result.get('message', 'Unknown error')))
                
        except Exception as e:
            ltp = "N/A"
            status = "❌ Error"
            failing.append((sector_name, symbol, token, str(e)))
        
        print(f"{sector_name:<25} {symbol:<25} {token:<12} {str(ltp):>12} {status:<10}")
        time.sleep(0.15)  # Rate limiting
    
    print("=" * 90)
    
    # Summary
    print(f"\n📊 SUMMARY:")
    print(f"   ✅ Working: {len(working)}/{len(SECTORS_TO_TEST)}")
    print(f"   ❌ Failing: {len(failing)}/{len(SECTORS_TO_TEST)}")
    
    if failing:
        print(f"\n⚠️ FAILING SECTORS:")
        for sector, symbol, token, error in failing:
            print(f"   • {sector}: {error}")
        
        # Try alternative tokens for failing sectors
        print("\n\n" + "=" * 80)
        print("   TRYING ALTERNATIVE TOKENS FOR FAILING SECTORS")
        print("=" * 80 + "\n")
        
        for sector, _, _, _ in failing:
            if sector in ALTERNATIVE_TOKENS:
                print(f"\n🔍 Trying alternatives for {sector}:")
                
                for alt_symbol, alt_token in ALTERNATIVE_TOKENS[sector]:
                    try:
                        result = obj.ltpData("NSE", alt_symbol, alt_token)
                        
                        if result.get('status') and result.get('data'):
                            ltp = result['data'].get('ltp', 0)
                            if ltp > 100:
                                print(f"   ✅ FOUND: Symbol='{alt_symbol}', Token='{alt_token}', LTP={ltp}")
                            else:
                                print(f"   ⚠️ Low LTP: Symbol='{alt_symbol}', Token='{alt_token}', LTP={ltp}")
                        else:
                            print(f"   ❌ Failed: Symbol='{alt_symbol}', Token='{alt_token}'")
                            
                    except Exception as e:
                        print(f"   ❌ Error: Symbol='{alt_symbol}', Token='{alt_token}' - {e}")
                    
                    time.sleep(0.15)
    
    # Test some additional tokens to find correct ones
    print("\n\n" + "=" * 80)
    print("   SCANNING ADDITIONAL TOKENS (99926024 - 99926040)")
    print("=" * 80 + "\n")
    
    print(f"{'Token':<15} {'LTP':>12} {'Close':>12} {'Possible Index':<30}")
    print("-" * 70)
    
    for i in range(24, 41):
        token = f"999260{i:02d}"
        try:
            # Try with generic symbol
            result = obj.ltpData("NSE", f"Nifty {i}", token)
            
            if result.get('status') and result.get('data'):
                ltp = result['data'].get('ltp', 0)
                close = result['data'].get('close', 0)
                
                # Guess what index this might be based on LTP value
                guess = ""
                if 10000 < ltp < 20000:
                    guess = "Could be Energy/Infra/FinService"
                elif ltp > 50000:
                    guess = "Could be IT/Bank"
                elif 20000 < ltp < 40000:
                    guess = "Could be Metal/Commodities"
                
                print(f"{token:<15} {ltp:>12.2f} {close:>12.2f} {guess:<30}")
        except:
            pass
        
        time.sleep(0.1)
    
    # Disconnect
    print("\n")
    obj.terminateSession(CLIENT_ID)
    print("   ✅ Disconnected from Angel One API")
    
    # Final recommendation
    print("\n" + "=" * 80)
    print("   RECOMMENDATION")
    print("=" * 80)
    print("""
If sectors are still failing, update config.py with the correct tokens
discovered above. The format is:

    "NIFTY ENERGY": ("Nifty Energy", "CORRECT_TOKEN", "NSE"),

Note: The symbol name (first parameter) must exactly match what Angel One
expects. Try variations like:
    - "Nifty Energy"
    - "NIFTY ENERGY"
    - "Nifty Energy Index"
""")


if __name__ == "__main__":
    test_sector_tokens()
