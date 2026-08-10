# Quick Troubleshooting Guide - Screenshots & AI Validation

## ❌ Problem: Screenshots still showing 404

### Check List:
1. **Verify Flask restarted:**
   ```bash
   ps aux | grep "python.*app.py"
   ```
   Should show running process with PID

2. **Verify ExecutionResults folder exists:**
   ```bash
   ls -la ExecutionResults/
   ```

3. **Test screenshot endpoint:**
   ```bash
   curl -I "http://localhost:11079/screenshots/10.0.0.28_DT_LAB_XIONE-UK-17-97_Iteration-1_Before-Reboot_20260807_020203.png"
   ```
   Should return: `HTTP/1.1 200 OK` (not 404)

4. **Check Flask logs:**
   ```bash
   tail -50 app.log | grep screenshot
   ```

---

## ❌ Problem: AI Validation not showing in logs

### Check List:
1. **Verify OLLAMA running:**
   ```bash
   curl http://localhost:11434/api/tags
   ```
   Should return JSON with models list

2. **Start OLLAMA if needed:**
   ```bash
   ollama serve &
   ```

3. **Check available models:**
   ```bash
   ollama list
   ```
   Should show at least `mistral:latest`

4. **Check if validation is actually being called:**
   - Look in execution logs for: `🔍 Performing AI-based screen validation`
   - If not present → AI validation may be disabled or skipped
   - This is OK - execution still works without it

---

## ✅ Expected Output

### Screenshots Displaying:
- JOBs page shows "Captured Screens" section with thumbnails
- No 404 errors in browser console
- Image loads successfully

### AI Validation Working:
- Execution logs show:
  ```
  🔍 Performing AI-based screen validation (provider: auto-detected)
     Using provider: ollama
  ✓ Screen detected: HomeScreen (95.23%)
  ```

---

## 🔧 Flask Restart

**If screenshots still 404 after changes:**
```bash
cd /home/guser/Desk-automation/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard
pkill -9 -f "python.*app.py"
sleep 2
source venv/bin/activate
nohup python app.py > app.log 2>&1 &
sleep 5
ps aux | grep "python.*app.py" | grep -v grep
```

---

## 📊 Status Commands

**Check OLLAMA:**
```bash
# Is it running?
curl -s http://localhost:11434/api/tags | head -5

# Does it have models?
ollama list

# Try a simple request (takes 5-10s):
curl -X POST http://localhost:11434/api/generate \
  -d '{"model":"mistral:latest","prompt":"hello","stream":false}' | jq '.response' | head -c 100
```

**Check Flask:**
```bash
# Is it running?
ps aux | grep "python.*app.py"

# Recent logs:
tail -100 app.log | grep -i screenshot

# Full logs:
tail -200 app.log
```

---

## 📝 Execution Log Checklist

### ✅ All Good:
```
[STEP 1.5] Capturing BEFORE screenshot
   ✓ BEFORE screenshot captured successfully
   ✓ File: 10.0.0.28_DT_LAB_..._Before-Reboot_20260807_020203.png

[STEP 7] Capturing AFTER screenshot  
   ✓ AFTER screenshot captured successfully
   ✓ Screen detected: HomeScreen (98.50%)

[CAPTURED SCREENS]
   Before: /path/to/Before-Reboot_20260807_020203.png ✅
   After: /path/to/After-Reboot_20260807_041610.png ✅
```

### ⚠️ Expected Warning (AI unavailable):
```
🔍 Performing AI-based screen validation
   ⚠ AI Screen Validation not available - using legacy validation
   → Execution continues (validation is informational)
```

### ❌ Error (Should NOT see):
```
[ERROR] Screenshot capture failed
❌ AFTER screenshot not captured
Failed to load resource: 404 NOT FOUND
```

---

## Performance Impact

- **Screenshot serving:** < 5ms (local file read)
- **AI validation:** 2-5 seconds (first request to OLLAMA)
- **AI validation cache:** ~0.1 seconds (cached results)
- **Total execution time:** Same as before (validation is parallel)

---

## Backward Compatibility

- ✅ Old screenshots still work (`~/screenshots`, reference_screens)
- ✅ No database changes required
- ✅ No configuration changes needed
- ✅ Existing feature flags still work
- ✅ Safe to rollback (just one file change)

---

## Support

If problems persist:
1. Share execution ID
2. Share relevant logs (from execution and `app.log`)
3. Run: `curl http://localhost:11434/api/tags` and share output
4. Run: `ps aux | grep -E "python|ollama"` and share output

