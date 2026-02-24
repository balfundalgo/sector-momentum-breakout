"""
Settings Manager — reads and saves all config parameters to config.py
Works both as a .py script and inside a PyInstaller EXE
"""

import os
import re
import sys

# Determine config.py path — always next to the EXE or script
if getattr(sys, 'frozen', False):
    CONFIG_PATH = os.path.join(os.path.dirname(sys.executable), 'config.py')
else:
    CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.py')


def _read_config_text():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return f.read()


def _write_config_text(text):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        f.write(text)


def _update_param(text, key, value):
    """Replace a single key = 'value' or key = value line in config text."""
    # Match quoted strings
    pattern_str = rf"^({re.escape(key)}\s*=\s*)['\"].*?['\"]"
    replacement_str = rf"\g<1>'{value}'"
    new_text, count = re.subn(pattern_str, replacement_str, text, flags=re.MULTILINE)
    if count:
        return new_text
    # Match numeric values
    pattern_num = rf"^({re.escape(key)}\s*=\s*)[\d.]+"
    replacement_num = rf"\g<1>{value}"
    new_text, count = re.subn(pattern_num, replacement_num, text, flags=re.MULTILINE)
    if count:
        return new_text
    # Match booleans
    pattern_bool = rf"^({re.escape(key)}\s*=\s*)(True|False)"
    replacement_bool = rf"\g<1>{value}"
    new_text, count = re.subn(pattern_bool, replacement_bool, text, flags=re.MULTILINE)
    return new_text


def _get_param(text, key):
    """Extract a single parameter value from config text."""
    m = re.search(rf"^{re.escape(key)}\s*=\s*['\"]?(.*?)['\"]?\s*(?:#.*)?$",
                  text, re.MULTILINE)
    return m.group(1).strip().strip("'\"") if m else ''


def save_settings(updates: dict):
    """
    Save a dict of {PARAM_NAME: value} to config.py
    Example: save_settings({'CLIENT_ID': 'ABC123', 'MPIN': '1234'})
    """
    text = _read_config_text()
    for key, value in updates.items():
        text = _update_param(text, key, value)
    _write_config_text(text)


def get_settings() -> dict:
    """Return all editable settings as a dict."""
    text = _read_config_text()
    return {
        # Credentials
        'CLIENT_ID':               _get_param(text, 'CLIENT_ID'),
        'API_KEY':                 _get_param(text, 'API_KEY'),
        'MPIN':                    _get_param(text, 'MPIN'),
        'TOTP_SECRET':             _get_param(text, 'TOTP_SECRET'),
        # Strategy
        'TREND_CANDLE_MINUTES':    _get_param(text, 'TREND_CANDLE_MINUTES'),
        'MONITORING_CANDLE_MINUTES': _get_param(text, 'MONITORING_CANDLE_MINUTES'),
        'MAX_STOCK_MOVEMENT_PCT':  _get_param(text, 'MAX_STOCK_MOVEMENT_PCT'),
        'MIN_STOCK_MOVEMENT_PCT':  _get_param(text, 'MIN_STOCK_MOVEMENT_PCT'),
        'SECOND_CANDLE_MAX_RANGE_PCT': _get_param(text, 'SECOND_CANDLE_MAX_RANGE_PCT'),
        'TRAILING_TRIGGER_PCT':    _get_param(text, 'TRAILING_TRIGGER_PCT'),
        'RISK_REWARD_RATIO':       _get_param(text, 'RISK_REWARD_RATIO'),
        # Time
        'ENTRY_CUTOFF':            _get_param(text, 'ENTRY_CUTOFF'),
        'FORCE_EXIT_TIME':         _get_param(text, 'FORCE_EXIT_TIME'),
        # Limits
        'MAX_TRADES_PER_DAY':      _get_param(text, 'MAX_TRADES_PER_DAY'),
        'LOTS_PER_TRADE':          _get_param(text, 'LOTS_PER_TRADE'),
        # Mode
        'PAPER_TRADING':           _get_param(text, 'PAPER_TRADING'),
    }


