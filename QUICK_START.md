# 🚀 Quick Start Guide - Stock Telegram Bot

Get your Stock Market News Telegram Bot running in 5 minutes!

## ⚡ Super Quick Setup

### 1. Get Your Bot Token
- Open Telegram, search for `@BotFather`
- Send `/newbot`
- Choose a name and username for your bot
- **Copy the token** (you'll need this!)

### 2. Setup the Bot
```bash
# Download and navigate to the project
cd stock-telegram-bot

# Create virtual environment
python3 -m venv venv

# Activate it (Mac/Linux)
source venv/bin/activate
# Or Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with your token
echo "TELEGRAM_BOT_TOKEN=YOUR_ACTUAL_TOKEN_HERE" > .env
```

### 3. Run the Bot
```bash
# Start the bot
python3 stock_bot.py
```

**That's it!** 🎉

## 📱 Test Your Bot

1. **Find your bot** in Telegram (search the username you chose)
2. **Send `/start`** to begin
3. **Send `/news`** to get market news
4. **Send `/subscribe`** for daily updates

## 🔐 Admin Features

- **First user automatically becomes admin** when using `/addadmin`
- **Use `/notify`** to manually trigger notifications to all subscribers
- **Use `/addadmin <user_id>`** to grant admin access to others

## 🕐 What Happens Next

- **9:00 AM EST daily**: Automatic market news summary
- **9:30 AM EST weekdays**: Market opening updates
- **Any time**: Use `/news` for instant updates

## 🆘 Need Help?

- **Bot not responding?** Check if it's running in your terminal
- **No news?** Some RSS feeds might be temporarily down
- **More help?** Check the full README.md or DEPLOYMENT.md

## 🔧 Customize (Optional)

- **Change timing**: Edit `schedule_daily_summaries()` in `stock_bot.py`
- **Add news sources**: Edit `news_sources` dictionary
- **Deploy to cloud**: See DEPLOYMENT.md for options

---

**⚠️ Remember**: Replace `YOUR_ACTUAL_TOKEN_HERE` with the real token from BotFather!
