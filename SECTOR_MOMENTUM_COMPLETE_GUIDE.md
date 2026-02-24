# Sector Momentum Breakout Strategy - Complete Setup Guide

## 📋 Project Overview

This is a sophisticated **Sector Momentum Breakout Strategy** for Indian markets using Angel One SmartAPI. 

### Strategy Flow:
1. **Trend Identification** (9:15-9:25): Analyze first 10-minute NIFTY 50 candle
2. **Sector Selection**: Best sector for bullish / Worst sector for bearish
3. **Stock Selection**: Find best stock in sector (movement ≤ 3%)
4. **Entry Monitoring**: Wait for 2 consecutive candles above PDH (bullish) or below PDL (bearish)
5. **Order Execution**: BUY PE + BUY FUTURE (bullish) or BUY CE + SHORT FUTURE (bearish)
6. **Position Monitoring**: SL (candle low), TP (2x SL), Trailing (0.5% → BE)
7. **Force Exit**: 3:15 PM

### Project Structure:
```
sector_momentum/
├── main.py                  # Main entry point
├── config.py                # Configuration and credentials
├── angel_api.py             # Angel One API wrapper with WebSocket
├── api_rate_limiter.py      # Endpoint-aware rate limiting
├── websocket_manager.py     # Real-time LTP via WebSocket
├── data_fetcher.py          # Historical data and candles
├── trend_identifier.py      # First 10-min candle analysis
├── sector_scanner.py        # Sector performance ranking
├── stock_selector.py        # Stock selection within sector
├── entry_monitor.py         # PDH/PDL breakout monitoring
├── order_executor.py        # Option + Future order placement
├── position_monitor.py      # SL/TP/Trailing stop management
├── logger.py                # Logging and trade records
├── candle_builder.py        # Hybrid OHLC builder
├── __init__.py              # Package initialization
├── discover_tokens.py       # Utility: Find sector tokens
├── find_sector_tokens.py    # Utility: Search tokens
├── test_sector_tokens.py    # Utility: Test tokens live
└── fetch_sector_constituents.py  # Utility: Fetch sector stocks
```

---

## 🖥️ Part 1: GitHub Repository Setup (Complete from Scratch)

### Step 1: Install Git (if not installed)

**Mac:**
```bash
# Check if git is installed
git --version

# If not installed, install via Homebrew
brew install git
```

**Windows:**
- Download from: https://git-scm.com/download/win
- Run installer with default settings

### Step 2: Configure Git (One-time setup)

```bash
# Set your name and email
git config --global user.name "Navneet"
git config --global user.email "your-email@example.com"

# Verify configuration
git config --list
```

### Step 3: Create GitHub Account and Repository

