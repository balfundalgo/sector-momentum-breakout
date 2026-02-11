"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    FIND CORRECT SECTOR INDEX TOKENS                           ║
║              Searches instrument master for all NIFTY indices                 ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Run this script to discover correct tokens for all sectoral indices.
"""

import pandas as pd
import sys

# Angel One instrument master URL
INSTRUMENT_MASTER_URL = 'https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json'

def find_sector_tokens():
    print("\n📥 Downloading instrument master...")
    df = pd.read_json(INSTRUMENT_MASTER_URL)
    print(f"   ✅ Downloaded {len(df)} instruments\n")
    
    # Filter for NSE indices (tokens starting with 999)
    print("🔍 Searching for NIFTY sectoral indices...\n")
    
    # Find all indices
    indices = df[
        (df['exch_seg'] == 'NSE') & 
        (df['token'].astype(str).str.startswith('999'))
    ].copy()
    
    print(f"Found {len(indices)} index instruments\n")
    
    # Search for specific sector-related indices
    search_terms = [
        'NIFTY BANK', 'NIFTY IT', 'NIFTY PHARMA', 'NIFTY AUTO', 
        'NIFTY METAL', 'NIFTY REALTY', 'NIFTY FMCG', 'NIFTY MEDIA',
        'NIFTY ENERGY', 'NIFTY INFRA', 'NIFTY PSU', 'NIFTY FIN',
        'NIFTY PVT', 'NIFTY COMMODITIES', 'NIFTY CONSUMPTION',
        'NIFTY HEALTHCARE', 'NIFTY OIL', 'NIFTY MNC', 'NIFTY FINANCIAL'
    ]
    
    print("=" * 80)
    print(f"{'Symbol':<40} {'Token':<15} {'Name':<25}")
    print("-" * 80)
    
    found_indices = {}
    
    for _, row in indices.iterrows():
        symbol = str(row.get('symbol', '')).upper()
        name = str(row.get('name', '')).upper()
        token = str(row.get('token', ''))
        
        # Check if it matches any of our search terms
        for term in search_terms:
            if term.upper() in symbol or term.upper() in name:
                print(f"{row['symbol']:<40} {token:<15} {row.get('name', 'N/A'):<25}")
                found_indices[symbol] = {
                    'symbol': row['symbol'],
                    'token': token,
                    'name': row.get('name', '')
                }
                break
    
    print("=" * 80)
    
    # Now let's specifically look for the problematic ones
    print("\n\n🔍 Searching specifically for ENERGY, INFRA, FINANCIAL SERVICES...\n")
    
    problem_search = ['ENERGY', 'INFRA', 'FINANCIAL', 'FIN SERVICE']
    
    for _, row in indices.iterrows():
        symbol = str(row.get('symbol', '')).upper()
        name = str(row.get('name', '')).upper()
        
        for term in problem_search:
            if term in symbol or term in name:
                print(f"Symbol: {row['symbol']:<35} Token: {row['token']:<12} Name: {row.get('name', 'N/A')}")
    
    # Generate the corrected config
    print("\n\n" + "=" * 80)
    print("📋 CORRECTED SECTORAL_INDICES FOR config.py:")
    print("=" * 80)
    print("""
# Copy this to your config.py file:

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
    # Below are the ones that need correct tokens - check output above
}
""")


if __name__ == "__main__":
    find_sector_tokens()
