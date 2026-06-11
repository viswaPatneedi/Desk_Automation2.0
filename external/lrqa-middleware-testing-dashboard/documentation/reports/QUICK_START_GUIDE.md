# 🚀 Quick Start Guide - Flask Application with venv

## Prerequisites
- Python 3.12.3 (or higher)
- Linux environment (Ubuntu, Raspberry Pi OS, etc.)
- Internet connection (for initial setup)

---

## 📋 One-Time Setup (First Time Only)

### 1. Navigate to Project Directory
```bash
cd /home/lrqa/Desktop/viswa/Desk-automation2.0/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
```

### 3. Activate Virtual Environment
```bash
source venv/bin/activate
```

### 4. Upgrade pip, setuptools, and wheel
```bash
pip install --upgrade pip setuptools wheel
```

### 5. Install All Dependencies
```bash
pip install -r requirements.txt
```

**Expected Output:**
```
Successfully installed [37 packages]
```

---

## ⚡ Run the Application

### Every Time You Run the App

#### Step 1: Activate Virtual Environment
```bash
cd /home/lrqa/Desktop/viswa/Desk-automation2.0/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard
source venv/bin/activate
```

You should see `(venv)` in your terminal prompt:
```
(venv) lrqa@lrqa-desktop:~/... $
```

#### Step 2: Start the Flask Application
```bash
python app.py
```

**Expected Output:**
```
============================================================
FLASK STARTUP CONFIGURATION
============================================================
Environment: DEVELOPMENT
Debug Mode: True
Host: 0.0.0.0
Port: 11079
============================================================

 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:11079
 * Running on http://10.0.0.123:11079
INFO:werkzeug:Press CTRL+C to quit
```

#### Step 3: Access the Application
- **Local device**: http://localhost:11079
- **Network device**: http://10.0.0.123:11079
- **Other IP**: http://<your-device-ip>:11079

---

## 🛑 Stop the Application

### Option 1: In the Terminal
Press `Ctrl+C` to stop the Flask development server

### Option 2: In Another Terminal
```bash
pkill -f "python app.py"
```

### Step 3: Deactivate Virtual Environment
```bash
deactivate
```

---

## 📊 File Structure

```
lrqa-middleware-testing-dashboard/
├── venv/                          # Python virtual environment
│   ├── bin/activate               # Activation script
│   ├── lib/python3.12/site-packages/  # Installed packages
│   └── ...
├── app.py                         # Main Flask application
├── requirements.txt               # Dependencies list
├── templates/
│   ├── index.html                 # Landing page (formerly dashboard.html)
│   ├── index2.html                # Methods page (formerly index.html)
│   └── ... (18 more templates)
├── models/                        # Data models
├── controllers/                   # Business logic
├── services/                      # Services layer
├── static/                        # CSS, JS, images
└── ... (other files)
```

---

## 🔧 Common Tasks

### Check if Flask is Running
```bash
ps aux | grep "python app.py" | grep -v grep
```

### Check if Port 11079 is in Use
```bash
ss -tuln | grep 11079
```

### View Recent Logs
```bash
tail -f /tmp/app_startup.log      # Latest startup
tail -f /tmp/flask_startup.log    # Previous startup
```

### Test API Endpoint
```bash
curl http://localhost:11079/login
```

### Run on Different Port
```bash
export FLASK_PORT=8080
python app.py
```

---

## ⚠️ Troubleshooting

### Issue: "Python command not found"
**Solution**: Use `python3` instead of `python`
```bash
python3 app.py
```

### Issue: "ModuleNotFoundError"
**Solution**: Ensure venv is activated
```bash
# Check for (venv) in prompt
source venv/bin/activate

# If still failing, reinstall
pip install --force-reinstall -r requirements.txt
```

### Issue: "Port 11079 is already in use"
**Solution 1**: Stop the existing process
```bash
pkill -f "python app.py"
sleep 2
python app.py
```

