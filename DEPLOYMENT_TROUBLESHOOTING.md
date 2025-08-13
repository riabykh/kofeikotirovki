# 🚨 Deployment Troubleshooting Guide

## Common Issue: Multiple Bot Instances Conflict

### Error Message:
```
telegram.error.Conflict: Conflict: terminated by other getUpdates request; 
make sure that only one bot instance is running
```

### ⚠️ **CRITICAL**: This means multiple bot instances are running simultaneously!

## 🔍 **Diagnosis Steps:**

### 1. Check Local Instances
```bash
ps aux | grep stock_bot
pkill -f stock_bot.py  # Stop all local instances
```

### 2. Check Cloud Deployments
- **Railway**: Check if deployment is active
- **Heroku**: Check if dynos are running
- **VPS**: SSH and check processes
- **Docker**: Check running containers

### 3. Clear Telegram State
```bash
python3 clear_webhook.py  # Clear webhooks and pending updates
```

## 🛠️ **Resolution Steps:**

### Option A: Run Locally Only
1. **Stop ALL cloud deployments**:
   - Railway: Pause/delete deployment
   - Heroku: Scale dynos to 0
   - VPS: Stop bot service
   - Docker: Stop containers

2. **Clear conflicts**:
   ```bash
   python3 clear_webhook.py
   ./start_bot.sh
   ```

### Option B: Run on Cloud Only
1. **Stop local instances**:
   ```bash
   pkill -f stock_bot.py
   ```

2. **Deploy to cloud**:
   - Ensure only ONE cloud platform is active
   - Set environment variables
   - Monitor logs for conflicts

### Option C: Switch Between Deployments
1. **Before switching deployment location**:
   ```bash
   # Stop current deployment
   # Clear Telegram state
   python3 clear_webhook.py
   # Wait 30 seconds
   # Start new deployment
   ```

## 🚀 **Safe Deployment Practices:**

### 1. Use Safe Starter Script
```bash
./start_bot.sh  # Automatically handles conflicts
```

### 2. Monitor Health
```bash
python3 health_check.py  # Check bot status
```

### 3. Graceful Shutdown
```bash
# Send SIGTERM (Ctrl+C) instead of kill -9
# Let the bot cleanup properly
```

## 📊 **Platform-Specific Instructions:**

### Railway Deployment
1. **Stop local bot first**:
   ```bash
   pkill -f stock_bot.py
   python3 clear_webhook.py
   ```

2. **Deploy to Railway**:
   - Push to GitHub
   - Railway auto-deploys
   - Monitor Railway logs

3. **If conflicts occur**:
   - Pause Railway deployment
   - Clear webhook locally
   - Resume deployment

### Local Development
1. **Stop cloud deployments first**
2. **Use safe starter**:
   ```bash
   ./start_bot.sh
   ```

### Docker Deployment
```bash
# Stop any existing containers
docker stop $(docker ps -q --filter "ancestor=stock-bot")
# Clear webhook
python3 clear_webhook.py
# Start new container
docker-compose up -d
```

## 🔧 **Emergency Recovery:**

### Complete Reset
```bash
# 1. Stop EVERYTHING
pkill -9 -f stock_bot
docker stop $(docker ps -q --filter "ancestor=stock-bot") 2>/dev/null
# Stop all cloud deployments manually

# 2. Clear Telegram state
python3 clear_webhook.py

# 3. Wait 30 seconds
sleep 30

# 4. Start fresh
./start_bot.sh
```

### Rollback to Working Version
```bash
./rollback.sh  # Use backup version
```

## 📝 **Prevention:**

1. **Document active deployments**
2. **Use only ONE deployment at a time**
3. **Always clear webhook when switching**
4. **Monitor logs for conflicts**
5. **Use health checks regularly**

## 🆘 **Still Having Issues?**

1. Check Railway/Heroku dashboard for active deployments
2. Verify environment variables are set correctly
3. Check if webhook is set by another service
4. Wait 5 minutes between stopping and starting
5. Use `python3 clear_webhook.py` before any restart

---

**Remember**: Telegram bots can only have ONE active polling connection at a time!
