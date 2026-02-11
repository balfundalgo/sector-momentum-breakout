# 🚀 Quick Reference Card - Git & Build Commands

## Mac Terminal - Git Commands

```bash
# ═══════════════════════════════════════════════════════════════
# INITIAL SETUP (One-time)
# ═══════════════════════════════════════════════════════════════

# Configure git
git config --global user.name "Your Name"
git config --global user.email "your@email.com"

# Initialize repo
cd /path/to/sector_momentum
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/USERNAME/sector-momentum-strategy.git
git push -u origin main


# ═══════════════════════════════════════════════════════════════
# DAILY GIT WORKFLOW
# ═══════════════════════════════════════════════════════════════

# Check status
git status

# Add and commit
git add .
git commit -m "Your message"

# Push to GitHub
git push origin main


# ═══════════════════════════════════════════════════════════════
# FORCE PUSH COMMANDS (⚠️ USE WITH CAUTION!)
# ═══════════════════════════════════════════════════════════════

# Force push - overwrites remote completely
git push --force origin main

# Safer force push (fails if remote has new commits you don't have)
git push --force-with-lease origin main

# When you're 100% sure local should replace remote:
git push -f origin main


# ═══════════════════════════════════════════════════════════════
# UNDO / RESET COMMANDS
# ═══════════════════════════════════════════════════════════════

# Undo last commit, keep changes
git reset --soft HEAD~1

# Undo last commit, discard changes (DANGEROUS!)
git reset --hard HEAD~1

# Discard all local changes
git checkout -- .

# Match remote exactly
git fetch origin
git reset --hard origin/main


# ═══════════════════════════════════════════════════════════════
# CREATE A NEW VERSION TAG
# ═══════════════════════════════════════════════════════════════

git tag v1.0.0
git push origin v1.0.0

# This triggers GitHub Actions to build EXE and Mac app!
```

## Windows PowerShell - Build EXE

```powershell
# ═══════════════════════════════════════════════════════════════
# SETUP (One-time)
# ═══════════════════════════════════════════════════════════════

# Install Python from python.org (check "Add to PATH")

# Install dependencies
pip install -r requirements.txt
pip install pyinstaller


# ═══════════════════════════════════════════════════════════════
# BUILD WINDOWS EXE
# ═══════════════════════════════════════════════════════════════

# Simple build
pyinstaller --onefile --console --name SectorMomentumStrategy main.py

# Full build with hidden imports
pyinstaller --onefile --console --name SectorMomentumStrategy `
    --hidden-import=smartapi `
    --hidden-import=SmartApi `
    --hidden-import=SmartApi.smartWebSocketV2 `
    --hidden-import=pyotp `
    --hidden-import=websocket `
    --add-data "config.py;." `
    main.py

# Using spec file (recommended)
pyinstaller sector_momentum.spec

# EXE location:
# dist\SectorMomentumStrategy.exe
```

## Mac Terminal - Build App

```bash
# ═══════════════════════════════════════════════════════════════
# BUILD MAC EXECUTABLE
# ═══════════════════════════════════════════════════════════════

# Install dependencies
pip install -r requirements.txt
pip install pyinstaller

# Simple build
pyinstaller --onefile --console --name SectorMomentumStrategy main.py

# Full build
pyinstaller --onefile --console --name SectorMomentumStrategy \
    --hidden-import=smartapi \
    --hidden-import=SmartApi \
    --hidden-import=SmartApi.smartWebSocketV2 \
    --hidden-import=pyotp \
    --hidden-import=websocket \
    --add-data "config.py:." \
    main.py

# Using spec file
pyinstaller sector_momentum.spec

# Executable location:
# dist/SectorMomentumStrategy

# Make executable
chmod +x dist/SectorMomentumStrategy

# Run
./dist/SectorMomentumStrategy
```

## GitHub Actions - Automatic Build

```bash
# Trigger build by creating a version tag:
git tag v1.0.0
git push origin v1.0.0

# Go to GitHub → Actions → See build progress
# Download from Releases when complete
```

## Common Issues & Fixes

```bash
# Issue: "Permission denied" when pushing
git remote set-url origin https://USERNAME:TOKEN@github.com/USERNAME/repo.git

# Issue: "fatal: not a git repository"
git init

# Issue: "remote origin already exists"
git remote remove origin
git remote add origin https://github.com/USERNAME/repo.git

# Issue: Merge conflicts when pulling
git stash
git pull
git stash pop

# Issue: Need to completely restart
rm -rf .git
git init
git add .
git commit -m "Fresh start"
git remote add origin https://github.com/USERNAME/repo.git
git push -u --force origin main
```
