#!/usr/bin/env python3
"""Quick restart with cache clearing"""
import subprocess
import os
import time
import shutil
from pathlib import Path

WORK_DIR = "/home/viswa-pi4/Desktop/LRQA-DASHBOARD/lrqa-middleware-testing-dashboard"
os.chdir(WORK_DIR)

# Kill old processes
print("🛑 Stopping old app processes...")
os.system("pkill -9 -f 'python.*app.py' 2>/dev/null || true")
time.sleep(1)

# Clear cache directories
print("🧹 Clearing cache...")
for pycache in Path(WORK_DIR).rglob("__pycache__"):
    shutil.rmtree(pycache, ignore_errors=True)

# Start app
print("🚀 Starting app in venv...")
cmd = "source venv/bin/activate && nohup python app.py > logs/app-background.log 2>&1 &"
subprocess.Popen(["bash", "-c", cmd], cwd=WORK_DIR)

time.sleep(3)
print("✅ App started!")
print("📝 Log: logs/app-background.log")
print("🌐 URL: http://10.0.0.32:11078")
