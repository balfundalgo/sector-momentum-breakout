"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    DISCOVER CORRECT SECTOR INDEX TOKENS                       ║
║              Searches Angel One instrument master for all indices             ║
║                                                                               ║
║  Run this script to find correct tokens for sectors that aren't working       ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Usage: python discover_tokens.py
"""

import pandas as pd
import sys

# Angel One instrument master URL
INSTRUMENT_MASTER_URL = 'https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json'

def discover_tokens():
    """
    Download instrument master and find all NIFTY index tokens
    """
    print("\n" + "=" * 80)
    print("   DISCOVERING NIFTY INDEX TOKENS FROM ANGEL ONE INSTRUMENT MASTER")
    print("=" * 80)
    
    print("\n📥 Downloading instrument master...")
    try:
        df = pd.read_json(INSTRUMENT_MASTER_URL)
        print(f"   ✅ Downloaded {len(df)} instruments\n")
    except Exception as e:
        print(f"   ❌ Failed to download: {e}")
        return
    
    # Filter for NSE exchange and tokens starting with 999 (indices)
    print("🔍 Filtering for NSE indices (tokens starting with 999)...\n")
    
    indices = df[
        (df['exch_seg'] == 'NSE') & 
        (df['token'].astype(str).str.startswith('999'))
    ].copy()
    
    # Sort by token for easier reading
    indices = indices.sort_values('token')
    
    print(f"Found {len(indices)} index instruments\n")
    
    # Display all indices
    print("=" * 90)
    print(f"{'Token':<15} {'Symbol':<40} {'Name':<30}")
    print("-" * 90)
    
    for _, row in indices.iterrows():
        token = str(row.get('token', ''))
        symbol = str(row.get('symbol', ''))
        name = str(row.get('name', ''))
        
        # Highlight NIFTY sectoral indices
        is_sector = any(x in symbol.upper() for x in [
            'BANK', 'IT', 'PHARMA', 'AUTO', 'METAL', 'REALTY', 'FMCG', 
            'MEDIA', 'ENERGY', 'INFRA', 'PSU', 'FIN', 'PVT', 'COMMODITIES',
            'CONSUMPTION', 'HEALTHCARE', 'OIL', 'GAS', 'MNC'
        ])
        
        marker = "⭐" if is_sector else "  "
        print(f"{marker} {token:<13} {symbol:<40} {name:<30}")
    
    print("=" * 90)
    print("\n⭐ = Likely sectoral index\n")
    
    # Now search specifically for the problematic ones
    print("\n" + "=" * 80)
    print("   SEARCHING FOR SPECIFIC PROBLEMATIC SECTORS")
    print("=" * 80)
    
    problem_sectors = ['ENERGY', 'INFRA', 'FIN SERVICE', 'FINANCIAL']
    
    for sector in problem_sectors:
        print(f"\n🔍 Searching for '{sector}'...")
        matches = indices[
            (indices['symbol'].str.upper().str.contains(sector.upper(), na=False)) |
            (indices['name'].str.upper().str.contains(sector.upper(), na=False))
        ]
        
        if len(matches) > 0:
            for _, row in matches.iterrows():
                print(f"   ✅ Found: Token={row['token']}, Symbol={row['symbol']}, Name={row.get('name', 'N/A')}")
        else:
            print(f"   ❌ No matches found for '{sector}'")
    
    # Generate Python config snippet
    print("\n\n" + "=" * 80)
    print("   RECOMMENDED SECTORAL_INDICES CONFIG")
    print("=" * 80)
    print("""
# Copy this to your config.py and verify tokens match the discovered ones above:

