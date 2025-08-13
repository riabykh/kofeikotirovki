# 📈 Кофе и Котировки (Coffee & Quotes) - AI Stock News Bot

A powerful Telegram bot that delivers AI-powered financial market analysis with real-time news, asset prices, and predictions.

## 🚀 Features

### 📰 Smart News Delivery
- **AI-Generated Digests**: Uses OpenAI to create concise, relevant market summaries
- **Real Source Attribution**: No fake links - only credible financial news sources
- **Multi-Message Format**: Split into 3 optimized messages to avoid Telegram limits
- **Topic-Based News**: Personalized content based on user interests

### 📊 Market Coverage
- **Oil & Gas**: Energy sector news and commodity prices
- **Metals & Mining**: Precious metals, industrial metals, and mining updates  
- **Technology**: Tech stocks and innovation trends
- **Finance & Banking**: Financial sector developments
- **All Topics**: Comprehensive market overview

### 🕐 Automated Notifications (European Timezone)
- **8:00 AM CET**: Daily morning market digest
- **9:00 AM CET**: European market opening summary
- **5:30 PM CET**: European market closing report
- **10:00 PM CET**: US market closing summary

### 🌍 Multi-Language Support
- **Russian** (default): Complete Russian interface and news
- **English**: Full English translation available
- **Smart Translation**: AI-powered content adaptation

### 👑 Admin Features
- **Manual Notifications**: `/notify` - Send digest to all subscribers
- **Self-Admin Setup**: `/makeadmin` - First users become admins automatically
- **User Management**: Add additional admins, view statistics

## 🎯 Commands

### User Commands
- `/start` - Initialize bot and see welcome message
- `/news` - Get latest AI-powered market digest (3 messages)
- `/topics` - Choose your market interests
- `/language` - Switch between Russian/English
- `/subscribe` - Enable automatic notifications
- `/unsubscribe` - Disable automatic notifications
- `/status` - Check your subscription status
- `/help` - Show help information

### Admin Commands
- `/notify` - Send manual notification to all users
- `/makeadmin` - Make yourself an administrator
- `/addadmin <user_id>` - Add another user as admin
- `/stats` - View bot statistics

## 🛠️ Setup

### Prerequisites
- Python 3.8+
- OpenAI API key
- Telegram Bot Token

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/riabykh/kofeikotirovki.git
cd kofeikotirovki
```

2. **Create virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Environment setup**
Create `.env` file:
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
OPENAI_API_KEY=your_openai_api_key
```

5. **Run the bot**
```bash
python3 stock_bot.py
```

## 🐳 Docker Deployment

### Using Docker Compose
```bash
docker-compose up -d
```

### Manual Docker
```bash
docker build -t stock-bot .
docker run -d --env-file .env stock-bot
```

## ☁️ Cloud Deployment

### Railway
1. Connect your GitHub repository to Railway
2. Set environment variables in Railway dashboard
3. Deploy automatically

### DigitalOcean/AWS
1. Create a VPS instance
2. Install Docker and Docker Compose
3. Clone repository and run with docker-compose

### Heroku
```bash
git push heroku main
```

## 📊 Architecture

### Core Components
- **StockNewsBot**: Main bot class handling all Telegram interactions
- **DatabaseManager**: SQLite database for user management and preferences
- **AI Integration**: OpenAI GPT-3.5-turbo for content generation
- **Scheduler**: Background thread for automated notifications
- **Multi-Message System**: Optimized message delivery to avoid Telegram limits

### Data Flow
1. **News Generation**: AI researches latest financial news by topic
2. **Asset Research**: AI fetches current asset prices and trends
3. **Content Processing**: Generate 3 separate optimized messages
4. **Delivery**: Send via Telegram with proper formatting and delays

## 🔧 Configuration

### Notification Schedule
All times in Central European Time (CET/CEST):
- Daily digest: 8:00 AM (every day)
- Market open: 9:00 AM (weekdays)
- EU close: 5:30 PM (weekdays)  
- US close: 10:00 PM (weekdays)

### Message Limits
- News digest: max 800 characters
- Asset prices: max 600 characters
- Predictions: max 600 characters

## 📈 Performance

### Optimizations
- **Split messaging** prevents Telegram character limit issues
- **Rate limiting** prevents API throttling
- **Background scheduling** doesn't block main bot operations
- **Error handling** with graceful fallbacks
- **Database migrations** for seamless updates

### Monitoring
- Comprehensive logging for debugging
- Success/failure tracking for notifications
- Auto-unsubscribe for blocked users

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 💡 Support

For support, please open an issue on GitHub or contact the maintainers.

---

**Made with ❤️ for the financial community**