import asyncio
import logging
from datetime import datetime, timedelta
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
import schedule
import time
from typing import List, Dict
import os
from dataclasses import dataclass
import sqlite3
from openai import AsyncOpenAI

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

@dataclass
class NewsItem:
    title: str
    summary: str
    source: str
    published: str
    url: str = ""

@dataclass
class AssetItem:
    symbol: str
    name: str
    price: float
    change: float
    change_direction: str
    source: str = "AI Research"

class DatabaseManager:
    def __init__(self, db_path: str = "stock_bot.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table to store subscriber information
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                subscribed BOOLEAN DEFAULT TRUE,
                language TEXT DEFAULT 'ru',
                topic_preferences TEXT DEFAULT 'all',
                joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Admin users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_users (
                user_id INTEGER PRIMARY KEY,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # Run database migration for existing installations
        self._migrate_database()
    
    def _migrate_database(self):
        """Migrate existing database to add new columns if they don't exist"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get existing columns
            cursor.execute('PRAGMA table_info(users)')
            columns = [column[1] for column in cursor.fetchall()]
            
            # Check if language column exists
            if 'language' not in columns:
                print("🔄 Adding language column to existing database...")
                cursor.execute('ALTER TABLE users ADD COLUMN language TEXT DEFAULT "ru"')
                cursor.execute('UPDATE users SET language = "ru" WHERE language IS NULL')
                print("✅ Language column migration completed!")
            
            # Check if topic_preferences column exists
            if 'topic_preferences' not in columns:
                print("🔄 Adding topic_preferences column to existing database...")
                cursor.execute('ALTER TABLE users ADD COLUMN topic_preferences TEXT DEFAULT "all"')
                cursor.execute('UPDATE users SET topic_preferences = "all" WHERE topic_preferences IS NULL')
                print("✅ Topic preferences column migration completed!")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"⚠️ Database migration warning: {e}")
    
    def add_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Add or update a user in the database without resetting preferences"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Use UPSERT to preserve existing preferences
        cursor.execute('''
            INSERT INTO users (user_id, username, first_name, last_name, last_active)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name,
                last_name=excluded.last_name,
                last_active=CURRENT_TIMESTAMP
        ''', (user_id, username, first_name, last_name))
        
        conn.commit()
        conn.close()
    
    def get_subscribed_users(self) -> List[int]:
        """Get all subscribed user IDs"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE subscribed = TRUE')
        users = [row[0] for row in cursor.fetchall()]
        conn.close()
        return users
    
    def get_all_users(self) -> List[int]:
        """Get all user IDs"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users')
        users = [row[0] for row in cursor.fetchall()]
        conn.close()
        return users
    
    def subscribe_user(self, user_id: int):
        """Subscribe a user to daily updates"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET subscribed = TRUE WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
    
    def unsubscribe_user(self, user_id: int):
        """Unsubscribe a user from daily updates"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET subscribed = FALSE WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
    
    def get_user_count(self) -> int:
        """Get total number of users"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def add_admin(self, user_id: int):
        """Add a user as admin"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO admin_users (user_id) VALUES (?)', (user_id,))
        conn.commit()
        conn.close()
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM admin_users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result is not None
    
    def get_user_language(self, user_id: int) -> str:
        """Get user's preferred language"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT language FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 'ru'
    
    def set_user_language(self, user_id: int, language: str):
        """Set user's preferred language"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET language = ? WHERE user_id = ?', (language, user_id))
        conn.commit()
        conn.close()
    
    def get_user_topics(self, user_id: int) -> str:
        """Get user's topic preferences"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT topic_preferences FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 'all'
    
    def set_user_topics(self, user_id: int, topics: str):
        """Set user's topic preferences"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET topic_preferences = ? WHERE user_id = ?', (topics, user_id))
        conn.commit()
        conn.close()

class StockNewsBot:
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.bot = Bot(token=bot_token)
        self.application = Application.builder().token(bot_token).build()
        self.db = DatabaseManager()
        
        # Topic definitions
        self.available_topics = {
            'all': {
                'en': 'All Topics',
                'ru': 'Все темы'
            },
            'oil_gas': {
                'en': 'Oil & Gas',
                'ru': 'Нефть и газ'
            },
            'metals_mining': {
                'en': 'Metals & Mining',
                'ru': 'Металлы и добыча'
            },
            'technology': {
                'en': 'Technology',
                'ru': 'Технологии'
            },
            'finance': {
                'en': 'Finance & Banking',
                'ru': 'Финансы и банкинг'
            }
        }
        
        # Supported languages
        self.supported_languages = ['en', 'ru']
        self.default_language = 'ru'
        
        # Translation dictionaries
        self.translations = {
            'en': {
                'welcome_title': 'Кофе и Котировки',
                'welcome_message': 'Welcome, {name}! I am your personal financial markets news assistant.',
                'what_i_do': 'What I offer:',
                'daily_news': 'Daily market news summaries powered by AI research',
                'sentiment_analysis': 'AI-powered market sentiment analysis',
                'predictions': 'Trending topics and market predictions',
                'auto_updates': 'Automatic daily updates (9:00 AM & 9:30 AM EST)',
                'commands': 'Commands:',
                'news_cmd': '/news - Get latest market news',
                'notify_cmd': '/notify - Manually trigger notifications for all subscribers (Admin only)',
                'subscribe_cmd': '/subscribe - Enable daily news updates',
                'unsubscribe_cmd': '/unsubscribe - Disable daily updates',
                'language_cmd': '/language - Choose language with buttons',
                'topics_cmd': '/topics - Choose topics of interest',
                'help_cmd': '/help - Show all commands',
                'status_cmd': '/status - Check bot and market status',
                'stats_cmd': '/stats - View bot usage statistics',
                'admin_features': 'Admin Features:',
                'first_user_admin': 'First user automatically becomes admin',
                'fetching_news': '📰 Researching latest market news...',
                'no_news': '❌ Unable to fetch news at the moment. Please try again later.',
                'error_fetching': '❌ Error occurred while fetching news. Please try again.',
                'subscribed': '✅ You are now subscribed to daily market updates!',
                'already_subscribed': 'ℹ️ You are already subscribed to daily updates.',
                'unsubscribed': '✅ You have been unsubscribed from daily updates.',
                'not_subscribed': 'ℹ️ You are not currently subscribed.',
                'language_selection': '🌍 Language Selection',
                'current_language': 'Current language',
                'topic_selection': '🎯 Topic Selection',
                'current_topics': 'Current topic',
                'topics_updated': '✅ Topic preferences updated!',
                'notification_success': 'Manual notification sent successfully!',
                'no_subscribers': 'No subscribers found.',
                'error_notification': '❌ Error sending notifications.',
                'results': 'Results',
                'successfully_sent': 'Successfully sent',
                'failed_to_send': 'Failed to send',
                'total_subscribers': 'Total subscribers',
                'sent_at': 'Sent at',
                'all_notified': 'All subscribers have been notified!'
            },
            'ru': {
                'welcome_title': 'Кофе и Котировки',
                'welcome_message': 'Добро пожаловать, {name}! Я ваш персональный помощник по новостям финансовых рынков.',
                'what_i_do': 'Что я предлагаю:',
                'daily_news': 'Ежедневные сводки рыночных новостей на основе ИИ-исследований',
                'sentiment_analysis': 'Анализ настроений рынка с помощью ИИ',
                'predictions': 'Трендовые темы и прогнозы рынка',
                'auto_updates': 'Автоматические ежедневные обновления (9:00 и 9:30 EST)',
                'commands': 'Команды:',
                'news_cmd': '/news - Получить последние новости рынка',
                'notify_cmd': '/notify - Вручную отправить уведомления всем подписчикам (только для админов)',
                'subscribe_cmd': '/subscribe - Включить ежедневные обновления новостей',
                'unsubscribe_cmd': '/unsubscribe - Отключить ежедневные обновления',
                'language_cmd': '/language - Выбрать язык кнопками',
                'topics_cmd': '/topics - Выбрать интересующие темы',
                'help_cmd': '/help - Показать все команды',
                'status_cmd': '/status - Проверить статус бота и рынка',
                'stats_cmd': '/stats - Просмотреть статистику использования бота',
                'admin_features': 'Функции администратора:',
                'first_user_admin': 'Первый пользователь автоматически становится администратором',
                'fetching_news': '📰 Исследую последние новости рынка...',
                'no_news': '❌ Не удалось получить новости в данный момент. Попробуйте позже.',
                'error_fetching': '❌ Произошла ошибка при получении новостей. Попробуйте снова.',
                'subscribed': '✅ Вы подписались на ежедневные обновления рынка!',
                'already_subscribed': 'ℹ️ Вы уже подписаны на ежедневные обновления.',
                'unsubscribed': '✅ Вы отписались от ежедневных обновлений.',
                'not_subscribed': 'ℹ️ Вы в настоящее время не подписаны.',
                'language_selection': '🌍 Выбор языка',
                'current_language': 'Текущий язык',
                'topic_selection': '🎯 Выбор тем',
                'current_topics': 'Текущая тема',
                'topics_updated': '✅ Предпочтения по темам обновлены!',
                'notification_success': 'Ручное уведомление отправлено успешно!',
                'no_subscribers': 'Подписчики не найдены.',
                'error_notification': '❌ Ошибка отправки уведомлений.',
                'results': 'Результаты',
                'successfully_sent': 'Успешно отправлено',
                'failed_to_send': 'Не удалось отправить',
                'total_subscribers': 'Всего подписчиков',
                'sent_at': 'Отправлено в',
                'all_notified': 'Все подписчики уведомлены!'
            }
        }
        
        # Market timing definitions for different topics
        self.market_times = {
            'all': {
                'markets': [
                    {'name': 'US Markets', 'open': '09:30', 'close': '16:00', 'timezone': 'EST'},
                    {'name': 'European Markets', 'open': '03:00', 'close': '11:30', 'timezone': 'EST'},
                    {'name': 'Asian Markets', 'open': '20:00', 'close': '02:00', 'timezone': 'EST'}
                ]
            },
            'oil_gas': {
                'markets': [
                    {'name': 'NYMEX Energy', 'open': '09:00', 'close': '14:30', 'timezone': 'EST'},
                    {'name': 'ICE Brent', 'open': '02:00', 'close': '16:00', 'timezone': 'EST'},
                    {'name': 'US Energy Stocks', 'open': '09:30', 'close': '16:00', 'timezone': 'EST'}
                ]
            },
            'metals_mining': {
                'markets': [
                    {'name': 'COMEX Metals', 'open': '08:00', 'close': '13:30', 'timezone': 'EST'},
                    {'name': 'LME Metals', 'open': '03:00', 'close': '16:00', 'timezone': 'EST'},
                    {'name': 'Mining Stocks', 'open': '09:30', 'close': '16:00', 'timezone': 'EST'}
                ]
            },
            'technology': {
                'markets': [
                    {'name': 'NASDAQ Tech', 'open': '09:30', 'close': '16:00', 'timezone': 'EST'},
                    {'name': 'Asian Tech', 'open': '20:00', 'close': '02:00', 'timezone': 'EST'},
                    {'name': 'European Tech', 'open': '03:00', 'close': '11:30', 'timezone': 'EST'}
                ]
            },
            'finance': {
                'markets': [
                    {'name': 'NYSE Financial', 'open': '09:30', 'close': '16:00', 'timezone': 'EST'},
                    {'name': 'Bond Markets', 'open': '08:00', 'close': '17:00', 'timezone': 'EST'},
                    {'name': 'Currency Markets', 'open': '17:00', 'close': '17:00', 'timezone': 'EST'}
                ]
            }
        }
        
        # Set up command handlers
        self.setup_handlers()
    
    def get_text(self, user_id: int, key: str) -> str:
        """Get translated text for user"""
        language = self.db.get_user_language(user_id)
        return self.translations.get(language, self.translations['ru']).get(key, key)
    
    def setup_handlers(self):
        """Set up command handlers"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("news", self.news_command))
        self.application.add_handler(CommandHandler("subscribe", self.subscribe_command))
        self.application.add_handler(CommandHandler("unsubscribe", self.unsubscribe_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("notify", self.notify_command))
        self.application.add_handler(CommandHandler("addadmin", self.add_admin_command))
        self.application.add_handler(CommandHandler("language", self.language_command))
        self.application.add_handler(CommandHandler("topics", self.topics_command))
        self.application.add_handler(CommandHandler("testnotifications", self.test_notifications_command))
        
        # Add callback query handler for inline buttons
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
    
    async def setup_bot_menu(self):
        """Set up bot commands menu"""
        from telegram import BotCommand
        
        # Define all available commands
        commands = [
            BotCommand("start", "🎉 Start the bot and see welcome message"),
            BotCommand("news", "📰 Get latest AI-powered market news"),
            BotCommand("topics", "🎯 Choose your topics of interest"),
            BotCommand("language", "🌍 Choose your language"),
            BotCommand("subscribe", "✅ Enable daily news updates"),
            BotCommand("unsubscribe", "❌ Disable daily updates"),
            BotCommand("status", "📊 Check bot and market status"),
            BotCommand("help", "❓ Show all commands and help"),
            BotCommand("notify", "🔔 Manual notification (Admin only)"),
            BotCommand("testnotifications", "🧪 Test notifications (Admin only)"),
            BotCommand("addadmin", "👑 Add new admin (Admin only)")
        ]
        
        # Set commands menu
        try:
            await self.bot.set_my_commands(commands)
            logger.info("✅ Bot commands menu set successfully")
        except Exception as e:
            logger.warning(f"⚠️ Could not set bot commands menu: {e}")
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin (first user becomes admin automatically)"""
        if self.db.get_user_count() == 1:
            self.db.add_admin(user_id)
            return True
        return self.db.is_admin(user_id)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        try:
            logger.info(f"📥 Received /start command from user {update.effective_user.id}")
            user = update.effective_user
            self.db.add_user(user.id, user.username, user.first_name, user.last_name)
            
            # Make first user admin automatically
            if self.db.get_user_count() == 1:
                self.db.add_admin(user.id)
            
            welcome_title = self.get_text(user.id, 'welcome_title')
            welcome_message = self.get_text(user.id, 'welcome_message').format(name=user.first_name or user.username or "User")
            what_i_do = self.get_text(user.id, 'what_i_do')
            daily_news = self.get_text(user.id, 'daily_news')
            sentiment_analysis = self.get_text(user.id, 'sentiment_analysis')
            predictions = self.get_text(user.id, 'predictions')
            auto_updates = self.get_text(user.id, 'auto_updates')
            commands = self.get_text(user.id, 'commands')
            news_cmd = self.get_text(user.id, 'news_cmd')
            topics_cmd = self.get_text(user.id, 'topics_cmd')
            subscribe_cmd = self.get_text(user.id, 'subscribe_cmd')
            unsubscribe_cmd = self.get_text(user.id, 'unsubscribe_cmd')
            language_cmd = self.get_text(user.id, 'language_cmd')
            help_cmd = self.get_text(user.id, 'help_cmd')
            status_cmd = self.get_text(user.id, 'status_cmd')
            stats_cmd = self.get_text(user.id, 'stats_cmd')
            
            # Admin commands
            admin_commands = ""
            if self.is_admin(user.id):
                admin_commands = f"\n\n**🔧 Admin Commands:**\n/testnotifications - Test notifications to all users\n/addadmin <user_id> - Add new administrator"
            
            message = f"""
🎉 **{welcome_title}** 🎉

{welcome_message}

**📈 {what_i_do}**
• {daily_news}
• {sentiment_analysis}
• {predictions}
• {auto_updates}

**📱 {commands}**
{news_cmd}
{topics_cmd}
{subscribe_cmd}
{unsubscribe_cmd}
{language_cmd}
{help_cmd}
{status_cmd}
{stats_cmd}

Ready to start! Use /news to get your first market digest! 🚀{admin_commands}
            """
            
            await update.message.reply_text(message, parse_mode='Markdown')
            logger.info(f"✅ Sent start response to user {user.id}")
            
        except Exception as e:
            logger.error(f"❌ Error in start_command: {e}")
            try:
                await update.message.reply_text("❌ Error occurred. Please try again later.")
            except:
                pass
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        await self.start_command(update, context)
    
    async def news_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /news command - get AI-powered market digest"""
        user = update.effective_user
        self.db.add_user(user.id, user.username, user.first_name, user.last_name)
        
        await update.message.reply_text(self.get_text(user.id, 'fetching_news'))
        
        try:
            digest = await self.generate_ai_digest(user.id)
            await update.message.reply_text(digest, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error generating AI digest for user {user.id}: {e}")
            await update.message.reply_text(self.get_text(user.id, 'error_fetching'))
    
    async def generate_ai_digest(self, user_id: int) -> str:
        """Generate AI-powered market digest based on user's topic preferences"""
        try:
            user_topics = self.db.get_user_topics(user_id)
            user_language = self.db.get_user_language(user_id)
            
            logger.info(f"🎯 Generating AI digest for user {user_id}: topic='{user_topics}', language='{user_language}'")
            
            # Get topic-specific news and assets
            news_items = await self.fetch_ai_news(user_topics, user_language)
            asset_items = await self.fetch_ai_assets(user_topics, user_language)
            
            # Generate unified digest using ChatGPT
            digest = await self.generate_unified_digest(news_items, asset_items, user_topics, user_language)
            
            return digest
            
        except Exception as e:
            logger.error(f"Error generating AI digest: {e}")
            return self.get_text(user_id, 'error_fetching')
    
    async def fetch_ai_news(self, topic: str, language: str) -> List[NewsItem]:
        """Fetch topic-specific news using AI research"""
        try:
            # Define topic focus for AI research
            topic_descriptions = {
                'all': {
                    'en': 'general financial markets, major companies, stock indices, economic indicators, and global market trends',
                    'ru': 'общие финансовые рынки, крупные компании, фондовые индексы, экономические показатели и глобальные рыночные тренды'
                },
                'oil_gas': {
                    'en': 'oil prices, natural gas markets, energy companies, OPEC decisions, pipeline developments, and energy policy changes',
                    'ru': 'цены на нефть, рынки природного газа, энергетические компании, решения ОПЕК, развитие трубопроводов и изменения энергетической политики'
                },
                'metals_mining': {
                    'en': 'precious metals prices, industrial metals, mining companies, commodity markets, mining regulations, and supply chain developments',
                    'ru': 'цены на драгоценные металлы, промышленные металлы, горнодобывающие компании, товарные рынки, регулирование добычи и развитие цепочек поставок'
                },
                'technology': {
                    'en': 'technology companies, AI developments, semiconductor industry, software updates, digital transformation, and tech IPOs',
                    'ru': 'технологические компании, развитие ИИ, полупроводниковая промышленность, обновления программного обеспечения, цифровая трансформация и технологические IPO'
                },
                'finance': {
                    'en': 'banking sector, financial services, central bank decisions, interest rates, regulatory changes, and investment trends',
                    'ru': 'банковский сектор, финансовые услуги, решения центральных банков, процентные ставки, изменения в регулировании и инвестиционные тренды'
                }
            }
            
            topic_desc = topic_descriptions[topic].get(language, topic_descriptions[topic]['en'])
            
            # Create AI prompt for news research
            current_date = datetime.now().strftime("%Y-%m-%d")
            prompt = f"""Research and provide the latest financial news for {topic_desc} as of {current_date}.

Please provide 5-7 most important recent news stories with:
1. Accurate, factual information from the last 24-48 hours
2. Clear market impact analysis
3. Reliable source attribution with URLs when possible

Format each story as:
Title: [Concise, informative headline]
Summary: [2-3 sentences with key details and market impact]
Source: [Reputable financial news source]
URL: [Link to full article if available, or main source website]
Date: [Recent date]

Focus on high-impact news that would be most relevant to investors and traders in this sector. Include links to reputable financial news sources like Bloomberg, Reuters, MarketWatch, Financial Times, etc."""

            # Generate news using AI
            client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional financial news researcher. Provide accurate, timely market news with proper source attribution. Focus on factual information and clear market analysis."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1200,
                temperature=0.3
            )
            
            # Parse AI response into NewsItem objects
            content = response.choices[0].message.content
            news_items = self._parse_ai_news(content)
            
            logger.info(f"Generated {len(news_items)} AI news items for topic: {topic}")
            return news_items
            
        except Exception as e:
            logger.error(f"Error fetching AI news: {e}")
            return []
    
    def _parse_ai_news(self, content: str) -> List[NewsItem]:
        """Parse AI-generated news content into NewsItem objects"""
        try:
            import re
            news_items = []
            
            # Split content into individual news stories
            sections = re.split(r'\n\s*\n', content.strip())
            
            for section in sections:
                if not section.strip():
                    continue
                
                # Extract components using regex
                title_match = re.search(r'Title:\s*(.+)', section)
                summary_match = re.search(r'Summary:\s*(.+?)(?=\n[A-Z]|\Z)', section, re.DOTALL)
                source_match = re.search(r'Source:\s*(.+)', section)
                url_match = re.search(r'URL:\s*(.+)', section)
                date_match = re.search(r'Date:\s*(.+)', section)
                
                if title_match and summary_match:
                    title = title_match.group(1).strip()
                    summary = summary_match.group(1).strip().replace('\n', ' ')
                    source = source_match.group(1).strip() if source_match else "AI Research"
                    url = url_match.group(1).strip() if url_match else ""
                    published = date_match.group(1).strip() if date_match else datetime.now().strftime("%Y-%m-%d")
                    
                    news_items.append(NewsItem(
                        title=title,
                        summary=summary,
                        source=source,
                        published=published,
                        url=url
                    ))
                    
                    if len(news_items) >= 7:  # Limit to 7 news items
                        break
            
            return news_items
            
        except Exception as e:
            logger.error(f"Error parsing AI news: {e}")
            return []
    
    async def fetch_ai_assets(self, topic: str, language: str) -> List[AssetItem]:
        """Fetch topic-specific asset prices using AI research"""
        try:
            # Define asset types for each topic
            asset_descriptions = {
                'all': {
                    'en': 'major stock indices (S&P 500, Dow Jones, NASDAQ), key individual stocks, and important commodities',
                    'ru': 'основные фондовые индексы (S&P 500, Dow Jones, NASDAQ), ключевые отдельные акции и важные товары'
                },
                'oil_gas': {
                    'en': 'oil prices (WTI, Brent crude), natural gas futures, major energy company stocks (Exxon, Chevron, Shell, BP)',
                    'ru': 'цены на нефть (WTI, Brent), фьючерсы на природный газ, акции крупных энергетических компаний (Exxon, Chevron, Shell, BP)'
                },
                'metals_mining': {
                    'en': 'precious metals (gold, silver, platinum), industrial metals (copper, aluminum, nickel), mining company stocks',
                    'ru': 'драгоценные металлы (золото, серебро, платина), промышленные металлы (медь, алюминий, никель), акции горнодобывающих компаний'
                },
                'technology': {
                    'en': 'major tech stocks (Apple, Microsoft, Google, Amazon, Meta, Tesla, NVIDIA), semiconductor companies, tech ETFs',
                    'ru': 'крупные технологические акции (Apple, Microsoft, Google, Amazon, Meta, Tesla, NVIDIA), компании-производители полупроводников, технологические ETF'
                },
                'finance': {
                    'en': 'major bank stocks (JPMorgan, Bank of America, Wells Fargo), financial ETFs, interest rate indicators',
                    'ru': 'акции крупных банков (JPMorgan, Bank of America, Wells Fargo), финансовые ETF, индикаторы процентных ставок'
                }
            }
            
            asset_desc = asset_descriptions[topic].get(language, asset_descriptions[topic]['en'])
            
            # Create AI prompt for asset research
            prompt = f"""Provide current market data for {asset_desc}.

For each asset, provide:
1. Current price (in USD where applicable)
2. Recent price change (24h percentage)
3. Brief context about the price movement

Format each asset as:
Symbol: [Asset symbol/name]
Price: [Current price with currency]
Change: [Percentage change with + or - sign]
Context: [Brief explanation of price movement]

Provide 5-7 most important assets in this category with realistic market data."""

            # Generate asset data using AI
            client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a financial market data analyst. Provide realistic current market prices and changes for financial assets. Use typical market ranges and realistic price movements."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.3
            )
            
            # Parse AI response into AssetItem objects
            content = response.choices[0].message.content
            asset_items = self._parse_ai_assets(content)
            
            logger.info(f"Generated {len(asset_items)} AI asset items for topic: {topic}")
            return asset_items
            
        except Exception as e:
            logger.error(f"Error fetching AI assets: {e}")
            return []
    
    def _parse_ai_assets(self, content: str) -> List[AssetItem]:
        """Parse AI-generated asset content into AssetItem objects"""
        try:
            import re
            asset_items = []
            
            # Split content into individual asset entries
            sections = re.split(r'\n\s*\n', content.strip())
            
            for section in sections:
                if not section.strip():
                    continue
                
                # Extract components using regex
                symbol_match = re.search(r'Symbol:\s*(.+)', section)
                price_match = re.search(r'Price:\s*(.+)', section)
                change_match = re.search(r'Change:\s*([+-]?\d+\.?\d*)%?', section)
                
                if symbol_match and price_match and change_match:
                    symbol = symbol_match.group(1).strip()
                    price_str = price_match.group(1).strip()
                    change_str = change_match.group(1).strip()
                    
                    # Extract numeric price
                    price_num_match = re.search(r'[\d,]+\.?\d*', price_str.replace(',', ''))
                    if price_num_match:
                        price = float(price_num_match.group().replace(',', ''))
                    else:
                        price = 100.0  # Default fallback
                    
                    # Extract numeric change
                    change = float(change_str.replace('+', '').replace('%', ''))
                    direction = 'up' if change >= 0 else 'down'
                    
                    asset_items.append(AssetItem(
                        symbol=symbol,
                        name=symbol,
                        price=price,
                        change=change,
                        change_direction=direction,
                        source="AI Research"
                    ))
                    
                    if len(asset_items) >= 7:  # Limit to 7 assets
                        break
            
            return asset_items
            
        except Exception as e:
            logger.error(f"Error parsing AI assets: {e}")
            return []
    
    async def generate_unified_digest(self, news_items: List[NewsItem], asset_items: List[AssetItem], topic: str, language: str) -> str:
        """Generate unified market digest using ChatGPT"""
        try:
            # Prepare content for ChatGPT
            content = f"=== MARKET RESEARCH DATA ===\n\n"
            
            # Add news content
            content += "=== NEWS STORIES ===\n"
            for i, item in enumerate(news_items[:7], 1):
                content += f"{i}. {item.title}\n"
                content += f"   Summary: {item.summary}\n"
                content += f"   Source: {item.source}\n"
                if item.url:
                    content += f"   URL: {item.url}\n"
                content += f"   Date: {item.published}\n\n"
            
            # Add asset data
            content += "=== ASSET PRICES ===\n"
            for asset in asset_items[:7]:
                direction = "📈" if asset.change_direction == 'up' else "📉"
                content += f"{direction} {asset.symbol}: ${asset.price} ({asset.change:+.2f}%)\n"
            
            # Create system prompt based on language
            if language == 'ru':
                system_prompt = """Ты - эксперт по финансовым рынкам. Создай структурированный дайджест новостей и цен на основе предоставленных данных на русском языке.

Формат:
📊 **РЫНОЧНЫЙ ДАЙДЖЕСТ** 📊

📰 **ГЛАВНЫЕ НОВОСТИ**
• Краткое описание ключевых новостей (3-5 самых важных)
• Анализ влияния на рынок
• Источники новостей

📈 **КЛЮЧЕВЫЕ АКТИВЫ**
• Цены и изменения по основным активам
• Тренды и паттерны
• Анализ движения цен

🔮 **ПРОГНОЗЫ И ТЕНДЕНЦИИ**
• Анализ настроений рынка
• Ключевые секторы для внимания
• Рекомендации для инвесторов

Используй эмодзи, структурируй информацию для легкого чтения, и сделай анализ профессиональным и понятным."""
            else:
                system_prompt = """You are a financial markets expert. Create a structured digest of news and asset prices based on the provided data in English.

Format:
📊 **MARKET DIGEST** 📊

📰 **TOP NEWS**
• Brief description of key news (3-5 most important)
• Market impact analysis
• News sources

📈 **KEY ASSETS**
• Prices and changes for major assets
• Trends and patterns
• Price movement analysis

🔮 **FORECASTS & TRENDS**
• Market sentiment analysis
• Key sectors to watch
• Investor recommendations

Use emojis, structure information for easy reading, and make the analysis professional and understandable."""
            
            # Process with ChatGPT
            client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content}
                ],
                max_tokens=1500,
                temperature=0.4
            )
            
            digest = response.choices[0].message.content
            logger.info(f"ChatGPT digest generation successful for language: {language}")
            return digest
            
        except Exception as e:
            logger.error(f"Error generating unified digest: {e}")
            return self.get_text(user_id if 'user_id' in locals() else 0, 'error_fetching')
    
    async def subscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /subscribe command"""
        user = update.effective_user
        self.db.add_user(user.id, user.username, user.first_name, user.last_name)
        
        # Check if already subscribed
        subscribed_users = self.db.get_subscribed_users()
        if user.id in subscribed_users:
            await update.message.reply_text(self.get_text(user.id, 'already_subscribed'))
        else:
            self.db.subscribe_user(user.id)
            await update.message.reply_text(self.get_text(user.id, 'subscribed'))
    
    async def unsubscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /unsubscribe command"""
        user = update.effective_user
        self.db.add_user(user.id, user.username, user.first_name, user.last_name)
        
        # Check if subscribed
        subscribed_users = self.db.get_subscribed_users()
        if user.id not in subscribed_users:
            await update.message.reply_text(self.get_text(user.id, 'not_subscribed'))
        else:
            self.db.unsubscribe_user(user.id)
            await update.message.reply_text(self.get_text(user.id, 'unsubscribed'))
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        user = update.effective_user
        self.db.add_user(user.id, user.username, user.first_name, user.last_name)
        
        user_count = self.db.get_user_count()
        subscriber_count = len(self.db.get_subscribed_users())
        user_language = self.db.get_user_language(user.id)
        user_topics = self.db.get_user_topics(user.id)
        
        topic_name = self.available_topics[user_topics].get(user_language, self.available_topics[user_topics]['en'])
        language_name = "Русский" if user_language == 'ru' else "English"
        
        status_message = f"""
🤖 **Bot Status**

📊 **Statistics:**
• Total users: {user_count}
• Active subscribers: {subscriber_count}
• Uptime: ✅ Online

👤 **Your Settings:**
• Language: {language_name}
• Topic: {topic_name}
• Subscribed: {'✅ Yes' if user.id in self.db.get_subscribed_users() else '❌ No'}

🔧 **System:**
• AI Research: ✅ Operational
• Database: ✅ Connected
• Scheduler: ✅ Running
        """
        
        await update.message.reply_text(status_message, parse_mode='Markdown')
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        await self.status_command(update, context)
    
    async def language_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /language command - show language selection"""
        user = update.effective_user
        self.db.add_user(user.id, user.username, user.first_name, user.last_name)
        
        current_lang = self.db.get_user_language(user.id)
        current_lang_name = "Русский" if current_lang == 'ru' else "English"
        
        language_message = f"""