def show_settings_menu():
    """Interactive terminal menu to view and edit all settings."""
    LINE = "─" * 60

    while True:
        s = get_settings()

        print("\n" + "=" * 60)
        print("   ⚙️   SETTINGS / CONFIGURATION")
        print("=" * 60)

        print("\n  [A] API CREDENTIALS (Angel One)")
        print(f"      1. Client ID       : {s['CLIENT_ID']}")
        print(f"      2. API Key         : {s['API_KEY']}")
        print(f"      3. MPIN            : {'*' * len(s['MPIN'])}")
        print(f"      4. TOTP Secret     : {s['TOTP_SECRET'][:6]}...")

        print("\n  [B] STRATEGY PARAMETERS")
        print(f"      5. Trend Candle    : {s['TREND_CANDLE_MINUTES']} min")
        print(f"      6. Monitor Candle  : {s['MONITORING_CANDLE_MINUTES']} min")
        print(f"      7. Max Stock Move  : {s['MAX_STOCK_MOVEMENT_PCT']}%")
        print(f"      8. Min Stock Move  : {s['MIN_STOCK_MOVEMENT_PCT']}%")
        print(f"      9. Candle Range    : {s['SECOND_CANDLE_MAX_RANGE_PCT']}%")
        print(f"     10. Trailing Trig   : {s['TRAILING_TRIGGER_PCT']}%")
        print(f"     11. Risk/Reward     : 1:{s['RISK_REWARD_RATIO']}")

        print("\n  [C] TIME WINDOWS")
        print(f"     12. Entry Cutoff    : {s['ENTRY_CUTOFF']}")
        print(f"     13. Force Exit      : {s['FORCE_EXIT_TIME']}")

        print("\n  [D] POSITION LIMITS")
        print(f"     14. Max Trades/Day  : {s['MAX_TRADES_PER_DAY']}")
        print(f"     15. Lots Per Trade  : {s['LOTS_PER_TRADE']}")

        print("\n  [E] MODE")
        print(f"     16. Paper Trading   : {s['PAPER_TRADING']}")

        print(f"\n  [S] Save all & return to main menu")
        print(f"  [Q] Quit settings (no save)\n")
        print(LINE)

        choice = input("  Enter number to edit, or S/Q: ").strip().upper()

        if choice == 'Q':
            print("  Settings unchanged.")
            break

        if choice == 'S':
            print("  ✅ Settings already saved after each edit.")
            break

        field_map = {
            '1':  ('CLIENT_ID',                 'Client ID',        'str'),
            '2':  ('API_KEY',                   'API Key',          'str'),
            '3':  ('MPIN',                      'MPIN',             'str'),
            '4':  ('TOTP_SECRET',               'TOTP Secret',      'str'),
            '5':  ('TREND_CANDLE_MINUTES',      'Trend Candle (min)', 'int'),
            '6':  ('MONITORING_CANDLE_MINUTES', 'Monitor Candle (min)', 'int'),
            '7':  ('MAX_STOCK_MOVEMENT_PCT',    'Max Stock Move %',  'float'),
            '8':  ('MIN_STOCK_MOVEMENT_PCT',    'Min Stock Move %',  'float'),
            '9':  ('SECOND_CANDLE_MAX_RANGE_PCT','Candle Range %',  'float'),
            '10': ('TRAILING_TRIGGER_PCT',      'Trailing Trigger %','float'),
            '11': ('RISK_REWARD_RATIO',         'Risk/Reward Ratio', 'int'),
            '12': ('ENTRY_CUTOFF',              'Entry Cutoff (HH:MM)', 'str'),
            '13': ('FORCE_EXIT_TIME',           'Force Exit (HH:MM)',   'str'),
            '14': ('MAX_TRADES_PER_DAY',        'Max Trades/Day',    'int'),
            '15': ('LOTS_PER_TRADE',            'Lots Per Trade',    'int'),
            '16': ('PAPER_TRADING',             'Paper Trading (True/False)', 'bool'),
        }

        if choice in field_map:
            key, label, dtype = field_map[choice]
            current = s[key]
            print(f"\n  Editing: {label}")
            print(f"  Current value: {current}")
            new_val = input(f"  New value (Enter to keep): ").strip()
            if new_val:
                # Validate
                try:
                    if dtype == 'int':   int(new_val)
                    if dtype == 'float': float(new_val)
                    if dtype == 'bool':
                        if new_val not in ('True', 'False'):
                            print("  ⚠️  Must be True or False")
                            continue
                except ValueError:
                    print(f"  ⚠️  Invalid value for {dtype}")
                    continue

                save_settings({key: new_val})
                print(f"  ✅ {label} saved!")
        else:
            print("  Invalid choice, try again.")


def credentials_are_default() -> bool:
    """Return True if credentials still look like placeholder/blank values."""
    s = get_settings()
    defaults = {'YOUR_CLIENT_ID', 'YOUR_API_KEY', 'YOUR_MPIN', 'YOUR_TOTP_SECRET', '', 'ENTER_HERE'}
    return (
        s['CLIENT_ID'].upper() in defaults or
        s['API_KEY'].upper() in defaults or
        s['MPIN'].upper() in defaults or
        s['TOTP_SECRET'].upper() in defaults or
        len(s['CLIENT_ID']) < 3
    )