1. Go to https://github.com and create an account (if you don't have one)
2. Click the **"+"** icon (top right) → **"New repository"**
3. Fill in:
   - **Repository name**: `sector-momentum-strategy`
   - **Description**: `Sector Momentum Breakout Strategy for Indian Markets`
   - **Visibility**: Private (recommended for trading code)
   - **DO NOT** check "Add a README file" (we'll add our own)
4. Click **"Create repository"**

### Step 4: Initialize Local Repository

```bash
# Navigate to your project folder
cd /path/to/your/sector_momentum

# Initialize git repository
git init

# Add all files
git add .

# Create first commit
git commit -m "Initial commit: Sector Momentum Breakout Strategy"

# Add remote origin (replace with YOUR repository URL)
git remote add origin https://github.com/YOUR_USERNAME/sector-momentum-strategy.git

# Push to GitHub
git push -u origin main
```

### Step 5: Create .gitignore file

Create a `.gitignore` file to exclude sensitive and unnecessary files:

```bash
# Create .gitignore
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
ENV/
env/
.venv/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Logs and cache
logs/
*.log
sector_constituents_cache.json

# Credentials (IMPORTANT!)
# config.py  # Uncomment if you don't want to push credentials

# OS files
.DS_Store
Thumbs.db

# Distribution
*.exe
*.dmg
*.app
SectorMomentum-*.zip
EOF
```

---

## 🔄 Part 2: Git Commands Cheat Sheet

### Daily Workflow Commands

```bash
# Check status of changes
git status

# Add specific file
git add filename.py

# Add all changes
git add .

# Commit with message
git commit -m "Your descriptive message"

# Push to GitHub
git push

# Pull latest from GitHub
git pull
```

### Force Push Commands (USE WITH CAUTION!)

```bash
# Force push - overwrites remote history
git push --force

# Force push with lease (safer - fails if remote has new commits)
git push --force-with-lease

# Force push specific branch
git push origin main --force

# If you need to completely overwrite remote:
git push origin main --force
```

### Undo/Reset Commands

```bash
# Undo last commit but keep changes
git reset --soft HEAD~1

# Undo last commit and discard changes
git reset --hard HEAD~1

# Discard all local changes
git checkout -- .

# Reset to match remote exactly
git fetch origin
git reset --hard origin/main
```

### Branch Commands

```bash
# Create new branch
git checkout -b new-feature

# Switch to branch
git checkout main

# List branches
git branch -a

# Merge branch into main
git checkout main
git merge new-feature

# Delete branch
git branch -d new-feature
```

---

## 📦 Part 3: Creating Windows EXE Files

### Prerequisites for Windows EXE

Create a `requirements.txt`:

```txt
smartapi-python>=1.4.0
pyotp>=2.8.0
pandas>=2.0.0
requests>=2.28.0
websocket-client>=1.5.0
pyinstaller>=6.0.0
```

### Method 1: Using PyInstaller (Recommended)

#### Option A: Build on Windows (Best Results)

1. **Install Python on Windows** (3.10 or 3.11 recommended)
   - Download from python.org
   - Check "Add Python to PATH" during installation

2. **Install dependencies:**
```powershell
# Open Command Prompt or PowerShell
pip install -r requirements.txt
pip install pyinstaller
```

3. **Create spec file** (`sector_momentum.spec`):

```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.py', '.'),
        ('sector_constituents_cache.json', '.') if os.path.exists('sector_constituents_cache.json') else None,
    ],
    hiddenimports=[
        'smartapi',
        'SmartApi',
        'SmartApi.smartWebSocketV2',
        'pyotp',
        'pandas',
        'requests',
        'websocket',
        'websocket._abnf',
        'websocket._app',
        'websocket._core',
        'websocket._exceptions',
        'websocket._handshake',
        'websocket._http',
        'websocket._logging',
        'websocket._socket',
        'websocket._ssl_compat',
        'websocket._url',
        'websocket._utils',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Filter out None entries from datas
a.datas = [d for d in a.datas if d is not None]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SectorMomentumStrategy',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Keep True for trading app (shows logs)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path if you have one: icon='app.ico'
)
```

4. **Build the EXE:**
```powershell
pyinstaller sector_momentum.spec
```

5. **Find your EXE in:** `dist/SectorMomentumStrategy.exe`

#### Option B: Simple one-liner build

```powershell
# Simple build (may need adjustments)
pyinstaller --onefile --console --name SectorMomentumStrategy main.py

# With hidden imports
pyinstaller --onefile --console --name SectorMomentumStrategy ^
    --hidden-import=smartapi ^
    --hidden-import=SmartApi ^
    --hidden-import=SmartApi.smartWebSocketV2 ^
    --hidden-import=pyotp ^
    --hidden-import=websocket ^
    main.py
```

### Method 2: Using GitHub Actions (Cross-Platform Build)

Create `.github/workflows/build-exe.yml`:

```yaml
name: Build Windows EXE

on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:  # Allows manual trigger

jobs:
  build-windows:
    runs-on: windows-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install smartapi-python pyotp pandas requests websocket-client pyinstaller
    
    - name: Build EXE
      run: |
        pyinstaller --onefile --console --name SectorMomentumStrategy `
          --hidden-import=smartapi `
          --hidden-import=SmartApi `
          --hidden-import=SmartApi.smartWebSocketV2 `
          --hidden-import=pyotp `
          --hidden-import=websocket `
          main.py
    
    - name: Upload artifact
      uses: actions/upload-artifact@v4
      with:
        name: SectorMomentumStrategy-Windows
        path: dist/SectorMomentumStrategy.exe

  build-mac:
    runs-on: macos-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install smartapi-python pyotp pandas requests websocket-client pyinstaller
    
    - name: Build App
      run: |
        pyinstaller --onefile --console --name SectorMomentumStrategy \
          --hidden-import=smartapi \
          --hidden-import=SmartApi \
          --hidden-import=SmartApi.smartWebSocketV2 \
          --hidden-import=pyotp \
          --hidden-import=websocket \
          main.py
    
    - name: Upload artifact
      uses: actions/upload-artifact@v4
      with:
        name: SectorMomentumStrategy-Mac
        path: dist/SectorMomentumStrategy
```

### Triggering the Build

```bash
# Create a version tag
git tag v1.0.0
git push origin v1.0.0

# Or manually trigger from GitHub:
# Go to Actions → Build Windows EXE → Run workflow
```

---

## 🍎 Part 4: Creating Mac App Bundle

### Simple Mac Build

```bash
# Install PyInstaller
pip install pyinstaller

# Build Mac executable
pyinstaller --onefile --console --name SectorMomentumStrategy \
    --hidden-import=smartapi \
    --hidden-import=SmartApi \
    --hidden-import=SmartApi.smartWebSocketV2 \
    --hidden-import=pyotp \
    --hidden-import=websocket \
    main.py

# The executable will be in dist/SectorMomentumStrategy
```

### Creating .app Bundle (Optional)

For a proper Mac app with icon:

```bash
pyinstaller --onefile --windowed --name SectorMomentumStrategy \
    --icon=app.icns \
    --hidden-import=smartapi \
    --hidden-import=SmartApi \
    main.py
```

---

## 📝 Part 5: Complete Project Files

### Create requirements.txt

```txt
# Core dependencies
smartapi-python>=1.4.0
pyotp>=2.8.0
pandas>=2.0.0
requests>=2.28.0
websocket-client>=1.5.0

# Optional: For building executables
pyinstaller>=6.0.0
```

### Create README.md

```markdown
# Sector Momentum Breakout Strategy

Automated trading strategy for Indian F&O markets using Angel One API.

## Features

- 🎯 Trend identification from NIFTY 50 first candle
- 📊 Real-time sector scanning and ranking
- 📈 Stock selection based on movement criteria
- 🔔 PDH/PDL breakout detection
- 💹 Option + Future order execution
- 🛡️ Trailing stop and risk management
- 📝 Comprehensive logging

## Requirements

- Python 3.10+
- Angel One trading account with API access

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Paper trading (default)
python main.py

# Live trading
python main.py --live

# Force trend direction
python main.py --trend BULLISH

# Test sector scanning
python main.py --test-sectors
```

## Configuration

Edit `config.py` to set:
- API credentials
- Trading parameters
- Risk settings

## Disclaimer

This software is for educational purposes only. Trading involves risk.
```

---

## 🔧 Part 6: Quick Reference Commands

### Mac Terminal - Git Force Push

```bash
# Navigate to project
cd /path/to/sector_momentum

# Check status
git status

# Add all changes
git add .

# Commit
git commit -m "Your message"

# Normal push
git push origin main

# FORCE PUSH (overwrites remote)
git push --force origin main

# Safer force push
git push --force-with-lease origin main

# If remote is ahead and you want to overwrite:
git push --force origin main
```

### Windows PowerShell - Build EXE

```powershell
# Navigate to project
cd C:\path\to\sector_momentum

# Install requirements
pip install -r requirements.txt
pip install pyinstaller

# Build EXE
pyinstaller --onefile --console --name SectorMomentumStrategy main.py

# Find EXE
dir dist\
```

---

## ⚠️ Important Notes

### Security Considerations

1. **Never commit credentials to public repos**
   - Consider using environment variables for API keys
   - Add `config.py` to `.gitignore` for public repos

2. **For EXE distribution:**
   - Credentials are embedded in the EXE
   - Only distribute to trusted users

### Testing Before Live Trading

1. Always test with `PAPER_TRADING = True` in config.py
2. Run during market hours to verify all API calls work
3. Check logs for any rate limiting errors

### Common Issues

1. **AB1004 Rate Limit Error:**
   - The code has built-in rate limiting
   - If still occurring, increase delays in `api_rate_limiter.py`

2. **WebSocket Connection Failed:**
   - Code falls back to REST API automatically
   - Check network connectivity

3. **Token Not Found:**
   - Run `python discover_tokens.py` to find correct tokens
   - Update `config.py` with verified tokens
