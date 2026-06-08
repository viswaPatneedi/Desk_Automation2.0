# XUMO Activation Browser Setup Guide

## Problem Overview
The XUMO activation feature requires Selenium WebDriver with a compatible browser. However, different platforms (ARM64 vs x86_64) require different browser and driver configurations.

## Current Status
- **Platform**: Raspberry Pi (ARM64/aarch64)
- **Issue**: Standard browser automation doesn't work out-of-box on ARM
- **Options**: Firefox (snap version has geckodriver issues), Chrome (not available for ARM64)

---

## Solution Options

### Option 1: Run Selenium on Separate x86_64 Machine (RECOMMENDED for Production)

**Setup:**
1. Keep code fetching on Raspberry Pi (via SSH to device)
2. Send activation code to a separate x86_64 server/container
3. Run Selenium automation there with full Chrome support

**Implementation:**
```python
# On RPi: Fetch code + Send to activation server
activation_code = fetch_xumo_activation_code(device_ip)
requests.post('http://activation-server:5000/activate', 
              json={'code': activation_code})

# On x86_64 server: Run Selenium
@app.route('/activate', methods=['POST'])
def activate():
    code = request.json['code']
    result = run_selenium_activation(code)
    return jsonify(result)
```

**Advantages:**
- ✅ Works reliably with standard Chrome/ChromeDriver
- ✅ No ARM compatibility issues
- ✅ Better for cloud migration
- ✅ Separates concerns (RPi = device management, Server = browser automation)

---

### Option 2: Use Playwright (Better ARM Support)

**Install:**
```bash
pip install playwright
playwright install firefox
```

**Update auto_activate_xumo.py:**
```python
from playwright.sync_api import sync_playwright

def activate_xumo_device(device_ip=None, activation_code=None):
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False)
        page = browser.new_page()
        page.goto(ACTIVATION_URL)
        # ... rest of automation
```

**Advantages:**
- ✅ Better ARM64 support
- ✅ Simpler API than Selenium
- ✅ Built-in browser downloads

**Disadvantages:**
- ⚠️ Requires rewriting automation logic
- ⚠️ Larger dependency (downloads full browser)

---

### Option 3: Docker Container with x86_64 Emulation

**Setup:**
```bash
# Install QEMU for x86 emulation
sudo apt install qemu-user-static

# Run Chrome container
docker run --platform linux/amd64 \
  -p 4444:4444 \
  selenium/standalone-chrome:latest
```

**Connect from Python:**
```python
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

driver = webdriver.Remote(
    command_executor='http://localhost:4444/wd/hub',
    desired_capabilities=DesiredCapabilities.CHROME
)
```

**Advantages:**
- ✅ Uses standard Selenium code
- ✅ Chrome support on ARM
- ✅ Isolated environment

**Disadvantages:**
- ⚠️ Performance overhead from emulation
- ⚠️ Requires Docker

---

### Option 4: Chromium with Manual ChromeDriver (Current ARM Workaround)

**Install Chromium:**
```bash
# Chromium might be available from snap
sudo snap install chromium

# Or build from source (very slow)
```

**Download ARM ChromeDriver:**
```bash
# No official ARM builds, would need third-party or build from source
```

**Status:** ❌ Not recommended - ChromeDriver ARM support is limited

---

## Recommended Implementation Path

### For Current RPi Setup:
**Use Option 2 (Playwright)** - Best immediate solution for ARM

### For Cloud Migration:
**Use Option 1 (Separate Activation Service)** - Most scalable architecture

### Hybrid Approach (BEST):
1. Create activation microservice with Playwright (works on both ARM and x86_64)
2. Deploy as Docker container
3. RPi calls this service via HTTP API
4. Easy to migrate to cloud later

---

## Implementation: Activation Microservice

### Service Code (activation_service.py):
```python
from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
import os

app = Flask(__name__)

@app.route('/activate', methods=['POST'])
def activate():
    data = request.json
    code = data.get('activation_code')
    username = data.get('username', os.getenv('XUMO_USERNAME'))
    password = data.get('password', os.getenv('XUMO_PASSWORD'))
    
    try:
        result = run_activation(code, username, password)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def run_activation(code, username, password):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        # Automation logic here
        browser.close()
        return "Activation completed"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
```

### Dockerfile:
```dockerfile
FROM python:3.12-slim
RUN pip install flask playwright
RUN playwright install --with-deps chromium
COPY activation_service.py /app/
WORKDIR /app
CMD ["python", "activation_service.py"]
```

### Integration with existing code:
```python
# method_xumo_activation.py
import requests

def activate_xumo(device_ip, port, username, password):
    # Fetch code from device
    code_result = fetch_xumo_activation_code(device_ip, port, username, password)
    
    if not code_result['success']:
        return code_result
    
    # Send to activation service
    response = requests.post('http://localhost:5001/activate', 
                            json={'activation_code': code_result['activation_code']},
                            timeout=120)
    
    return response.json()
```

---

## Next Steps

1. **Short-term**: Document the browser requirement issue
2. **Medium-term**: Implement Playwright-based activation microservice
3. **Long-term**: Deploy microservice to cloud for production use

---

## Testing Current Setup

```bash
# Test if Firefox can be automated
python -c "from selenium import webdriver; driver = webdriver.Firefox(); driver.quit()"

# Test if Chrome works
python -c "from selenium import webdriver; driver = webdriver.Chrome(); driver.quit()"
```

If both fail, proceed with microservice approach.
