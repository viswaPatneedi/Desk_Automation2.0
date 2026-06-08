#!/usr/bin/env python3
"""
Force restart Flask app with new code
"""
import subprocess
import time
import os
import signal
import sys

WORK_DIR = "/home/viswa-pi4/Desktop/LRQA-DASHBOARD/lrqa-middleware-testing-dashboard"
os.chdir(WORK_DIR)

print("🛑 Killing any existing Python/Flask processes...")
os.system("pkill -9 -f 'python.*app.py' 2>/dev/null || true")
time.sleep(2)

print("✅ Processes killed")
print("")
print("🚀 Starting fresh Flask app...")

# Start in background with output redirection
cmd = f"""
cd {WORK_DIR}
source venv/bin/activate
python app.py > logs/app-background.log 2>&1 &
"""

result = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)

time.sleep(5)

print("✅ Flask app started")
print("📝 Log file: logs/app-background.log")
print("🌐 URL: http://10.0.0.32:11078")
print("")
print("📋 Next steps:")
print("  1. Open browser and go to http://10.0.0.32:11078")
print("  2. Press Ctrl+Shift+Delete to open clear cache dialog")
print("  3. Select 'All time' and check 'Cookies and other site data'")
print("  4. Click 'Clear data'")
print("  5. Press Ctrl+Shift+R to hard refresh the page")
print("  6. Open DevTools (F12) and check the Console tab")
