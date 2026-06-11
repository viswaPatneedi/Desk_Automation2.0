#!/usr/bin/env python3
"""
Complete Flask app restart with all cache clearing
"""
import subprocess
import shutil
import sys
import os
import time
from pathlib import Path

WORK_DIR = "/home/viswa-pi4/Desktop/LRQA-DASHBOARD/lrqa-middleware-testing-dashboard"
os.chdir(WORK_DIR)

print("=" * 60)
print("COMPLETE APP RESTART WITH CACHE CLEARING")
print("=" * 60)
print()

# Step 1: Kill old processes
print("1️⃣  Killing old processes...")
os.system("pkill -9 -f 'python.*app.py' 2>/dev/null || true")
time.sleep(2)
print("   ✅ Done")
print()

# Step 2: Clear Python cache
print("2️⃣  Clearing Python cache...")
for pycache in Path(WORK_DIR).rglob("__pycache__"):
    try:
        shutil.rmtree(pycache)
    except:
        pass
for pyc in Path(WORK_DIR).rglob("*.pyc"):
    try:
        pyc.unlink()
    except:
        pass
print("   ✅ Done")
print()

# Step 3: Clear Flask template cache
print("3️⃣  Clearing Flask template cache...")
cache_dir = Path(WORK_DIR) / ".jinja2_cache"
if cache_dir.exists():
    shutil.rmtree(cache_dir)
print("   ✅ Done")
print()

# Step 4: Start app
print("4️⃣  Starting fresh Flask app...")
cmd = f"""
cd {WORK_DIR}
source venv/bin/activate
python app.py > logs/app-background.log 2>&1 &
"""
subprocess.run(["bash", "-c", cmd])
time.sleep(3)
print("   ✅ Done")
print()

print("=" * 60)
print("✅ APP RESTART COMPLETE")
print("=" * 60)
print()
print("📝 Log: logs/app-background.log")
print("🌐 URL: http://10.0.0.32:11078")
print()
print("🔧 Browser instructions:")
print("  1. Press: Ctrl+Shift+Delete")
print("  2. Select: All time AND Cookies + Site Data")
print("  3. Click: Clear data")
print("  4. Hard refresh: Ctrl+Shift+R")
print("  5. Open DevTools: F12")
print("  6. Check Console tab for errors")
