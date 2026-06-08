# AI Vision OCR Setup Instructions

## FREE Option: Ollama with LLaVA (Recommended)

### 1. Install Ollama
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama service
ollama serve &

# Download LLaVA model (vision-capable, ~4.7GB)
ollama pull llava
```

### 2. Configure Application
```bash
# Edit the service file
sudo nano /etc/systemd/system/device-testing.service

# Add these lines in the [Service] section:
Environment="AI_VISION_PROVIDER=ollama"
Environment="OLLAMA_BASE_URL=http://localhost:11434"

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart device-testing.service
```

### 3. Verify Ollama is Running
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Test with a simple request
ollama run llava "Describe this image" < test.png
```

### Benefits:
- ✅ **100% FREE** - No API costs ever
- ✅ **Runs locally** - No internet required after model download
- ✅ **Privacy** - Images never leave your server
- ✅ **Good accuracy** - Comparable to commercial APIs for text extraction

---

## Paid Option: OpenAI GPT-4 Vision

### 1. Install OpenAI Package
```bash
source venv/bin/activate
pip install openai
```

### 2. Set Environment Variables

#### Option A: Set in System Environment (Permanent)
```bash
# Edit the service file
sudo nano /etc/systemd/system/device-testing.service

# Add these lines in the [Service] section:
Environment="AI_VISION_PROVIDER=openai"
Environment="OPENAI_API_KEY=your-api-key-here"

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart device-testing.service
```

#### Option B: Set in Shell (Temporary - for testing)
```bash
export AI_VISION_PROVIDER=openai
export OPENAI_API_KEY=your-api-key-here
# Then restart the service
```

### 3. Get OpenAI API Key
1. Go to https://platform.openai.com/api-keys
2. Create new API key
3. Copy and use in environment variable

### 4. Verify Configuration
The application will automatically:
- Use OpenAI Vision if configured
- Fall back to Tesseract if OpenAI fails or not configured
- Log which method is being used in real-time logs

### 5. Cost Considerations
- GPT-4o Vision: ~$0.01 per image
- For high-volume testing, Tesseract (free) might be more cost-effective
- You can switch between providers by changing AI_VISION_PROVIDER

## Alternative Providers (Future Enhancement)

### Google Cloud Vision
```bash
export AI_VISION_PROVIDER=google
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
```

### Azure Computer Vision
```bash
export AI_VISION_PROVIDER=azure
export AZURE_VISION_KEY=your-key
export AZURE_VISION_ENDPOINT=your-endpoint
```

## Disable AI Vision (Use Tesseract Only)
```bash
export AI_VISION_PROVIDER=tesseract
# Or simply don't set any AI_VISION_PROVIDER variable
```
