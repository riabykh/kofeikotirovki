# 🤖 "Кофе и Котировки" - AI-Powered Stock News Bot

<div align="center">

![Bot Status](https://img.shields.io/badge/Status-Active-brightgreen)
![Language](https://img.shields.io/badge/Language-Python-blue)
![AI](https://img.shields.io/badge/AI-OpenAI%20GPT-orange)
![Platform](https://img.shields.io/badge/Platform-Telegram-26A5E4)

*An intelligent Telegram bot that delivers personalized stock market news, AI-powered analysis, and real-time market insights in English and Russian.*

</div>

## 🌟 Features

### 📰 **AI-Powered News Digest**
- **Topic-Specific News**: Oil & Gas, Metals & Mining, Technology, Finance
- **Real-time Analysis**: Market impact assessment and key insights
- **Smart Translation**: AI-powered Russian/English translation
- **Source Links**: Direct links to full articles

### 📊 **Market Intelligence**
- **Asset Price Tracking**: Topic-relevant stocks, commodities, and indices
- **Market Notifications**: 15 minutes before/after market open/close
- **Daily Highlights**: Morning briefings with yesterday's key developments
- **AI Recommendations**: Investment insights and market outlook

### 🎯 **Personalization**
- **Multi-Language Support**: English and Russian (default)
- **Topic Selection**: Choose your areas of interest
- **Flexible Scheduling**: Manual notifications + automated updates
- **User Preferences**: Persistent settings storage

### ⏰ **Smart Scheduling**
- **8:00 AM**: Daily highlights and market outlook
- **Market Hours**: Topic-specific open/close notifications
- **Weekdays Only**: Monday-Friday market focus
- **Manual Triggers**: On-demand news updates

## 🚀 Quick Start

### Option 1: Railway Deployment (Recommended)
1. **Fork this repository** to your GitHub
2. **Sign up** at [railway.app](https://railway.app)
3. **Connect your GitHub** repository
4. **Set Environment Variables**:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token
   OPENAI_API_KEY=your_openai_key
   ```
5. **Deploy** - Your bot will be live in minutes! 🎉

### Option 2: Local Development
```bash
# Clone repository
git clone <your-repo-url>
cd stock-telegram-bot

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export TELEGRAM_BOT_TOKEN="your_bot_token"
export OPENAI_API_KEY="your_openai_key"

# Run bot
python stock_bot.py
```

### Option 3: Docker
```bash
# Set your OpenAI API key
export OPENAI_API_KEY="your_openai_key"

# Deploy with Docker
docker-compose up -d
```

## 📱 Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Initialize bot and select language |
| `/help` | Show available commands |
| `/language` | Change language (English/Russian) |
| `/topics` | Select interested topics |
| `/notify` | Send manual news digest |
| `/status` | Show current settings |
| `/stop` | Unsubscribe from notifications |

### Admin Commands
| Command | Description |
|---------|-------------|
| `/admin` | Admin panel access |
| `/users` | View user statistics |
| `/testnotifications` | Send test notifications |

## 🏗️ Architecture

### Core Components
- **`stock_bot.py`**: Main bot application with AI integration
- **`DatabaseManager`**: SQLite user management and preferences
- **OpenAI Integration**: News research, translation, and analysis
- **Market Data**: Real-time asset prices and market timing
- **Scheduling System**: Automated notifications and market alerts

### AI-Powered Features
- **News Research**: Topic-specific news discovery
- **Content Enhancement**: Market impact analysis
- **Translation**: Context-aware language conversion
- **Price Analysis**: Asset movement interpretation
- **Market Insights**: Investment recommendations

## 🛠️ Technology Stack

- **Python 3.11+**: Core application
- **python-telegram-bot**: Telegram Bot API
- **OpenAI API**: AI-powered content generation
- **SQLite**: User data and preferences
- **asyncio**: Asynchronous operations
- **schedule**: Task automation
- **Docker**: Containerized deployment

## 📈 Market Coverage

### Topics & Assets
- **All Markets**: Major indices (S&P 500, NASDAQ, Dow Jones)
- **Oil & Gas**: Crude oil, natural gas, energy stocks
- **Metals & Mining**: Gold, silver, copper, mining companies
- **Technology**: Tech stocks, AI companies, semiconductors
- **Finance**: Banks, financial services, interest rates

### Market Hours
- **US Markets**: 9:30 AM - 4:00 PM EST
- **NYMEX Energy**: 9:00 AM - 2:30 PM EST  
- **COMEX Metals**: 8:20 AM - 1:30 PM EST

## 🔧 Configuration

### Required Environment Variables
```bash
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
OPENAI_API_KEY=your_openai_api_key
```

### Optional Configuration
- Database path: `stock_bot.db` (default)
- Log level: INFO (default)
- Timezone: Automatic detection

## 📊 Deployment Options

| Platform | Difficulty | Cost | Reliability |
|----------|------------|------|-------------|
| Railway | ⭐ | $5-10/mo | ⭐⭐⭐⭐⭐ |
| DigitalOcean | ⭐⭐ | $4-6/mo | ⭐⭐⭐⭐⭐ |
| AWS EC2 | ⭐⭐⭐ | $3-8/mo | ⭐⭐⭐⭐⭐ |
| Heroku | ⭐ | $7-25/mo | ⭐⭐⭐⭐ |
| Self-hosted | ⭐⭐⭐ | $2-5/mo | ⭐⭐⭐⭐ |

## 📋 Requirements

### Python Dependencies
```
python-telegram-bot>=20.0
openai>=1.0.0
python-dotenv>=1.0.0
schedule>=1.2.0
asyncio
sqlite3 (built-in)
```

### External APIs
- **Telegram Bot API**: Free
- **OpenAI API**: ~$1-5/month (typical usage)

## 🔍 Monitoring

### Health Checks
```bash
# Run health check
python health_check.py

# Check bot status
curl https://api.telegram.org/bot<TOKEN>/getMe
```

### Backup & Recovery
```bash
# Backup database
./backup_script.sh

# Restore from backup
cp backups/stock_bot_backup_YYYYMMDD_HHMMSS.tar.gz ./
tar -xzf stock_bot_backup_YYYYMMDD_HHMMSS.tar.gz
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Common Issues
- **Bot not responding**: Check token and network connectivity
- **Translation errors**: Verify OpenAI API key and credits
- **Missing notifications**: Check user subscription status
- **Database errors**: Run health check script

### Getting Help
1. Check the [Deployment Guide](DEPLOYMENT.md)
2. Run the health check: `python health_check.py`
3. Review logs for error messages
4. Open an issue with detailed error information

## 🙏 Acknowledgments

- **OpenAI** for powerful AI capabilities
- **Telegram** for excellent bot platform
- **Python Community** for amazing libraries
- **Financial Data Providers** for market information

---

<div align="center">

**Made with ❤️ and ☕ for stock market enthusiasts**

*"Кофе и Котировки" - Your AI-powered financial companion*

</div>