# OLLAMA-Exclusive Configuration - Quick Reference

## 🎯 Current Setup (As of August 5, 2026)

### AI Providers
- **Screen Validation**: OLLAMA LLaVA (vision) - PORT 11434
- **Sequence Generation**: OLLAMA Mistral 7B (text) - PORT 11434
- **Cloud Services**: DISABLED (Google Gemini, AWS, Azure)
- **Fallback Chain**: OLLAMA → Legacy Pixel-Based (local only)

### Critical Files
| File | Purpose | Change |
|------|---------|--------|
| `app.py` | Main Flask app | Removed genai import, added `_regenerate_steps_with_ollama()` |
| `services/unified_screen_validator.py` | Screen validation router | OLLAMA-only path, no provider selection |
| `services/ollama_integration.py` | OLLAMA integration | Added `generate_text()` method |
| `config/config_screen_validation_provider.py` | AI config | Hardcoded OLLAMA, disabled Gemini |

---

## 🚀 Quick Operations

### Start Application
```bash
cd /home/guser/Desk-automation/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard
python3 app.py
# OR with nohup (background):
nohup python3 app.py > app_startup.log 2>&1 &
```

### Check OLLAMA Status
```bash
# Is OLLAMA running?
curl -s http://localhost:11434/api/tags | python3 -m json.tool

# Check models loaded
ollama list

# Monitor performance
top -p $(pgrep ollama)
```

### Check Flask App
```bash
# Is Flask running?
curl -s http://localhost:11079/api/ollama/status | python3 -m json.tool

# Check screen validation
curl -X POST http://localhost:11079/api/ollama/verify-screen

# Check agents
curl -s http://localhost:11079/api/agents/orchestrator/status
```

### Restart Everything
```bash
# Kill app
pkill -f "python3 app.py"

# Kill OLLAMA if needed
pkill ollama

# Wait a bit
sleep 5

# Start OLLAMA first
ollama serve &

# Start Flask
cd /path/to/app && nohup python3 app.py > app_startup.log 2>&1 &

# Verify
sleep 3 && curl http://localhost:11079/api/ollama/status
```

---

## 🔧 Configuration Points

### Port Configuration
- **OLLAMA**: `http://localhost:11434` (hardcoded in `services/ollama_integration.py`)
- **Flask**: `http://localhost:11079` (configured in `app.py`)

### Model Configuration
- **Mistral 7B**: Used for text generation (sequence building)
- **LLaVA**: Used for screen validation (vision analysis)
- **Fallback**: Legacy pixel-based (local, no AI needed)

### No Longer Used
```python
# These are IGNORED now:
os.environ.get('GOOGLE_API_KEY')           # Not used
os.environ.get('SCREEN_VALIDATION_PROVIDER')  # Hardcoded to 'ollama'
os.environ.get('GEMINI_API_KEY')           # Not used
```

---

## 📊 Performance Baseline

**Hardware:**
- CPU: Intel Core i7-6700 (8 cores @ 3.4GHz)
- RAM: 15GB (11GB available for inference)
- Storage: SSD

**Typical Latencies:**
- Screen Validation: 3-8 seconds (LLaVA)
- Sequence Generation: 2-5 seconds (Mistral 7B)
- API Response: <1 second (Flask overhead)

**Resource Usage:**
- OLLAMA at rest: 50-100MB
- OLLAMA during inference: 2-4GB
- Flask app: 150-300MB
- Full system during inference: 2.5-4.5GB (well under 11GB limit)

---

## 🧪 Testing Checklist

### Pre-Deployment
- [ ] OLLAMA running: `curl http://localhost:11434/api/tags`
- [ ] Models loaded: `ollama list` shows mistral and llava
- [ ] Flask starts: `python3 app.py` runs without errors
- [ ] Flask responds: `curl http://localhost:11079/api/health`

### Post-Deployment
- [ ] OLLAMA status: `curl http://localhost:11079/api/ollama/status`
- [ ] Screen validation: POST to `/api/ollama/verify-screen`
- [ ] Agents active: `curl http://localhost:11079/api/agents/orchestrator/status`
- [ ] Sequence generation: POST to `/api/ai/sequences/generate`
- [ ] No errors: `grep ERROR app_startup.log`
- [ ] No cloud calls: `grep "http://\|https://" app.log` (should be empty)

### Execution Test
- [ ] Run test execution
- [ ] Verify screen validation happens (3-8 sec latency)
- [ ] Check logs for "OLLAMA" mentions
- [ ] Confirm no "google" or "cloud" keywords

---

## 🛑 Emergency Procedures

### OLLAMA Crash
```bash
# Restart OLLAMA
pkill ollama
sleep 2
ollama serve &

# Check models
sleep 5 && ollama list

# Reload Flask (to reconnect)
pkill -f "python3 app.py"
sleep 2
python3 app.py &
```

### Flask Crash
```bash
# Restart Flask
pkill -f "python3 app.py"
sleep 2
python3 app.py &

# Verify
sleep 3 && curl http://localhost:11079/api/ollama/status
```