**Solution 2**: Use a different port
```bash
export FLASK_PORT=11080
python app.py
```

### Issue: "Permission denied"
**Solution**: Add executable permission
```bash
chmod +x app.py
chmod +x venv/bin/activate
```

### Issue: "No module named 'flask'"
**Solution**: Install dependencies
```bash
source venv/bin/activate
pip install -r requirements.txt
```

---

## 📝 Configuration

### Override Port (Environment Variable)
```bash
export FLASK_PORT=8080
python app.py
```

### Override Host
```bash
export FLASK_HOST=0.0.0.0
python app.py
```

### Enable Production Mode
```bash
export FLASK_ENV=production
python app.py
```

---

## 📦 Installed Packages

### Web Framework
- Flask 3.0.0
- Flask-Login 0.6.3
- Flask-Bcrypt 1.0.1
- Werkzeug 3.1.8

### Database
- SQLAlchemy 2.0.23
- psycopg2-binary 2.9.9
- Alembic 1.13.1

### Image Processing
- Pillow 10.1.0
- opencv-python 4.8.1.78
- scikit-image 0.22.0
- imagehash 4.3.1

### SSH & Networking
- Paramiko 3.4.0
- Requests 2.31.0
- cryptography 41.0.7

### Other
- Gevent 24.2.1 (Async)
- Gunicorn 21.2.0 (Production server)
- python-dotenv 1.0.0 (Environment variables)
- PyGithub 2.1.1 (GitHub API)

**Total: 37 packages**

---

## ✅ Verification Commands

### Check Python Version
```bash
source venv/bin/activate
python --version
```

### Check Flask Version
```bash
python -c "import flask; print(flask.__version__)"
```

### List All Installed Packages
```bash
pip list
```

### Check Specific Package
```bash
pip show flask
```

---

## 🚀 Performance Tips

### 1. Use Production Server (Gunicorn)
```bash
source venv/bin/activate
gunicorn -w 4 -b 0.0.0.0:11079 app:app
```

### 2. Run in Background
```bash
source venv/bin/activate
nohup python app.py > app.log 2>&1 &
```

### 3. Run with Systemd Service
```bash
# Create /etc/systemd/system/flask-app.service
[Unit]
Description=Flask LRQA Application
After=network.target

[Service]
Type=simple
User=lrqa
WorkingDirectory=/home/lrqa/Desktop/viswa/Desk-automation2.0/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard
Environment="PATH=/home/lrqa/Desktop/viswa/Desk-automation2.0/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard/venv/bin"
ExecStart=/home/lrqa/Desktop/viswa/Desk-automation2.0/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard/venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### 4. Monitor Resource Usage
```bash
watch -n 1 'ps aux | grep python'
```

---

## 📚 Additional Resources

- **Flask Documentation**: https://flask.palletsprojects.com/
- **Python venv Guide**: https://docs.python.org/3/library/venv.html
- **SQLAlchemy Docs**: https://docs.sqlalchemy.org/
- **PostgreSQL Docs**: https://www.postgresql.org/docs/

---

## 🎯 Complete Startup Checklist

- [ ] Navigate to project directory
- [ ] Activate virtual environment: `source venv/bin/activate`
- [ ] See `(venv)` in terminal prompt
- [ ] Start Flask: `python app.py`
- [ ] See "Running on http://..."
- [ ] Access via browser: http://localhost:11079
- [ ] Login with credentials
- [ ] Check port 11079 is listening
- [ ] Verify no errors in console

---

## 💾 Backup & Recovery

### Backup venv (Optional but Recommended)
```bash
tar -czf venv_backup.tar.gz venv
```

### Restore venv
```bash
tar -xzf venv_backup.tar.gz
```

### Clean & Reinstall
```bash
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

**Last Updated**: 2026-06-08  
**Version**: 1.0  
**Status**: ✅ Production Ready