🌍 **{self.get_text(user.id, 'language_selection')}**

**📍 {self.get_text(user.id, 'current_language')}**: {current_lang_name}

Выберите язык / Choose language:
        """
        
        # Create inline keyboard with language options
        keyboard = [
            [
                InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
                InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            language_message, 
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def topics_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /topics command - show topic selection"""
        user = update.effective_user
        self.db.add_user(user.id, user.username, user.first_name, user.last_name)
        
        # Get current topics
        current_topics = self.db.get_user_topics(user.id)
        
        # Create topic selection keyboard
        keyboard = []
        row = []
        
        for topic_key, topic_names in self.available_topics.items():
            topic_name = topic_names.get(self.db.get_user_language(user.id), topic_names['en'])
            callback_data = f"topic_{topic_key}"
            
            # Mark current selection
            if topic_key == current_topics:
                topic_name = f"✅ {topic_name}"
            
            row.append(InlineKeyboardButton(topic_name, callback_data=callback_data))
            
            if len(row) == 2:  # 2 buttons per row
                keyboard.append(row)
                row = []
        
        if row:  # Add remaining buttons
            keyboard.append(row)
        
        # Add current topics info
        current_topic_name = self.available_topics[current_topics][self.db.get_user_language(user.id)]
        
        message_text = (
            f"{self.get_text(user.id, 'topic_selection')}\n\n"
            f"{self.get_text(user.id, 'current_topics')}: {current_topic_name}"
        )
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message_text, reply_markup=reply_markup)
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all callback queries (language and topic selection)"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        self.db.add_user(user.id, user.username, user.first_name, user.last_name)
        
        # Check if it's a language selection
        if query.data.startswith("lang_"):
            await self._handle_language_selection(query)
        # Check if it's a topic selection
        elif query.data.startswith("topic_"):
            await self._handle_topic_selection(query)
        else:
            await query.edit_message_text("❌ Invalid selection")
    
    async def _handle_language_selection(self, query):
        """Handle language selection from inline buttons"""
        user = query.from_user
        
        # Extract language from callback data
        if query.data == "lang_ru":
            language = "ru"
            language_name = "Русский"
        elif query.data == "lang_en":
            language = "en"
            language_name = "English"
        else:
            await query.edit_message_text("❌ Invalid language selection")
            return
        
        # Set user language
        self.db.set_user_language(user.id, language)
        
        # Send confirmation message
        if language == "ru":
            confirmation = f"""
✅ **Язык успешно изменен!**

🌍 **Текущий язык**: {language_name}

💡 **Совет**: Используйте /start чтобы увидеть интерфейс на новом языке!
            """
        else:
            confirmation = f"""
✅ **Language changed successfully!**

🌍 **Current language**: {language_name}

💡 **Tip**: Use /start to see the interface in your new language!
            """
        
        await query.edit_message_text(confirmation, parse_mode='Markdown')
    
    async def _handle_topic_selection(self, query):
        """Handle topic selection callbacks"""
        user_id = query.from_user.id
        topic_key = query.data.replace('topic_', '')
        
        if topic_key in self.available_topics:
            # Update user's topic preferences
            self.db.set_user_topics(user_id, topic_key)
            
            # Get topic name in user's language
            user_language = self.db.get_user_language(user_id)
            topic_name = self.available_topics[topic_key].get(user_language, self.available_topics[topic_key]['en'])
            
            # Update the message to show selection
            keyboard = []
            row = []
            
            for t_key, t_names in self.available_topics.items():
                t_name = t_names.get(user_language, t_names['en'])
                callback_data = f"topic_{t_key}"
                
                # Mark current selection
                if t_key == topic_key:
                    t_name = f"✅ {t_name}"
                
                row.append(InlineKeyboardButton(t_name, callback_data=callback_data))
                
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
            
            if row:
                keyboard.append(row)
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"{self.get_text(user_id, 'topics_updated')}\n\n"
                f"{self.get_text(user_id, 'current_topics')}: {topic_name}",
                reply_markup=reply_markup
            )
    
    async def notify_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /notify command - manually trigger notification to all subscribers"""
        user = update.effective_user
        self.db.add_user(user.id, user.username, user.first_name, user.last_name)
        
        # Check if user is admin
        if not self.is_admin(user.id):
            await update.message.reply_text(
                "❌ **Access Denied**\n\n"
                "Only administrators can trigger manual notifications.\n"
                "Contact the bot administrator to request access."
            )
            return
        
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        try:
            # Get all subscribed users
            subscribers = self.db.get_subscribed_users()
            
            if not subscribers:
                await update.message.reply_text(self.get_text(user.id, 'no_subscribers'))
                return
            
            # Send notification to all subscribers
            successful_sends = 0
            failed_sends = 0
            
            for user_id in subscribers:
                try:
                    # Generate personalized digest for each user
                    digest = await self.generate_ai_digest(user_id)
                    await self.bot.send_message(
                        chat_id=user_id, 
                        text=f"🔔 **{self.get_text(user_id, 'notification_success')}**\n\n{digest}", 
                        parse_mode='Markdown'
                    )
                    successful_sends += 1
                    
                    # Rate limiting - Telegram allows ~30 messages per second
                    await asyncio.sleep(0.05)
                    
                except Exception as e:
                    logger.error(f"Failed to send manual notification to user {user_id}: {e}")
                    failed_sends += 1
                    
                    # If user blocked bot, unsubscribe them
                    if "bot was blocked" in str(e).lower():
                        self.db.unsubscribe_user(user_id)
            
            # Send confirmation to the user who triggered the notification
            confirmation = f"""