### Both Down
```bash
# Full restart sequence
pkill ollama
pkill -f "python3 app.py"
sleep 5

# Start OLLAMA first
nohup ollama serve > /tmp/ollama.log 2>&1 &
sleep 10

# Start Flask
cd /path/to/app
nohup python3 app.py > app_startup.log 2>&1 &
sleep 5

# Verify both
echo "OLLAMA:" && curl -s http://localhost:11434/api/tags | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"Models: {len(d['models'])}\")"
echo "Flask:" && curl -s http://localhost:11079/api/ollama/status | python3 -c "import sys, json; d=json.load(sys.stdin); print(d['status'])"
```

### Clear / Reset Everything
```bash
# Stop services
pkill ollama
pkill -f "python3 app.py"

# Reset OLLAMA (WARNING: deletes models!)
rm -rf ~/.ollama

# Restart OLLAMA
ollama serve &
sleep 10

# Download models again
ollama pull mistral
ollama pull llava

# Restart Flask
python3 app.py &
```

---

## 📋 Dependency Check

### Required Services Must Be Running
```bash
# Check if OLLAMA running
ps aux | grep "ollama serve" | grep -v grep

# Check if Flask running
ps aux | grep "python3 app.py" | grep -v grep

# Check ports available
netstat -tuln | grep -E "11079|11434"
```

### Zero Cloud Dependencies
These should be EMPTY or NON-EXISTENT:
```bash
echo $GOOGLE_API_KEY          # Should be empty
echo $GEMINI_API_KEY          # Should be empty
env | grep -i google          # Should return nothing
env | grep -i aws             # Should return nothing
env | grep -i azure           # Should return nothing
```

---

## 🔍 Debug Commands

### See Flask Startup Output
```bash
tail -100 app_startup.log | grep -E "OLLAMA|AI|Screen|Agent|Error"
```

### See OLLAMA Inference Logs
```bash
# While inference is running:
watch -n 1 'curl -s http://localhost:11434/api/tags | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))"'

# Or check OpenAI-compatible endpoint
curl -X POST http://localhost:11434/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral",
    "messages": [{"role": "user", "content": "test"}],
    "stream": false
  }' | python3 -m json.tool
```

### Monitor Resource Usage During Inference
```bash
# Terminal 1: Start inference
curl -X POST http://localhost:11079/api/ollama/verify-screen \
  -H "Content-Type: application/json" \
  -d '{"image_path": "/path/to/screenshot.png"}'

# Terminal 2: Watch resources
watch -n 1 'ps aux | grep -E "ollama|python3" | grep -v grep | awk "{print \$1, \$3, \$4, \$11}"'
```

### Check Network Calls
```bash
# Monitor network while running test
sudo tcpdump -i lo -n "dst port 11434 or dst port 11079" 2>/dev/null &

# Run test
# ...

# Kill tcpdump
pkill tcpdump

# Verify NO external networks (except localhost)
netstat -an | grep ESTABLISHED | grep -v localhost
```

---

## 📚 File Locations

| Item | Path |
|------|------|
| Flask App | `/home/guser/Desk-automation/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard/app.py` |
| OLLAMA Config | `services/ollama_integration.py` |
| Screen Validator | `services/unified_screen_validator.py` |
| AI Config | `config/config_screen_validation_provider.py` |
| Startup Log | `/home/guser/Desk-automation/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard/app_startup.log` |
| Execution Storage | `/home/guser/Desk-automation/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard/ExecutionResults/` |
| OLLAMA Models | `~/.ollama/models` |

---

## ✅ Status Endpoints

All endpoints ready for monitoring:

```bash
# OLLAMA Status
curl http://localhost:11079/api/ollama/status

# OLLAMA Models
curl http://localhost:11079/api/ollama/models

# Orchestrator Status
curl http://localhost:11079/api/agents/orchestrator/status

# Health Check
curl http://localhost:11079/api/health
```

---

## 🎓 Key Concepts

### Why OLLAMA-Only?
1. **Data Privacy**: No screenshots sent to cloud
2. **Cost**: No API charges
3. **Reliability**: No internet dependency
4. **Speed**: No round-trip latency (marginal)
5. **Compliance**: No third-party data sharing
6. **Control**: All models run locally

### Models Being Used
- **Mistral 7B**: 4.4GB, runs in 2-5 seconds, powerful text generation
- **LLaVA**: 4.7GB, runs in 3-8 seconds, understands screenshots

### What Happens If OLLAMA Dies?
- ✅ Application still runs
- ⚠️ Screen validation falls back to legacy pixel-based
- ⚠️ Sequence generation fails (returns empty)
- → Restart OLLAMA to restore full AI capabilities

---

**Last Updated:** August 5, 2026  
**Status:** Production Ready  
**Maintainer:** DevOps Team  
**Emergency Contact:** See DEPLOYMENT_CHECKLIST.txt
