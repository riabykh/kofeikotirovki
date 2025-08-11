# 🚀 Deployment Guide - Stock News Bot

This guide covers multiple deployment options for running your AI-powered stock news bot 24/7.

## 📋 Prerequisites

Before deploying, ensure you have:
- ✅ Bot token: `8392034913:AAGk9ZyeVeGhTZzodCvt1hdOGr2SR7GF1qE`
- ✅ OpenAI API key
- ✅ Working bot code
- ✅ All dependencies listed in `requirements.txt`

## 🌐 Deployment Options

### 1. 🐳 Docker + Cloud (Recommended)
**Best for**: Scalability, reliability, professional deployment

### 2. ☁️ Cloud Platforms (Easy)
**Best for**: Quick deployment, managed infrastructure

### 3. 🖥️ VPS/Dedicated Server
**Best for**: Full control, cost-effective for long-term

### 4. 🏠 Local Server/Raspberry Pi
**Best for**: Learning, testing, home lab

---

## 🐳 Option 1: Docker Deployment

### Step 1: Create Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
USER botuser

# Run the bot
CMD ["python", "stock_bot.py"]
```

### Step 2: Create docker-compose.yml
```yaml
version: '3.8'

services:
  stock-bot:
    build: .
    restart: unless-stopped
    environment:
      - TELEGRAM_BOT_TOKEN=8392034913:AAGk9ZyeVeGhTZzodCvt1hdOGr2SR7GF1qE
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    healthcheck:
      test: ["CMD", "python", "-c", "import sqlite3; conn=sqlite3.connect('stock_bot.db'); conn.close()"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Step 3: Deploy Commands
```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down

# Update
docker-compose pull && docker-compose up -d
```

---

## ☁️ Option 2: Cloud Platform Deployment

### A. Railway (Recommended - Easy)
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

### B. Heroku
```bash
# Install Heroku CLI and login
heroku login

# Create app
heroku create your-stock-bot

# Set environment variables
heroku config:set TELEGRAM_BOT_TOKEN=8392034913:AAGk9ZyeVeGhTZzodCvt1hdOGr2SR7GF1qE
heroku config:set OPENAI_API_KEY=your_openai_key

# Deploy
git push heroku main
```

### C. DigitalOcean App Platform
1. Connect GitHub repository
2. Set environment variables in dashboard
3. Deploy automatically

### D. AWS EC2/ECS
- Use Docker deployment on EC2 instance
- Or deploy to ECS with Docker container

---

## 🖥️ Option 3: VPS Deployment

### Step 1: Server Setup (Ubuntu/Debian)
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3 python3-pip python3-venv git -y

# Clone repository
git clone <your-repo-url>
cd stock-telegram-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Create Systemd Service
```bash
sudo nano /etc/systemd/system/stock-bot.service
```

```ini
[Unit]
Description=Stock News Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/stock-telegram-bot
Environment=PATH=/home/ubuntu/stock-telegram-bot/venv/bin
Environment=TELEGRAM_BOT_TOKEN=8392034913:AAGk9ZyeVeGhTZzodCvt1hdOGr2SR7GF1qE
Environment=OPENAI_API_KEY=your_openai_key_here
ExecStart=/home/ubuntu/stock-telegram-bot/venv/bin/python stock_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Step 3: Enable and Start Service
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable stock-bot.service

# Start service
sudo systemctl start stock-bot.service

# Check status
sudo systemctl status stock-bot.service

# View logs
sudo journalctl -u stock-bot.service -f
```

---

## 🏠 Option 4: Raspberry Pi / Local Server

### Step 1: Setup (Raspberry Pi OS)
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python dependencies
sudo apt install python3-pip python3-venv git -y

# Clone and setup
git clone <your-repo-url>
cd stock-telegram-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Auto-start Script
```bash
# Create startup script
nano ~/start_bot.sh
```

```bash
#!/bin/bash
cd /home/pi/stock-telegram-bot
source venv/bin/activate
export TELEGRAM_BOT_TOKEN="8392034913:AAGk9ZyeVeGhTZzodCvt1hdOGr2SR7GF1qE"
export OPENAI_API_KEY="your_openai_key_here"
python stock_bot.py
```

```bash
# Make executable
chmod +x ~/start_bot.sh

# Add to crontab
crontab -e
# Add: @reboot /home/pi/start_bot.sh
```

---

## 🔧 Additional Configuration

### Environment Variables
Create `.env` file for local development:
```bash
TELEGRAM_BOT_TOKEN=8392034913:AAGk9ZyeVeGhTZzodCvt1hdOGr2SR7GF1qE
OPENAI_API_KEY=your_openai_key_here
```

### Logging Configuration
Add to `stock_bot.py`:
```python
import logging
from logging.handlers import RotatingFileHandler

# Setup file logging
handler = RotatingFileHandler('logs/bot.log', maxBytes=10*1024*1024, backupCount=5)
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)
```

### Health Check Script
```python
# health_check.py
import requests
import sys

def check_bot_health():
    try:
        # Check if bot is responding
        token = "8392034913:AAGk9ZyeVeGhTZzodCvt1hdOGr2SR7GF1qE"
        response = requests.get(f"https://api.telegram.org/bot{token}/getMe")
        if response.status_code == 200:
            print("✅ Bot is healthy")
            return True
        else:
            print("❌ Bot health check failed")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

if __name__ == "__main__":
    if not check_bot_health():
        sys.exit(1)
```

---

## 📊 Monitoring & Maintenance

### 1. Log Monitoring
```bash
# View recent logs
tail -f logs/bot.log

# Search for errors
grep "ERROR" logs/bot.log
```

### 2. Database Backup
```bash
# Backup database
cp stock_bot.db backups/stock_bot_$(date +%Y%m%d_%H%M%S).db

# Automated backup script
#!/bin/bash
# backup_db.sh
DATE=$(date +%Y%m%d_%H%M%S)
cp stock_bot.db backups/stock_bot_$DATE.db
find backups/ -name "*.db" -mtime +7 -delete  # Keep 7 days
```

### 3. Update Process
```bash
# Update bot code
git pull origin main

# Restart service (systemd)
sudo systemctl restart stock-bot.service

# Or restart Docker
docker-compose restart
```

---

## 🔒 Security Best Practices

1. **Environment Variables**: Never commit tokens to git
2. **Firewall**: Only open necessary ports
3. **SSL/TLS**: Use HTTPS for webhooks (if applicable)
4. **Updates**: Keep system and dependencies updated
5. **Backups**: Regular database backups
6. **Monitoring**: Set up alerts for failures

---

## 🚀 Quick Start (Railway - Easiest)

1. **Fork/Clone** this repository to GitHub
2. **Sign up** at [railway.app](https://railway.app)
3. **Connect GitHub** and select your repository
4. **Add Environment Variables**:
   - `TELEGRAM_BOT_TOKEN`: `8392034913:AAGk9ZyeVeGhTZzodCvt1hdOGr2SR7GF1qE`
   - `OPENAI_API_KEY`: `your_openai_key`
5. **Deploy** - Railway will automatically build and run your bot!

## 📞 Support

If you encounter issues:
1. Check logs for error messages
2. Verify environment variables are set correctly
3. Ensure all dependencies are installed
4. Test locally before deploying
5. Check network connectivity and API quotas

Your bot will now run 24/7 with automatic restarts, logging, and monitoring! 🎉