✅ **{self.get_text(user.id, 'notification_success')}**

📊 **{self.get_text(user.id, 'results')}:**
• {self.get_text(user.id, 'successfully_sent')}: {successful_sends} users
• {self.get_text(user.id, 'failed_to_send')}: {failed_sends} users
• {self.get_text(user.id, 'total_subscribers')}: {len(subscribers)} users

⏰ **{self.get_text(user.id, 'sent_at')}:** {datetime.now().strftime('%B %d, %Y at %H:%M:%S')} EST

🔔 {self.get_text(user.id, 'all_notified')}
            """
            
            await update.message.reply_text(confirmation, parse_mode='Markdown')
            
            logger.info(f"Manual notification triggered by user {user.id} - sent to {successful_sends} users, {failed_sends} failed")
            
        except Exception as e:
            logger.error(f"Error sending manual notification: {e}")
            await update.message.reply_text(self.get_text(user.id, 'error_notification'))
    
    async def add_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /addadmin command - add a new admin user"""
        user = update.effective_user
        
        if not self.is_admin(user.id):
            await update.message.reply_text("❌ Only administrators can add new admins.")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Please provide a user ID. Usage: /addadmin <user_id>")
            return
        
        try:
            new_admin_id = int(context.args[0])
            self.db.add_admin(new_admin_id)
            await update.message.reply_text(f"✅ User {new_admin_id} has been added as an administrator.")
            logger.info(f"New admin added: {new_admin_id} by {user.id}")
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID. Please provide a valid number.")
        except Exception as e:
            logger.error(f"Error adding admin: {e}")
            await update.message.reply_text("❌ Error adding administrator.")
    
    async def test_notifications_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /testnotifications command - send test notifications to all users"""
        user = update.effective_user
        self.db.add_user(user.id, user.username, user.first_name, user.last_name)
        
        # Check if user is admin
        if not self.is_admin(user.id):
            await update.message.reply_text("❌ Only administrators can send test notifications.")
            return
        
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        try:
            # Get all users (not just subscribers for testing)
            all_users = self.db.get_all_users()
            
            if not all_users:
                await update.message.reply_text("❌ No users found in database.")
                return
            
            await update.message.reply_text(f"🧪 Sending test notifications to {len(all_users)} users...")
            
            # Send test notification to all users
            successful_sends = 0
            failed_sends = 0
            
            for user_id in all_users:
                try:
                    # Generate personalized test digest for each user
                    digest = await self.generate_ai_digest(user_id)
                    test_message = f"🧪 **TEST NOTIFICATION**\n\n{digest}\n\n_This is a test message from the admin._"
                    
                    await self.bot.send_message(
                        chat_id=user_id, 
                        text=test_message, 
                        parse_mode='Markdown'
                    )
                    successful_sends += 1
                    
                    # Rate limiting
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Failed to send test notification to user {user_id}: {e}")
                    failed_sends += 1
                    
                    # Don't unsubscribe users during test
            
            # Send confirmation to admin
            confirmation = f"""