SECTORAL_INDICES = {
    "NIFTY BANK": ("Nifty Bank", "99926009", "NSE"),
    "NIFTY IT": ("Nifty IT", "99926013", "NSE"),
    "NIFTY PHARMA": ("Nifty Pharma", "99926014", "NSE"),
    "NIFTY AUTO": ("Nifty Auto", "99926016", "NSE"),
    "NIFTY METAL": ("Nifty Metal", "99926012", "NSE"),
    "NIFTY REALTY": ("Nifty Realty", "99926018", "NSE"),
    "NIFTY FMCG": ("Nifty FMCG", "99926011", "NSE"),
    "NIFTY MEDIA": ("Nifty Media", "99926020", "NSE"),
    "NIFTY PSU BANK": ("Nifty PSU Bank", "99926019", "NSE"),
    "NIFTY PVT BANK": ("Nifty Pvt Bank", "99926032", "NSE"),
    "NIFTY COMMODITIES": ("Nifty Commodities", "99926021", "NSE"),
    "NIFTY CONSUMPTION": ("Nifty Consumption", "99926022", "NSE"),
    "NIFTY HEALTHCARE": ("Nifty Healthcare", "99926031", "NSE"),
    "NIFTY OIL & GAS": ("Nifty Oil & Gas", "99926033", "NSE"),
    "NIFTY MNC": ("Nifty MNC", "99926023", "NSE"),
    # Update these tokens based on the discovered values above:
    "NIFTY ENERGY": ("Nifty Energy", "REPLACE_TOKEN", "NSE"),
    "NIFTY INFRA": ("Nifty Infra", "REPLACE_TOKEN", "NSE"),
    "NIFTY FIN SERVICE": ("Nifty Fin Service", "REPLACE_TOKEN", "NSE"),
}
""")


def test_tokens():
    """
    Test specific tokens to see what they return
    """
    print("\n" + "=" * 80)
    print("   TESTING SPECIFIC TOKENS")
    print("=" * 80)
    
    # Import Angel API
    try:
        from SmartApi import SmartConnect
        import pyotp
        
        # Credentials
        CLIENT_ID = 'AABY083324'
        API_KEY = 'Ce0Jc3hq'
        MPIN = '2825'
        TOTP_SECRET = 'VRIVIHGYF3KIYNWNXO7EXYCXQI'
        
        print("\n🔌 Connecting to Angel One API...")
        totp = pyotp.TOTP(TOTP_SECRET).now()
        obj = SmartConnect(api_key=API_KEY)
        data = obj.generateSession(CLIENT_ID, MPIN, totp)
        
        if not data.get('status'):
            print(f"   ❌ Connection failed: {data.get('message')}")
            return
        
        print("   ✅ Connected!\n")
        
        # Test tokens
        test_cases = [
            ("99926017", "India VIX (old ENERGY token)"),
            ("99926027", "Nifty Energy (new)"),
            ("99926015", "Old INFRA token"),
            ("99926028", "Nifty Infra (new)"),
            ("99926010", "Old FIN SERVICE token"),
            ("99926034", "Nifty Fin Service (new)"),
            ("99926026", "Nifty Serv Sector"),
        ]
        
        print(f"{'Token':<15} {'Expected':<30} {'LTP':>12} {'Status':<10}")
        print("-" * 70)
        
        for token, description in test_cases:
            try:
                result = obj.ltpData("NSE", f"Nifty {token[-2:]}", token)
                if result.get('status') and result.get('data'):
                    ltp = result['data'].get('ltp', 'N/A')
                    status = "✅ OK"
                else:
                    ltp = "N/A"
                    status = "❌ Failed"
            except Exception as e:
                ltp = "N/A"
                status = f"❌ {str(e)[:20]}"
            
            print(f"{token:<15} {description:<30} {str(ltp):>12} {status:<10}")
        
        # Disconnect
        obj.terminateSession(CLIENT_ID)
        print("\n   ✅ Disconnected")
        
    except ImportError:
        print("\n⚠️ SmartApi not installed. Run: pip install smartapi-python")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        test_tokens()
    else:
        discover_tokens()
        print("\n💡 Tip: Run with --test flag to test tokens against live API")
        print("   python discover_tokens.py --test\n")