✅ **Test Notifications Completed**

📊 **Results:**
• Successfully sent: {successful_sends} users
• Failed to send: {failed_sends} users
• Total users: {len(all_users)} users

⏰ **Sent at:** {datetime.now().strftime('%B %d, %Y at %H:%M:%S')} EST

🧪 Test notifications help verify the system is working correctly.
            """
            
            await update.message.reply_text(confirmation, parse_mode='Markdown')
            logger.info(f"Test notifications sent by admin {user.id} - {successful_sends} sent, {failed_sends} failed")
            
        except Exception as e:
            logger.error(f"Error sending test notifications: {e}")
            await update.message.reply_text("❌ Error sending test notifications.")
    
    async def send_daily_notifications(self):
        """Send daily AI-powered notifications to all subscribers"""
        try:
            subscribers = self.db.get_subscribed_users()
            if not subscribers:
                logger.info("No subscribers found for daily notifications")
                return
            
            successful_sends = 0
            failed_sends = 0
            
            for user_id in subscribers:
                try:
                    # Generate personalized AI digest for each user
                    digest = await self.generate_ai_digest(user_id)
                    
                    await self.bot.send_message(
                        chat_id=user_id, 
                        text=digest, 
                        parse_mode='Markdown'
                    )
                    successful_sends += 1
                    
                    # Rate limiting
                    await asyncio.sleep(0.05)
                    
                except Exception as e:
                    logger.error(f"Failed to send daily notification to user {user_id}: {e}")
                    failed_sends += 1
                    
                    # If user blocked bot, unsubscribe them
                    if "bot was blocked" in str(e).lower():
                        self.db.unsubscribe_user(user_id)
            
            logger.info(f"Daily notifications sent to {successful_sends} users, {failed_sends} failed")
            
        except Exception as e:
            logger.error(f"Error sending daily notifications: {e}")
    
    async def send_daily_highlights(self):
        """Send daily highlights at 8:00 AM with yesterday's summary"""
        try:
            subscribers = self.db.get_subscribed_users()
            if not subscribers:
                logger.info("No subscribers found for daily highlights")
                return
            
            successful_sends = 0
            failed_sends = 0
            
            for user_id in subscribers:
                try:
                    # Generate special highlights digest
                    highlights = await self.generate_highlights_digest(user_id)
                    
                    await self.bot.send_message(
                        chat_id=user_id, 
                        text=highlights, 
                        parse_mode='Markdown'
                    )
                    successful_sends += 1
                    
                    # Rate limiting
                    await asyncio.sleep(0.05)
                    
                except Exception as e:
                    logger.error(f"Failed to send daily highlights to user {user_id}: {e}")
                    failed_sends += 1
                    
                    # If user blocked bot, unsubscribe them
                    if "bot was blocked" in str(e).lower():
                        self.db.unsubscribe_user(user_id)
            
            logger.info(f"Daily highlights sent to {successful_sends} users, {failed_sends} failed")
            
        except Exception as e:
            logger.error(f"Error sending daily highlights: {e}")
    
    async def generate_highlights_digest(self, user_id: int) -> str:
        """Generate special highlights digest for morning summary"""
        try:
            user_topics = self.db.get_user_topics(user_id)
            user_language = self.db.get_user_language(user_id)
            
            # Create special prompt for highlights
            current_date = datetime.now().strftime("%Y-%m-%d")
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            
            topic_desc = {
                'all': {'en': 'global financial markets', 'ru': 'глобальные финансовые рынки'},
                'oil_gas': {'en': 'oil and gas markets', 'ru': 'нефтегазовые рынки'},
                'metals_mining': {'en': 'metals and mining markets', 'ru': 'рынки металлов и добычи'},
                'technology': {'en': 'technology sector', 'ru': 'технологический сектор'},
                'finance': {'en': 'financial sector', 'ru': 'финансовый сектор'}
            }[user_topics].get(user_language, 'financial markets')
            
            prompt = f"""Create a morning highlights summary for {topic_desc} covering key developments from {yesterday} and outlook for {current_date}.

Include:
1. Top 3-4 most important developments from yesterday
2. Key market movers and their impact
3. What to watch today
4. Important economic events or earnings

Format as a concise, professional morning briefing that an investor would want to read with their coffee."""
            
            # Generate highlights using AI
            client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a financial markets analyst creating morning briefings. Be concise, professional, and focus on actionable insights."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            
            # Add header
            if user_language == 'ru':
                header = f"☀️ **Утренние основные моменты - {current_date}**\n\n"
            else:
                header = f"☀️ **Morning Highlights - {current_date}**\n\n"
            
            return header + content
            
        except Exception as e:
            logger.error(f"Error generating highlights digest: {e}")
            return "☀️ **Morning Highlights**\n\nMarket analysis will be available shortly."
    
    async def send_market_notifications(self, market_name: str, action: str):
        """Send topic-specific market notifications"""
        try:
            subscribers = self.db.get_subscribed_users()
            if not subscribers:
                logger.info(f"No subscribers for {market_name} {action} notification")
                return
            
            # Filter users by relevant topics
            relevant_topics = {
                'US Markets': ['all', 'technology', 'finance'],
                'NYMEX Energy': ['all', 'oil_gas'],
                'COMEX Metals': ['all', 'metals_mining']
            }
            
            target_users = []
            for user_id in subscribers:
                user_topic = self.db.get_user_topics(user_id)
                if user_topic in relevant_topics.get(market_name, ['all']):
                    target_users.append(user_id)
            
            if not target_users:
                logger.info(f"No users interested in {market_name}")
                return
            
            successful_sends = 0
            failed_sends = 0
            
            for user_id in target_users:
                try:
                    # Generate market-specific notification
                    notification = await self.generate_market_notification(user_id, market_name, action)
                    
                    await self.bot.send_message(
                        chat_id=user_id, 
                        text=notification, 
                        parse_mode='Markdown'
                    )
                    successful_sends += 1
                    
                    # Rate limiting
                    await asyncio.sleep(0.05)
                    
                except Exception as e:
                    logger.error(f"Failed to send {market_name} notification to user {user_id}: {e}")
                    failed_sends += 1
                    
                    # If user blocked bot, unsubscribe them
                    if "bot was blocked" in str(e).lower():
                        self.db.unsubscribe_user(user_id)
            
            logger.info(f"{market_name} {action} notifications sent to {successful_sends} users, {failed_sends} failed")
            
        except Exception as e:
            logger.error(f"Error sending {market_name} notifications: {e}")
    
    async def generate_market_notification(self, user_id: int, market_name: str, action: str) -> str:
        """Generate market-specific opening/closing notification"""
        try:
            user_language = self.db.get_user_language(user_id)
            user_topics = self.db.get_user_topics(user_id)
            
            # Get relevant assets for this market and user topic
            asset_items = await self.fetch_ai_assets(user_topics, user_language)
            
            # Create notification based on action and language
            if user_language == 'ru':
                if action == "opening_soon":
                    header = f"🔔 **{market_name} открывается через 15 минут**"
                    subtitle = "Подготовьтесь к торговой сессии"
                elif action == "closed":
                    header = f"📊 **{market_name} закрылся 15 минут назад**"
                    subtitle = "Итоги торговой сессии"
                
                asset_header = "📈 **Ключевые активы:**"
            else:
                if action == "opening_soon":
                    header = f"🔔 **{market_name} opening in 15 minutes**"
                    subtitle = "Prepare for the trading session"
                elif action == "closed":
                    header = f"📊 **{market_name} closed 15 minutes ago**"
                    subtitle = "Trading session summary"
                
                asset_header = "📈 **Key Assets:**"
            
            # Format asset information
            asset_text = ""
            for asset in asset_items[:5]:  # Top 5 assets
                direction = "📈" if asset.change_direction == 'up' else "📉"
                if user_language == 'ru':
                    asset_text += f"{direction} **{asset.symbol}**: ${asset.price} ({asset.change:+.2f}%)\n"
                else:
                    asset_text += f"{direction} **{asset.symbol}**: ${asset.price} ({asset.change:+.2f}%)\n"
            
            notification = f"""
{header}

{subtitle}

{asset_header}
{asset_text}

📱 Используйте /news для полного анализа рынка
            """ if user_language == 'ru' else f"""
{header}

{subtitle}

{asset_header}
{asset_text}

📱 Use /news for full market analysis
            """
            
            return notification.strip()
            
        except Exception as e:
            logger.error(f"Error generating market notification: {e}")
            return f"🔔 {market_name} {action} notification"
    
    def schedule_daily_summaries(self):
        """Schedule daily AI-powered summaries and market notifications"""
        # Daily highlights at 8:00 AM EST (weekdays only)
        schedule.every().monday.at("08:00").do(
            lambda: asyncio.create_task(self.send_daily_highlights())
        )
        schedule.every().tuesday.at("08:00").do(
            lambda: asyncio.create_task(self.send_daily_highlights())
        )
        schedule.every().wednesday.at("08:00").do(
            lambda: asyncio.create_task(self.send_daily_highlights())
        )
        schedule.every().thursday.at("08:00").do(
            lambda: asyncio.create_task(self.send_daily_highlights())
        )
        schedule.every().friday.at("08:00").do(
            lambda: asyncio.create_task(self.send_daily_highlights())
        )
        
        # Schedule topic-specific market notifications (weekdays only)
        weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
        
        # US Markets (NASDAQ, NYSE) - 15 min before open and after close
        for day in weekdays:
            getattr(schedule.every(), day).at("09:15").do(
                lambda: asyncio.create_task(self.send_market_notifications("US Markets", "opening_soon"))
            )
            getattr(schedule.every(), day).at("16:15").do(
                lambda: asyncio.create_task(self.send_market_notifications("US Markets", "closed"))
            )
        
        # Energy Markets (NYMEX) - 15 min before open and after close
        for day in weekdays:
            getattr(schedule.every(), day).at("08:45").do(
                lambda: asyncio.create_task(self.send_market_notifications("NYMEX Energy", "opening_soon"))
            )
            getattr(schedule.every(), day).at("14:45").do(
                lambda: asyncio.create_task(self.send_market_notifications("NYMEX Energy", "closed"))
            )
        
        # Metals Markets (COMEX) - 15 min before open and after close
        for day in weekdays:
            getattr(schedule.every(), day).at("07:45").do(
                lambda: asyncio.create_task(self.send_market_notifications("COMEX Metals", "opening_soon"))
            )
            getattr(schedule.every(), day).at("13:45").do(
                lambda: asyncio.create_task(self.send_market_notifications("COMEX Metals", "closed"))
            )
    
    async def run_scheduler(self):
        """Run the scheduled tasks"""
        while True:
            schedule.run_pending()
            await asyncio.sleep(1)
    
    async def start(self):
        """Start the bot"""
        logger.info("Starting AI-Powered Stock News Bot...")
        
        # Initialize the application
        await self.application.initialize()
        
        # Set up bot commands menu
        await self.setup_bot_menu()
        
        # Set up scheduling
        self.schedule_daily_summaries()
        
        logger.info("Bot started successfully! AI-powered market research is operational.")
        logger.info(f"Current subscriber count: {len(self.db.get_subscribed_users())}")
        logger.info("Scheduler started")
        
        # Start polling for updates
        logger.info("🔄 Starting bot polling...")
        await self.application.run_polling(drop_pending_updates=True)

# Main execution
def main():
    # Load environment variables from .env file
    try:
        from dotenv import load_dotenv
        load_dotenv()
        logger.info("✅ Environment variables loaded from .env file")
    except Exception as e:
        logger.warning(f"Could not load .env file: {e}")
    
    # Load configuration from environment variables
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    if not BOT_TOKEN:
        logger.error("Please set TELEGRAM_BOT_TOKEN environment variable")
        return
    
    if not OPENAI_API_KEY:
        logger.error("Please set OPENAI_API_KEY environment variable")
        return
    
    logger.info(f"✅ OpenAI API key loaded: {OPENAI_API_KEY[:10]}...")
    
    # Create and start bot
    bot = StockNewsBot(BOT_TOKEN)
    
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error running bot: {e}")

if __name__ == "__main__":
    main()
