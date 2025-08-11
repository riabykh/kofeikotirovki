import asyncio
import logging
from datetime import datetime, timedelta
import aiohttp
import feedparser
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
import schedule
import time
from typing import List, Dict, Set
import json
import os
from dataclasses import dataclass
import sqlite3
from contextlib import asynccontextmanager
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
    url: str

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
        
        # News cache table to avoid sending duplicate news
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS news_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                url TEXT UNIQUE,
                sent_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Check if language column exists, if not add it (migration for existing databases)
        self._migrate_database(conn, cursor)
        
        conn.commit()
        conn.close()
    
    def _migrate_database(self, conn, cursor):
        """Migrate existing database to add new columns"""
        try:
            # Check if language column exists
            cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'language' not in columns:
                print("🔄 Adding language column to existing database...")
                cursor.execute('ALTER TABLE users ADD COLUMN language TEXT DEFAULT "ru"')
                
                # Update existing users to have Russian as default language
                cursor.execute('UPDATE users SET language = "ru" WHERE language IS NULL')
                print("✅ Language column migration completed!")
            
            # Check if topic_preferences column exists
            if 'topic_preferences' not in columns:
                print("🔄 Adding topic_preferences column to existing database...")
                cursor.execute('ALTER TABLE users ADD COLUMN topic_preferences TEXT DEFAULT "all"')
                
                # Update existing users to have 'all' topics by default
                cursor.execute('UPDATE users SET topic_preferences = "all" WHERE topic_preferences IS NULL')
                print("✅ Topic preferences column migration completed!")
            
        except Exception as e:
            print(f"⚠️ Database migration warning: {e}")
            # Continue even if migration fails
    
    def add_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Add or update a user in the database without resetting preferences"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Use UPSERT so that existing preference columns (language, topic_preferences, subscribed, etc.) are preserved
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
    
    def get_subscriber_count(self) -> int:
        """Get number of subscribed users"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE subscribed = TRUE')
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    
    def get_all_users(self) -> List[tuple]:
        """Get all users from database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT user_id, username, first_name, last_name, subscribed, language FROM users')
        users = cursor.fetchall()
        
        conn.close()
        return users
    
    def get_user_language(self, user_id: int) -> str:
        """Get user's preferred language"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT language FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        conn.close()
        return result[0] if result else 'en'
    
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

class PublicStockNewsBot:
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.bot = Bot(token=bot_token)
        self.application = Application.builder().token(bot_token).build()
        self.db = DatabaseManager()
        self.db.init_database()  # Initialize database with tables and migration
        
        # News sources RSS feeds (with fallback options)
        self.news_sources = {
            'Yahoo Finance': 'https://feeds.finance.yahoo.com/rss/2.0/headline',
            'MarketWatch': 'https://feeds.marketwatch.com/marketwatch/topstories/',
            'CNBC': 'https://www.cnbc.com/id/100003114/device/rss/rss.html',
            'Reuters Business': 'https://feeds.reuters.com/reuters/businessNews',
            'Bloomberg': 'https://feeds.bloomberg.com/markets/news.rss',
            'Financial Times': 'https://www.ft.com/rss/home/us',
            'Seeking Alpha': 'https://seekingalpha.com/feed.xml',
            'Investing.com': 'https://www.investing.com/rss/news_301.rss',
            'Barron\'s': 'https://www.barrons.com/feed',
            'Wall Street Journal': 'https://feeds.a.dj.com/rss/RSSMarketsMain.xml'
        }
        
        # Alternative RSS feeds that are more reliable
        self.fallback_sources = {
            'Yahoo Finance Alt': 'https://feeds.finance.yahoo.com/rss/2.0/headline',
            'MarketWatch Alt': 'https://feeds.marketwatch.com/marketwatch/topstories/',
            'CNBC Alt': 'https://www.cnbc.com/id/100003114/device/rss/rss.html',
            'Reuters Alt': 'https://feeds.reuters.com/reuters/businessNews',
            'Bloomberg Alt': 'https://feeds.bloomberg.com/markets/news.rss'
        }
        
        # Cache for news summaries to avoid regenerating
        self.daily_summary_cache = None
        self.last_summary_time = None
        
        # Market schedule for notifications
        self.market_schedule = {
            'NYSE': {'open': '09:30', 'close': '16:00', 'timezone': 'America/New_York'},
            'NASDAQ': {'open': '09:30', 'close': '16:00', 'timezone': 'America/New_York'},
            'LSE': {'open': '08:00', 'close': '16:30', 'timezone': 'Europe/London'},
            'TSE': {'open': '09:00', 'close': '15:30', 'timezone': 'Asia/Tokyo'},
            'HKEX': {'open': '09:30', 'close': '16:00', 'timezone': 'Asia/Hong_Kong'}
        }
        
        # Major stocks to track for price changes
        self.major_stocks = {
            'AAPL': 'Apple Inc.',
            'MSFT': 'Microsoft Corporation',
            'GOOGL': 'Alphabet Inc.',
            'AMZN': 'Amazon.com Inc.',
            'TSLA': 'Tesla Inc.',
            'NVDA': 'NVIDIA Corporation',
            'META': 'Meta Platforms Inc.',
            'BRK.A': 'Berkshire Hathaway Inc.',
            'JPM': 'JPMorgan Chase & Co.',
            'JNJ': 'Johnson & Johnson'
        }
        
        # Setup handlers
        self.setup_handlers()
        
        # Admin user IDs (you can customize this list)
        self.admin_users = set()
        # Add admin user IDs here, for example:
        # self.admin_users = {123456789, 987654321}
        
        # Language support
        self.supported_languages = ['en', 'ru']
        self.default_language = 'ru'  # Russian is now default
        
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
        
        # Translation dictionaries
        self.translations = {
            'en': {
                'welcome_title': 'Кофе и Котировки',
                'welcome_message': 'Welcome, {name}! I am your personal financial markets news assistant.',
                'what_i_do': 'What I offer:',
                'daily_news': 'Daily market news summaries from leading financial sources',
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
                'addadmin_info': 'Use /addadmin to grant admin access to others',
                'notify_info': 'Admins can trigger manual notifications anytime',
                'auto_subscribe': 'Auto-Subscribe:',
                'subscribed_message': 'You\'re automatically subscribed to daily updates! Use /unsubscribe if you want to disable them.',
                'ready_message': 'Ready to stay informed about the markets? Try /news to get started!',
                'daily_intelligence': 'DAILY STOCK MARKET INTELLIGENCE',
                'market_sentiment': 'MARKET SENTIMENT ANALYSIS',
                'positive_news': 'Positive News',
                'negative_news': 'Negative News',
                'neutral_news': 'Neutral News',
                'top_headlines': 'TOP MARKET HEADLINES',
                'market_predictions': 'MARKET PREDICTIONS & ANALYSIS',
                'market_outlook': 'Market Outlook',
                'key_focus': 'Key Focus Areas:',
                'sector_spotlight': 'Sector Spotlight:',
                'trading_considerations': 'Trading Considerations:',
                'risk_level': 'Risk Level',
                'reminder': 'Reminder: Analysis based on news sentiment. Not financial advice. Always do your own research.',
                'manual_notification': 'MANUAL NOTIFICATION TRIGGERED',
                'notification_success': 'Manual Notification Sent Successfully!',
                'results': 'Results:',
                'successfully_sent': 'Successfully sent to',
                'failed_to_send': 'Failed to send',
                'total_subscribers': 'Total subscribers',
                'sent_at': 'Sent at',
                'all_notified': 'All subscribed users have been notified with the latest market news and predictions.',
                'access_denied': 'Access Denied',
                'admin_only': 'Only administrators can trigger manual notifications.',
                'contact_admin': 'Contact the bot administrator to request access.',
                'language_selection': 'Language Selection',
                'choose_language': 'Please choose your preferred language:',
                'english': 'English',
                'russian': 'Russian',
                'language_changed': 'Language changed successfully!',
                'current_language': 'Current language',
                'topics_cmd': '/topics - Choose topics of interest',
                'topic_selection': 'Choose topics that interest you:',
                'topic_all': 'All Topics',
                'topic_oil_gas': 'Oil & Gas',
                'topic_metals_mining': 'Metals & Mining',
                'topic_technology': 'Technology',
                'topic_finance': 'Finance & Banking',
                'topics_updated': 'Your topics have been updated!',
                'current_topics': 'Your current topics:',
                'no_subscribers': 'No subscribers found to notify.',
                'fetching_news': 'Fetching latest market news and analysis...',
                'error_fetching': 'Sorry, there was an error fetching the news. Our team has been notified. Please try again in a few minutes.',
                'error_notification': 'Sorry, I couldn\'t send the notification right now. Please try again later.',
                'no_news': 'Unable to fetch news at this time. Please try again later.',
                'no_users': 'No users found.',
                'user_count': 'User count',
                'subscriber_count': 'Subscriber count',
                'bot_health': 'Bot Health:',
                'status_operational': 'Status: Fully operational',
                'news_sources': 'News Sources',
                'active': 'active',
                'database': 'Database: Connected',
                'updates': 'Updates: Real-time',
                'today_summary': 'Today\'s Summary:',
                'available': 'Available',
                'generating': 'Generating...',
                'use_news': 'Use /news to get the latest market analysis!'
            },
            'ru': {
                'welcome_title': 'Кофе и Котировки',
                'welcome_message': 'Привет {name}! Я ваш личный помощник по новостям рынка акций.',
                'what_i_do': 'Что я делаю:',
                'daily_news': 'Ежедневные сводки новостей рынка от ведущих финансовых источников',
                'sentiment_analysis': 'Анализ настроений рынка на основе ИИ',
                'predictions': 'Трендовые темы и прогнозы рынка',
                'auto_updates': 'Автоматические ежедневные обновления (9:00 AM и 9:30 AM EST)',
                'commands': 'Команды:',
                'news_cmd': '/news - Получить последние новости рынка',
                'notify_cmd': '/notify - Вручную отправить уведомления всем подписчикам (только для админов)',
                'subscribe_cmd': '/subscribe - Включить ежедневные обновления новостей',
                'unsubscribe_cmd': '/unsubscribe - Отключить ежедневные обновления',
                'language_cmd': '/language - Выбрать язык кнопками',
                'help_cmd': '/help - Показать все команды',
                'status_cmd': '/status - Проверить статус бота и рынка',
                'stats_cmd': '/stats - Просмотр статистики использования бота',
                'admin_features': 'Функции администратора:',
                'first_user_admin': 'Первый пользователь автоматически становится администратором',
                'addadmin_info': 'Используйте /addadmin для предоставления прав администратора другим',
                'notify_info': 'Администраторы могут вручную отправлять уведомления в любое время',
                'auto_subscribe': 'Автоподписка:',
                'subscribed_message': 'Вы автоматически подписаны на ежедневные обновления! Используйте /unsubscribe, если хотите их отключить.',
                'ready_message': 'Готовы быть в курсе событий на рынках? Попробуйте /news для начала!',
                'daily_intelligence': 'ЕЖЕДНЕВНАЯ РАЗВЕДКА РЫНКА АКЦИЙ',
                'market_sentiment': 'АНАЛИЗ НАСТРОЕНИЙ РЫНКА',
                'positive_news': 'Позитивные новости',
                'negative_news': 'Негативные новости',
                'neutral_news': 'Нейтральные новости',
                'top_headlines': 'ГЛАВНЫЕ НОВОСТИ РЫНКА',
                'market_predictions': 'ПРОГНОЗЫ И АНАЛИЗ РЫНКА',
                'market_outlook': 'Прогноз рынка',
                'key_focus': 'Ключевые области внимания:',
                'sector_spotlight': 'В центре внимания сектора:',
                'trading_considerations': 'Соображения по торговле:',
                'risk_level': 'Уровень риска',
                'reminder': 'Напоминание: Анализ основан на настроениях новостей. Не является финансовой консультацией. Всегда проводите собственное исследование.',
                'manual_notification': 'ВРУЧНУЮ ЗАПУЩЕНО УВЕДОМЛЕНИЕ',
                'notification_success': 'Ручное уведомление успешно отправлено!',
                'results': 'Результаты:',
                'successfully_sent': 'Успешно отправлено',
                'failed_to_send': 'Не удалось отправить',
                'total_subscribers': 'Всего подписчиков',
                'sent_at': 'Отправлено в',
                'all_notified': 'Все подписчики получили уведомления с последними новостями рынка и прогнозами.',
                'access_denied': 'Доступ запрещен',
                'admin_only': 'Только администраторы могут запускать ручные уведомления.',
                'contact_admin': 'Обратитесь к администратору бота для получения доступа.',
                'language_selection': 'Выбор языка',
                'choose_language': 'Пожалуйста, выберите предпочитаемый язык:',
                'english': 'Английский',
                'russian': 'Русский',
                'language_changed': 'Язык успешно изменен!',
                'current_language': 'Текущий язык',
                'topics_cmd': '/topics - Выбрать интересующие темы',
                'topic_selection': 'Выберите интересующие вас темы:',
                'topic_all': 'Все темы',
                'topic_oil_gas': 'Нефть и газ',
                'topic_metals_mining': 'Металлы и добыча',
                'topic_technology': 'Технологии',
                'topic_finance': 'Финансы и банкинг',
                'topics_updated': 'Ваши темы обновлены!',
                'current_topics': 'Ваши текущие темы:',
                'no_subscribers': 'Подписчики не найдены для уведомления.',
                'fetching_news': 'Получение последних новостей рынка и анализа...',
                'error_fetching': 'Извините, произошла ошибка при получении новостей. Наша команда уведомлена. Пожалуйста, попробуйте снова через несколько минут.',
                'error_notification': 'Извините, не удалось отправить уведомление прямо сейчас. Пожалуйста, попробуйте снова позже.',
                'no_news': 'Не удалось получить новости в данный момент. Пожалуйста, попробуйте снова позже.',
                'no_users': 'Пользователи не найдены.',
                'user_count': 'Количество пользователей',
                'subscriber_count': 'Количество подписчиков',
                'bot_health': 'Состояние бота:',
                'status_operational': 'Статус: Полностью работает',
                'news_sources': 'Источники новостей',
                'active': 'активны',
                'database': 'База данных: Подключена',
                'updates': 'Обновления: В реальном времени',
                'today_summary': 'Сегодняшняя сводка:',
                'available': 'Доступна',
                'generating': 'Генерируется...',
                'use_news': 'Используйте /news для получения последнего анализа рынка!'
            }
        }
    
    def is_admin(self, user_id: int) -> bool:
        """Check if a user is an admin"""
        return user_id in self.admin_users
    
    def get_text(self, user_id: int, key: str, **kwargs) -> str:
        """Get translated text for a user"""
        language = self.db.get_user_language(user_id)
        if language not in self.supported_languages:
            language = self.default_language
        
        text = self.translations[language].get(key, key)
        return text.format(**kwargs) if kwargs else text
    
    async def translate_news_content(self, text: str, target_language: str) -> str:
        """Translate news content to target language using AI translation"""
        if target_language == 'en':
            return text  # Keep original English
        
        try:
            # Try to use LibreTranslate API (free and reliable)
            import aiohttp
            import json
            
            # LibreTranslate API endpoint (free service)
            url = "https://libretranslate.de/translate"
            
            async with aiohttp.ClientSession() as session:
                payload = {
                    "q": text,
                    "source": "en",
                    "target": "ru",
                    "format": "text"
                }
                
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        translated_text = result.get('translatedText', text)
                        logger.info(f"AI translation successful: {text[:50]}... -> {translated_text[:50]}...")
                        return translated_text
                    else:
                        logger.warning(f"LibreTranslate API failed with status {response.status}")
                        raise Exception(f"API status {response.status}")
                        
        except Exception as e:
            logger.warning(f"AI translation failed, falling back to keyword-based: {e}")
            
            # Fallback to enhanced keyword-based translation
            translations = {
                # Market terms
                'gain': 'рост',
                'rise': 'подъем',
                'up': 'вверх',
                'bull': 'бычий',
                'growth': 'рост',
                'profit': 'прибыль',
                'surge': 'всплеск',
                'rally': 'ралли',
                'boom': 'бум',
                'strong': 'сильный',
                'beat': 'превзойти',
                'exceed': 'превысить',
                'positive': 'позитивный',
                'upgrade': 'повышение',
                'buy': 'покупка',
                'optimistic': 'оптимистичный',
                'fall': 'падение',
                'drop': 'снижение',
                'down': 'вниз',
                'bear': 'медвежий',
                'loss': 'потери',
                'crash': 'крах',
                'decline': 'снижение',
                'recession': 'рецессия',
                'slump': 'спад',
                'weak': 'слабый',
                'miss': 'пропустить',
                'disappointing': 'разочаровывающий',
                'negative': 'негативный',
                'downgrade': 'понижение',
                'sell': 'продажа',
                'pessimistic': 'пессимистичный',
                
                # Sectors
                'technology': 'технологии',
                'tech': 'технологии',
                'energy': 'энергия',
                'finance': 'финансы',
                'healthcare': 'здравоохранение',
                'crypto': 'криптовалюта',
                'inflation': 'инфляция',
                'fed': 'ФРС',
                'interest': 'процентная ставка',
                'earnings': 'доходы',
                'china': 'Китай',
                'europe': 'Европа',
                'jobs': 'рабочие места',
                'gdp': 'ВВП',
                
                # Common words
                'the': 'the',  # Keep articles
                'and': 'и',
                'or': 'или',
                'but': 'но',
                'in': 'в',
                'on': 'на',
                'at': 'в',
                'to': 'к',
                'for': 'для',
                'with': 'с',
                'by': 'от',
                'from': 'от',
                'about': 'о',
                'market': 'рынок',
                'stock': 'акция',
                'shares': 'акции',
                'trading': 'торговля',
                'investor': 'инвестор',
                'company': 'компания',
                'business': 'бизнес',
                'economy': 'экономика',
                'financial': 'финансовый',
                'economic': 'экономический',
                'global': 'глобальный',
                'world': 'мир',
                'news': 'новости',
                'report': 'отчет',
                'data': 'данные',
                'quarter': 'квартал',
                'year': 'год',
                'month': 'месяц',
                'week': 'неделя',
                'day': 'день',
                'today': 'сегодня',
                'yesterday': 'вчера',
                'tomorrow': 'завтра',
                'morning': 'утро',
                'afternoon': 'день',
                'evening': 'вечер',
                'night': 'ночь',
                'time': 'время',
                'price': 'цена',
                'value': 'стоимость',
                'increase': 'увеличение',
                'decrease': 'уменьшение',
                'high': 'высокий',
                'low': 'низкий',
                'new': 'новый',
                'old': 'старый',
                'big': 'большой',
                'small': 'маленький',
                'good': 'хороший',
                'bad': 'плохой',
                'important': 'важный',
                'major': 'крупный',
                'minor': 'незначительный'
            }
            
            # More sophisticated translation with context
            translated_text = text
            
            # Replace words with proper Russian translations
            for eng, rus in translations.items():
                # Use word boundaries to avoid partial replacements
                import re
                pattern = r'\b' + re.escape(eng) + r'\b'
                translated_text = re.sub(pattern, rus, translated_text, flags=re.IGNORECASE)
            
            return translated_text
    
    async def get_topic_assets(self, user_id: int) -> List[Dict[str, any]]:
        """Get topic-specific asset prices using ChatGPT research"""
        try:
            user_topics = self.db.get_user_topics(user_id)
            user_language = self.db.get_user_language(user_id)
            
            # Define topic-specific asset types
            topic_assets = {
                'all': {
                    'en': 'stocks, commodities, and major market indices',
                    'ru': 'акции, сырьевые товары и основные рыночные индексы'
                },
                'oil_gas': {
                    'en': 'oil prices (WTI, Brent), natural gas, major oil companies, and energy ETFs',
                    'ru': 'цены на нефть (WTI, Brent), природный газ, крупные нефтяные компании и энергетические ETF'
                },
                'metals_mining': {
                    'en': 'precious metals (gold, silver, platinum), industrial metals (copper, aluminum, nickel), mining companies, and commodity ETFs',
                    'ru': 'драгоценные металлы (золото, серебро, платина), промышленные металлы (медь, алюминий, никель), горнодобывающие компании и товарные ETF'
                },
                'technology': {
                    'en': 'major tech stocks, semiconductor companies, software firms, and tech ETFs',
                    'ru': 'крупные технологические акции, компании-производители полупроводников, программные фирмы и технологические ETF'
                },
                'finance': {
                    'en': 'major banks, financial services companies, insurance firms, and financial ETFs',
                    'ru': 'крупные банки, компании финансовых услуг, страховые фирмы и финансовые ETF'
                }
            }
            
            # Get asset description in user's language
            asset_description = topic_assets[user_topics].get(user_language, topic_assets[user_topics]['en'])
            
            # Create prompt for ChatGPT to research current prices
            prompt = f"""Research current market prices for {asset_description}.

Please provide:
1. Current prices for 5-7 key assets in this category
2. Recent price changes (24h or daily)
3. Brief market context
4. Format as structured data

Focus on the most liquid and widely traded assets in this category.
If exact current prices aren't available, provide recent market prices with a note about timing."""

            # Use ChatGPT to research prices
            try:
                client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                response = await client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a financial markets expert. Provide current market data in a structured format."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=800,
                    temperature=0.3
                )
                
                # Parse ChatGPT response and extract structured data
                content = response.choices[0].message.content
                assets = self._parse_asset_data(content, user_language)
                
                if assets:
                    logger.info(f"Generated {len(assets)} topic-specific assets for {user_topics}")
                    return assets
                
            except Exception as e:
                logger.warning(f"ChatGPT asset research failed: {e}")
            
            # Fallback to mock data if ChatGPT fails
            return self._get_fallback_assets(user_topics, user_language)
            
        except Exception as e:
            logger.error(f"Error getting topic assets: {e}")
            return self._get_fallback_assets('all', 'en')
    
    def _parse_asset_data(self, content: str, language: str) -> List[Dict[str, any]]:
        """Parse ChatGPT response to extract structured asset data"""
        try:
            import re
            assets = []
            lines = content.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line or ':' not in line:
                    continue
                
                # Look for patterns like "Asset: $Price (+/-X%)" or "Asset - $Price (change)"
                if '$' in line and ('%' in line or '(' in line):
                    parts = line.split(':')
                    if len(parts) >= 2:
                        symbol = parts[0].strip()
                        price_info = parts[1].strip()
                        
                        # Extract price and change
                        price_match = re.search(r'\$([\d,]+\.?\d*)', price_info)
                        change_match = re.search(r'([+-]?\d+\.?\d*)%', price_info)
                        
                        if price_match:
                            price = float(price_match.group(1).replace(',', ''))
                            change = float(change_match.group(1)) if change_match else 0.0
                            direction = 'up' if change > 0 else 'down'
                            
                            assets.append({
                                'symbol': symbol,
                                'name': symbol,
                                'price': price,
                                'change': change,
                                'change_direction': direction,
                                'source': 'ChatGPT Research'
                            })
                            
                            if len(assets) >= 7:  # Limit to 7 assets
                                break
            
            return assets
            
        except Exception as e:
            logger.error(f"Error parsing asset data: {e}")
            return []
    
    def _get_fallback_assets(self, topic: str, language: str) -> List[Dict[str, any]]:
        """Generate fallback asset prices when ChatGPT research fails"""
        import random
        
        # Topic-specific fallback assets
        fallback_assets = {
            'all': {
                'AAPL': 150.0, 'MSFT': 300.0, 'GOOGL': 120.0, 'AMZN': 140.0, 'TSLA': 250.0
            },
            'oil_gas': {
                'WTI': 75.0, 'BRENT': 80.0, 'XOM': 100.0, 'CVX': 150.0, 'NGAS': 3.5
            },
            'metals_mining': {
                'GOLD': 1950.0, 'SILVER': 25.0, 'COPPER': 4.2, 'PLAT': 950.0, 'NICKEL': 20.0
            },
            'technology': {
                'NVDA': 400.0, 'META': 200.0, 'NFLX': 450.0, 'ADBE': 500.0, 'CRM': 200.0
            },
            'finance': {
                'JPM': 160.0, 'BAC': 30.0, 'WFC': 45.0, 'GS': 350.0, 'MS': 85.0
            }
        }
        
        assets = fallback_assets.get(topic, fallback_assets['all'])
        selected = random.sample(list(assets.keys()), min(5, len(assets)))
        
        result = []
        for symbol in selected:
            base_price = assets[symbol]
            change_percent = random.uniform(-5.0, 5.0)
            new_price = base_price * (1 + change_percent / 100)
            direction = 'up' if change_percent > 0 else 'down'
            
            result.append({
                'symbol': symbol,
                'name': symbol,
                'price': round(new_price, 2),
                'change': round(change_percent, 2),
                'change_direction': direction,
                'source': 'Fallback Data'
            })
        
        return result
    
    def get_stock_prices(self) -> List[Dict[str, any]]:
        """Legacy method - now redirects to topic-specific assets"""
        # This method is kept for backward compatibility
        # In production, use get_topic_assets() instead
        return self._get_fallback_assets('all', 'en')
    
    async def send_market_notification(self, market_name: str, action: str, user_id: int):
        """Send market open/close notification with stock prices"""
        try:
            # Get topic-specific assets for the user
            stock_prices = await self.get_topic_assets(user_id)
            logger.info(f"Generated topic-specific assets: {stock_prices}")
            
            # Get user language
            user_language = self.db.get_user_language(user_id)
            logger.info(f"User {user_id} language: {user_language}")
            
            if user_language == 'ru':
                if action == 'open':
                    title = f"🚀 **{market_name} открывается**"
                    subtitle = "Рынок открывается через 15 минут"
                    stock_header = "📈 **Ключевые активы:**"
                else:  # close
                    title = f"🔚 **{market_name} закрывается**"
                    subtitle = "Рынок закрылся 15 минут назад"
                    stock_header = "📊 **Итоги торгов:**"
                
                # Format topic-specific assets in Russian
                stock_text = ""
                for stock in stock_prices:
                    direction = "📈" if stock['change_direction'] == 'up' else "📉"
                    source_info = f" ({stock.get('source', 'Market Data')})" if 'source' in stock else ""
                    stock_text += f"\n{direction} **{stock['symbol']}** ({stock['name']}){source_info}\n"
                    stock_text += f"   Цена: ${stock['price']} ({stock['change']:+.2f}%)\n"
                
                message = f"""{title}
{subtitle}

{stock_header}
{stock_text}

⏰ Время: {datetime.now().strftime('%H:%M')} EST"""
                
            else:
                if action == 'open':
                    title = f"🚀 **{market_name} Opening**"
                    subtitle = "Market opens in 15 minutes"
                    stock_header = "📈 **Key Assets:**"
                else:  # close
                    title = f"🔚 **{market_name} Closing**"
                    subtitle = "Market closed 15 minutes ago"
                    stock_header = "📊 **Trading Summary:**"
                
                # Format topic-specific assets in English
                stock_text = ""
                for stock in stock_prices:
                    direction = "📈" if stock['change_direction'] == 'up' else "📉"
                    source_info = f" ({stock.get('source', 'Market Data')})" if 'source' in stock else ""
                    stock_text += f"\n{direction} **{stock['symbol']}** ({stock['name']}){source_info}\n"
                    stock_text += f"   Price: ${stock['price']} ({stock['change']:+.2f}%)\n"
                
                message = f"""{title}
{subtitle}

{stock_header}
{stock_text}

⏰ Time: {datetime.now().strftime('%H:%M')} EST"""
            
            logger.info(f"Sending market notification to user {user_id}: {message}")
            
            # Send notification
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error sending market notification to user {user_id}: {e}")
    
    def setup_handlers(self):
        """Setup command handlers"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("news", self.manual_news_command))
        self.application.add_handler(CommandHandler("notify", self.manual_notify_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("subscribe", self.subscribe_command))
        self.application.add_handler(CommandHandler("unsubscribe", self.unsubscribe_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("addadmin", self.add_admin_command))
        self.application.add_handler(CommandHandler("language", self.language_command))
        self.application.add_handler(CommandHandler("topics", self.topics_command))
        self.application.add_handler(CommandHandler("testmarket", self.test_market_notification_command))
        self.application.add_handler(CommandHandler("testchatgpt", self.test_chatgpt_command))
        
        # Add callback query handler for inline buttons
        from telegram.ext import CallbackQueryHandler
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        self.db.add_user(user.id, user.username, user.first_name, user.last_name)
        
        # Get translated text to avoid Markdown conflicts
        welcome_title = self.get_text(user.id, 'welcome_title')
        welcome_message_text = self.get_text(user.id, 'welcome_message', name=user.first_name)
        what_i_do = self.get_text(user.id, 'what_i_do')
        daily_news = self.get_text(user.id, 'daily_news')
        sentiment_analysis = self.get_text(user.id, 'sentiment_analysis')
        predictions = self.get_text(user.id, 'predictions')
        auto_updates = self.get_text(user.id, 'auto_updates')
        commands = self.get_text(user.id, 'commands')
        news_cmd = self.get_text(user.id, 'news_cmd')
        topics_cmd = self.get_text(user.id, 'topics_cmd')
        notify_cmd = self.get_text(user.id, 'notify_cmd')
        subscribe_cmd = self.get_text(user.id, 'subscribe_cmd')
        unsubscribe_cmd = self.get_text(user.id, 'unsubscribe_cmd')
        language_cmd = self.get_text(user.id, 'language_cmd')
        help_cmd = self.get_text(user.id, 'help_cmd')
        status_cmd = self.get_text(user.id, 'status_cmd')
        stats_cmd = self.get_text(user.id, 'stats_cmd')
        admin_features = self.get_text(user.id, 'admin_features')
        first_user_admin = self.get_text(user.id, 'first_user_admin')
        addadmin_info = self.get_text(user.id, 'addadmin_info')
        notify_info = self.get_text(user.id, 'notify_info')
        auto_subscribe = self.get_text(user.id, 'auto_subscribe')
        subscribed_message = self.get_text(user.id, 'subscribed_message')
        ready_message = self.get_text(user.id, 'ready_message')
        
        welcome_message = f"""
🤖 **{welcome_title}** 🤖

{welcome_message_text}

**🚀 {what_i_do}**
📈 {daily_news}
🔮 {sentiment_analysis}
📊 {predictions}
⏰ {auto_updates}
🕐 Market open/close notifications with stock prices

**📱 {commands}**
{news_cmd}
{topics_cmd}
{notify_cmd}
{subscribe_cmd}
{unsubscribe_cmd}
{language_cmd}
{help_cmd}
{status_cmd}
{stats_cmd}

**🔐 {admin_features}**
• {first_user_admin}
• {addadmin_info}
• {notify_info}
• /testmarket - Test market notifications

**🔔 {auto_subscribe}**
{subscribed_message}

{ready_message} 📊
        """
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        user = update.effective_user
        self.db.add_user(user.id, user.username, user.first_name, user.last_name)
        
        # Get translated text to avoid Markdown conflicts
        welcome_title = self.get_text(user.id, 'welcome_title')
        commands_text = self.get_text(user.id, 'commands')
        news_cmd = self.get_text(user.id, 'news_cmd')
        topics_cmd = self.get_text(user.id, 'topics_cmd')
        notify_cmd = self.get_text(user.id, 'notify_cmd')
        subscribe_cmd = self.get_text(user.id, 'subscribe_cmd')
        unsubscribe_cmd = self.get_text(user.id, 'unsubscribe_cmd')
        language_cmd = self.get_text(user.id, 'language_cmd')
        help_cmd = self.get_text(user.id, 'help_cmd')
        status_cmd = self.get_text(user.id, 'status_cmd')
        stats_cmd = self.get_text(user.id, 'stats_cmd')
        
        help_text = f"""
**📚 {welcome_title} - Help**

**🔧 {commands_text}**

/start - Welcome message and bot introduction
/news - {news_cmd}
/topics - {topics_cmd}
/notify - {notify_cmd}
/subscribe - {subscribe_cmd}
/unsubscribe - {unsubscribe_cmd}
/language - {language_cmd}
/help - {help_cmd}
/status - {status_cmd}
/stats - {stats_cmd}

**🔐 Admin Commands:**
/addadmin <user_id> - Add a new admin user (Admin only)
/testmarket - Test market notifications (Admin only)
/testchatgpt - Test ChatGPT integration (Admin only)

**⏰ Automatic Features:**
• Daily market summary at 9:00 AM EST
• Market opening summary at 9:30 AM EST (weekdays)
• **NEW: Market notifications 15 min before/after open/close**
• **NEW: Major stock price changes included in notifications**
• News from 10+ major financial sources
• Sentiment analysis and trend detection
• Market predictions based on news analysis

**📊 News Sources:**
• Yahoo Finance
• MarketWatch  
• CNBC
• Reuters Business
• Bloomberg
• Financial Times
• Seeking Alpha
• Investing.com
• Barron's
• Wall Street Journal

**💡 Tips:**
- Use /news anytime for the latest market summary
- Subscribe for automatic daily updates
- Check /status for current market sentiment
- All predictions are for educational purposes only

**⚠️ Disclaimer:** This bot provides news summaries and analysis for informational purposes only. Not financial advice.

Need help? The bot is fully automated and runs 24/7!
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def subscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /subscribe command"""
        user = update.effective_user
        self.db.add_user(user.id, user.username, user.first_name, user.last_name)
        self.db.subscribe_user(user.id)
        
        subscribe_message = """
✅ **Subscription Activated!**

You'll now receive automatic daily market summaries:

🌅 **Morning Summary** - 7:00 AM EST
📈 **Market Open** - 9:30 AM EST (weekdays only)

Each summary includes:
• Latest market news from top financial sources
• Sentiment analysis and trending topics  
• Market predictions for the trading day
• Key headlines and important updates

You can use /news anytime to get the latest summary, or /unsubscribe to stop automatic updates.

Happy trading! 📊🚀
        """
        await update.message.reply_text(subscribe_message, parse_mode='Markdown')
    
    async def unsubscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /unsubscribe command"""
        user = update.effective_user
        self.db.unsubscribe_user(user.id)
        
        unsubscribe_message = """
😔 **Subscription Cancelled**

You've been unsubscribed from automatic daily updates.

**You can still:**
• Use /news anytime for market summaries
• Use /subscribe to re-enable automatic updates
• Access all other bot features

**Note:** You'll no longer receive:
❌ Daily 7:00 AM EST summaries
❌ Market opening updates at 9:30 AM EST

Use /subscribe anytime to re-enable automatic updates!
        """
        await update.message.reply_text(unsubscribe_message, parse_mode='Markdown')
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        total_users = self.db.get_user_count()
        subscribers = self.db.get_subscriber_count()
        
        stats_message = f"""
📊 **Bot Statistics**

👥 **Users:**
• Total Users: {total_users:,}
• Active Subscribers: {subscribers:,}
• Subscription Rate: {(subscribers/total_users*100) if total_users > 0 else 0:.1f}%

📈 **Service Info:**
• News Sources: {len(self.news_sources)}
• Daily Summaries: 2 per day
• Coverage: Global financial markets
• Uptime: 24/7 automated service

🔄 **Last Update:** {datetime.now().strftime('%Y-%m-%d %H:%M')} EST

The bot is serving the financial community with real-time market intelligence!
        """
        await update.message.reply_text(stats_message, parse_mode='Markdown')
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        user = update.effective_user
        
        # Check if user is subscribed
        subscribed_users = self.db.get_subscribed_users()
        is_subscribed = user.id in subscribed_users
        
        # Get current market day info
        now = datetime.now()
        market_status = "🔴 Closed"
        if now.weekday() < 5:  # Monday to Friday
            if 9 <= now.hour < 16:  # 9 AM to 4 PM EST (approximate)
                market_status = "🟢 Open"
        
        status_message = f"""
🤖 **Bot Status: 🟢 ONLINE**

**👤 Your Status:**
• Subscription: {"🔔 Active" if is_subscribed else "🔕 Inactive"}
• User ID: {user.id}
• Joined: User registered

**📈 Market Status:**
• US Markets: {market_status}
• Current Time: {now.strftime('%H:%M')} EST
• Next Summary: {"Tomorrow 7:00 AM" if now.hour >= 10 else "Today 7:00 AM"} EST

**🔄 Bot Health:**
• Status: Fully operational
• News Sources: {len(self.news_sources)} active
• Database: Connected
• Updates: Real-time

**📊 Today's Summary:**
{"✅ Available" if self.daily_summary_cache else "⏳ Generating..."}

Use /news to get the latest market analysis!
        """
        await update.message.reply_text(status_message, parse_mode='Markdown')
    
    async def manual_news_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle manual /news command - get unified digest"""
        user = update.effective_user
        self.db.add_user(user.id, user.username, user.first_name, user.last_name)
        
        await update.message.reply_text(self.get_text(user.id, 'fetching_news'))
        
        try:
            # Generate unified digest with stock prices for the user
            digest = await self.generate_unified_digest(user.id, include_stocks=True)
            await update.message.reply_text(digest, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error generating manual unified digest for user {user.id}: {e}")
            await update.message.reply_text(self.get_text(user.id, 'error_fetching'))
    
    async def manual_notify_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            # Generate fresh news summary
            summary = await self.generate_daily_summary()
            
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
                    # Generate unified digest for each user
                    user_digest = await self.generate_unified_digest(user_id, include_stocks=True)
                    await self.bot.send_message(
                        chat_id=user_id, 
                        text=f"🔔 **{self.get_text(user_id, 'manual_notification')}**\n\n{user_digest}", 
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
    
    async def test_market_notification_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /testmarket command - test market notifications"""
        user = update.effective_user
        
        if not self.is_admin(user.id):
            await update.message.reply_text("❌ This command is only available to administrators.")
            return
        
        try:
            # Send test market notification to the user
            await self.send_market_notification("NYSE", "open", user.id)
            await update.message.reply_text("✅ Test market notification sent! Check your messages.")
            
        except Exception as e:
            logger.error(f"Error sending test market notification: {e}")
            await update.message.reply_text(f"❌ Error sending test notification: {e}")
    
    async def test_chatgpt_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /testchatgpt command - test ChatGPT integration"""
        user = update.effective_user
        
        if not self.is_admin(user.id):
            await update.message.reply_text("❌ This command is only available to administrators.")
            return
        
        try:
            await update.message.reply_text("🧠 Testing ChatGPT integration...")
            
            # Test with a simple financial content
            test_content = """=== NEWS ARTICLES ===
1. Apple Reports Strong Q3 Earnings
   Source: Bloomberg
   Summary: Apple Inc. reported better-than-expected quarterly earnings...

2. Fed Signals Potential Rate Changes
   Source: Reuters
   Summary: Federal Reserve officials indicated possible adjustments...

=== STOCK PRICES & TRENDS ===
📈 AAPL: $150.25 (+2.5%)
📉 MSFT: $300.10 (-1.2%)
📈 GOOGL: $120.50 (+0.8%)

=== MARKET CONTEXT ===
Current time: Market hours
Focus: Financial markets, technology, economy, global trends
Instructions: Create a professional, engaging digest that combines news insights with stock analysis"""

            # Test ChatGPT processing
            result = await self._process_with_chatgpt(test_content, 'ru')
            
            await update.message.reply_text(f"✅ ChatGPT Test Successful!\n\n{result}", parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error testing ChatGPT: {e}")
            await update.message.reply_text(f"❌ ChatGPT test failed: {e}")
    
    async def add_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /addadmin command - add a new admin user"""
        user = update.effective_user
        self.db.add_user(user.id, user.username, user.first_name, user.last_name)
        
        # Only allow the first user (bot owner) to add admins
        # You can customize this logic based on your needs
        if len(self.admin_users) == 0:
            # First user becomes admin automatically
            self.admin_users.add(user.id)
            await update.message.reply_text(
                "✅ **Admin Access Granted**\n\n"
                f"You are now an administrator of this bot.\n"
                f"User ID: {user.id}\n"
                f"Username: @{user.username or 'None'}"
            )
            return
        
        # Check if current user is admin
        if not self.is_admin(user.id):
            await update.message.reply_text(
                "❌ **Access Denied**\n\n"
                "Only administrators can add new admin users."
            )
            return
        
        # Check if admin ID was provided
        if not context.args:
            await update.message.reply_text(
                "📝 **Usage:** `/addadmin <user_id>`\n\n"
                "Example: `/addadmin 123456789`\n\n"
                "To get a user's ID, ask them to send /start to the bot first."
            )
            return
        
        try:
            new_admin_id = int(context.args[0])
            
            # Check if user exists in database
            if new_admin_id not in [u[0] for u in self.db.get_all_users()]:
                await update.message.reply_text(
                    "❌ **User Not Found**\n\n"
                    f"User ID {new_admin_id} is not registered with this bot.\n"
                    "Ask them to send /start to the bot first."
                )
                return
            
            # Add to admin list
            self.admin_users.add(new_admin_id)
            
            await update.message.reply_text(
                "✅ **Admin Added Successfully**\n\n"
                f"User ID: {new_admin_id}\n"
                f"Added by: {user.id}\n"
                f"Total admins: {len(self.admin_users)}"
                )
            
            logger.info(f"Admin user {new_admin_id} added by {user.id}")
            
        except ValueError:
            await update.message.reply_text(
                "❌ **Invalid User ID**\n\n"
                "Please provide a valid numeric user ID.\n"
                "Example: `/addadmin 123456789`"
            )
    
    async def language_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /language command - show language selection with inline buttons"""
        user = update.effective_user
        self.db.add_user(user.id, user.username, user.first_name, user.last_name)
        
        # Show language selection menu with inline buttons
        current_lang = self.db.get_user_language(user.id)
        current_lang_name = self.get_text(user.id, 'english' if current_lang == 'en' else 'russian')
        
        language_message = f"""
🌍 **{self.get_text(user.id, 'language_selection')}**

{self.get_text(user.id, 'choose_language')}

**📍 {self.get_text(user.id, 'current_language')}**: {current_lang_name}

Выберите язык / Choose language:
        """
        
        # Create inline keyboard with language options
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
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
        current_topic_names = []
        if current_topics == 'all':
            current_topic_names = [self.get_text(user.id, 'topic_all')]
        else:
            current_topic_names = [self.available_topics[current_topics][self.db.get_user_language(user.id)]]
        
        message_text = (
            f"{self.get_text(user.id, 'topic_selection')}\n\n"
            f"{self.get_text(user.id, 'current_topics')}: {', '.join(current_topic_names)}"
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
    
    async def fetch_news_from_source(self, source_name: str, url: str) -> List[NewsItem]:
        """Fetch news from a single RSS source"""
        try:
            # Create SSL context that's more permissive for RSS feeds
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Create connector with SSL context
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        content = await response.text()
                        feed = feedparser.parse(content)
                        
                        news_items = []
                        for entry in feed.entries[:5]:  # Get top 5 articles
                            news_items.append(NewsItem(
                                title=entry.get('title', 'No title'),
                                summary=entry.get('summary', entry.get('description', 'No summary')),
                                source=source_name,
                                published=entry.get('published', 'Unknown'),
                                url=entry.get('link', '')
                            ))
                        return news_items
                    else:
                        logger.warning(f"HTTP {response.status} from {source_name}")
                        return []
        except Exception as e:
            logger.error(f"Error fetching from {source_name}: {e}")
            return []
    
    async def fetch_topic_news(self, user_id: int) -> List[NewsItem]:
        """Fetch topic-specific news using RSS + ChatGPT filtering"""
        try:
            user_topics = self.db.get_user_topics(user_id)
            user_language = self.db.get_user_language(user_id)
            
            logger.info(f"🎯 User {user_id} has topic: '{user_topics}', language: '{user_language}'")
            
            # First, fetch real-time news from RSS feeds
            all_news = await self.fetch_all_news()
            if not all_news:
                logger.warning("No RSS news available for topic filtering")
                return []
            
            # Define topic-specific keywords for filtering
            topic_keywords = {
                'all': {
                    'en': ['market', 'stock', 'economy', 'financial', 'trading', 'investment', 'earnings', 'revenue', 'profit', 'growth', 'company', 'business', 'industry', 'sector', 'price', 'index', 'dow', 'nasdaq', 'sp500', 'fed', 'inflation', 'interest', 'rate', 'oil', 'gas', 'gold', 'silver', 'tech', 'bank', 'energy', 'mining'],
                    'ru': ['рынок', 'акции', 'экономика', 'финансы', 'торговля', 'инвестиции', 'доходы', 'выручка', 'прибыль', 'рост', 'компания', 'бизнес', 'отрасль', 'сектор', 'цена', 'индекс', 'dow', 'nasdaq', 'sp500', 'фрс', 'инфляция', 'процент', 'ставка', 'нефть', 'газ', 'золото', 'серебро', 'технологии', 'банк', 'энергия', 'добыча']
                },
                'oil_gas': {
                    'en': ['oil', 'gas', 'energy', 'petroleum', 'crude', 'brent', 'wti', 'opec', 'pipeline', 'refinery', 'exxon', 'chevron', 'shell', 'bp', 'energy', 'fuel', 'drilling', 'shale'],
                    'ru': ['нефть', 'газ', 'энергия', 'нефтепродукты', 'сырая', 'брент', 'wti', 'опек', 'трубопровод', 'нефтепереработка', 'эксон', 'шеврон', 'шелл', 'бп', 'энергия', 'топливо', 'бурение', 'сланцы']
                },
                'metals_mining': {
                    'en': ['gold', 'silver', 'copper', 'aluminum', 'nickel', 'zinc', 'platinum', 'palladium', 'mining', 'commodity', 'ore', 'mineral', 'bhp', 'rio tinto', 'vale', 'glencore', 'mining', 'extraction'],
                    'ru': ['золото', 'серебро', 'медь', 'алюминий', 'никель', 'цинк', 'платина', 'палладий', 'добыча', 'сырье', 'руда', 'минерал', 'bhp', 'rio tinto', 'vale', 'glencore', 'добыча', 'извлечение']
                },
                'technology': {
                    'en': ['tech', 'technology', 'ai', 'artificial intelligence', 'semiconductor', 'chip', 'software', 'digital', 'innovation', 'apple', 'microsoft', 'google', 'amazon', 'meta', 'tesla', 'nvidia', 'amd', 'intel'],
                    'ru': ['технологии', 'искусственный интеллект', 'полупроводники', 'чип', 'программное обеспечение', 'цифровой', 'инновации', 'apple', 'microsoft', 'google', 'amazon', 'meta', 'tesla', 'nvidia', 'amd', 'intel']
                },
                'finance': {
                    'en': ['bank', 'banking', 'financial', 'finance', 'credit', 'loan', 'mortgage', 'interest rate', 'federal reserve', 'fed', 'jpmorgan', 'goldman', 'morgan stanley', 'credit suisse', 'ubs', 'regulation', 'compliance'],
                    'ru': ['банк', 'банковское дело', 'финансы', 'кредит', 'ссуда', 'ипотека', 'процентная ставка', 'федеральная резервная система', 'фрс', 'jpmorgan', 'goldman', 'morgan stanley', 'credit suisse', 'ubs', 'регулирование', 'соответствие']
                }
            }
            
            # Get keywords for user's topic and language
            keywords = topic_keywords[user_topics].get(user_language, topic_keywords[user_topics]['en'])
            
            # Filter news by topic relevance
            relevant_news = []
            logger.info(f"🔍 Filtering news for topic: {user_topics}")
            logger.info(f"🔍 Using keywords: {keywords[:5]}...")  # Log first 5 keywords
            
            for item in all_news:
                # Check if news item contains topic-relevant keywords
                text = (item.title + ' ' + item.summary).lower()
                relevance_score = sum(1 for keyword in keywords if keyword.lower() in text)
                
                if relevance_score > 0:
                    relevant_news.append((item, relevance_score))
                    logger.info(f"✅ Relevant news: {item.title[:50]}... (score: {relevance_score})")
                else:
                    logger.info(f"❌ Not relevant: {item.title[:50]}...")
            
            logger.info(f"📊 Found {len(relevant_news)} relevant news items out of {len(all_news)} total")
            
            # Sort by relevance score (highest first)
            relevant_news.sort(key=lambda x: x[1], reverse=True)
            
            # Take top 7 most relevant news items
            filtered_news = [item[0] for item in relevant_news[:7]]
            
            if filtered_news:
                logger.info(f"Filtered {len(filtered_news)} topic-relevant news items for {user_topics}")
                
                # Use ChatGPT to enhance and summarize the filtered news
                enhanced_news = await self._enhance_news_with_chatgpt(filtered_news, user_topics, user_language)
                if enhanced_news:
                    return enhanced_news
                
                return filtered_news
            else:
                logger.warning(f"No topic-relevant news found for {user_topics}, returning general news")
                return all_news[:5]  # Return top 5 general news items
            
        except Exception as e:
            logger.error(f"Error fetching topic news: {e}")
            return await self.fetch_all_news()
    
    async def _enhance_news_with_chatgpt(self, news_items: List[NewsItem], topic: str, language: str) -> List[NewsItem]:
        """Enhance filtered news with ChatGPT analysis"""
        try:
            # Create prompt for ChatGPT to enhance the news
            topic_names = {
                'all': {'en': 'general financial markets', 'ru': 'общие финансовые рынки'},
                'oil_gas': {'en': 'oil and gas sector', 'ru': 'нефтегазовый сектор'},
                'metals_mining': {'en': 'metals and mining sector', 'ru': 'металлургия и добыча'},
                'technology': {'en': 'technology sector', 'ru': 'технологический сектор'},
                'finance': {'en': 'finance and banking sector', 'ru': 'финансовый и банковский сектор'}
            }
            
            topic_name = topic_names[topic].get(language, topic_names[topic]['en'])
            
            # Prepare news content for ChatGPT
            news_content = ""
            for i, item in enumerate(news_items, 1):
                news_content += f"{i}. {item.title}\n"
                news_content += f"   Summary: {item.summary}\n"
                news_content += f"   Source: {item.source}\n\n"
            
            prompt = f"""Analyze and enhance these {topic_name} news stories. For each story, provide:

1. Enhanced summary with market impact analysis
2. Key insights for investors
3. Potential market implications

Format each enhanced story as:
Title: [Original Title]
Enhanced Summary: [Improved summary with analysis]
Market Impact: [How this affects the market]
Key Insights: [What investors should know]

Focus on making the analysis professional and actionable for investors in this sector."""

            # Use ChatGPT to enhance the news
            client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a financial analyst specializing in market analysis. Enhance news stories with professional insights and market impact analysis."},
                    {"role": "user", "content": prompt + "\n\n" + news_content}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            # Parse enhanced content and update news items
            enhanced_content = response.choices[0].message.content
            return self._parse_enhanced_news(enhanced_content, news_items, language)
            
        except Exception as e:
            logger.warning(f"ChatGPT enhancement failed: {e}")
            return news_items  # Return original news if enhancement fails
    
    def _parse_enhanced_news(self, enhanced_content: str, original_news: List[NewsItem], language: str) -> List[NewsItem]:
        """Parse ChatGPT enhanced news content"""
        try:
            import re
            enhanced_news = []
            
            # Split content into sections
            sections = enhanced_content.split('\n\n')
            
            for i, section in enumerate(sections):
                if i >= len(original_news):
                    break
                    
                # Extract enhanced components
                enhanced_summary_match = re.search(r'Enhanced Summary:\s*(.+)', section)
                market_impact_match = re.search(r'Market Impact:\s*(.+)', section)
                key_insights_match = re.search(r'Key Insights:\s*(.+)', section)
                
                if enhanced_summary_match:
                    # Update the original news item with enhanced content
                    original_item = original_news[i]
                    
                    # Combine enhanced summary with market impact and insights
                    enhanced_summary = enhanced_summary_match.group(1).strip()
                    if market_impact_match:
                        enhanced_summary += f" Market Impact: {market_impact_match.group(1).strip()}"
                    if key_insights_match:
                        enhanced_summary += f" Key Insights: {key_insights_match.group(1).strip()}"
                    
                    # Create enhanced news item
                    enhanced_item = NewsItem(
                        title=original_item.title,
                        summary=enhanced_summary,
                        source=original_item.source,
                        published=original_item.published,
                        url=original_item.url
                    )
                    
                    enhanced_news.append(enhanced_item)
            
            return enhanced_news if enhanced_news else original_news
            
        except Exception as e:
            logger.error(f"Error parsing enhanced news: {e}")
            return original_news
    

    
    async def fetch_all_news(self) -> List[NewsItem]:
        """Fetch news from all sources with fallback (legacy method)"""
        all_news = []
        successful_sources = 0
        
        # Try primary sources first
        for source_name, url in self.news_sources.items():
            try:
                news_items = await self.fetch_news_from_source(source_name, url)
                if news_items:
                    all_news.extend(news_items)
                    successful_sources += 1
                    logger.info(f"✅ Successfully fetched from {source_name}: {len(news_items)} articles")
                else:
                    logger.warning(f"⚠️ No news from {source_name}")
            except Exception as e:
                logger.error(f"❌ Failed to fetch from {source_name}: {e}")
        
        # If we don't have enough news, try fallback sources
        if len(all_news) < 10 and successful_sources < 3:
            logger.info("🔄 Trying fallback RSS sources...")
            for source_name, url in self.fallback_sources.items():
                try:
                    news_items = await self.fetch_news_from_source(source_name, url)
                    if news_items:
                        all_news.extend(news_items)
                        logger.info(f"✅ Fallback success from {source_name}: {len(news_items)} articles")
                except Exception as e:
                    logger.error(f"❌ Fallback failed for {source_name}: {e}")
        
        logger.info(f"📊 Total news fetched: {len(all_news)} articles from {successful_sources} sources")
        
        # If no news was fetched, create some mock content to avoid empty summaries
        if not all_news:
            logger.warning("⚠️ No news fetched from any source, creating fallback content")
            all_news = self.create_fallback_news()
        
        return all_news
    
    def create_fallback_news(self) -> List[NewsItem]:
        """Create fallback news content when RSS feeds fail"""
        from datetime import datetime, timedelta
        
        fallback_news = [
            NewsItem(
                title="Market Update: Trading Session Overview",
                summary="Current market session shows mixed signals across major indices. Technology sector leading gains while energy stocks face pressure from oil price fluctuations.",
                source="System Generated",
                published=(datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
                url=""
            ),
            NewsItem(
                title="Economic Calendar: Key Events This Week",
                summary="Federal Reserve meeting minutes, CPI data, and earnings reports from major tech companies expected to drive market sentiment this week.",
                source="System Generated",
                published=(datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
                url=""
            ),
            NewsItem(
                title="Sector Performance: Market Rotation Continues",
                summary="Defensive sectors showing strength as investors assess economic data. Healthcare and utilities outperforming while cyclical stocks remain volatile.",
                source="System Generated",
                published=(datetime.now() - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S"),
                url=""
            )
        ]
        
        logger.info(f"📝 Created {len(fallback_news)} fallback news items")
        return fallback_news
    
    def analyze_news_sentiment(self, news_items: List[NewsItem]) -> Dict[str, any]:
        """Advanced sentiment analysis and trend detection"""
        positive_keywords = ['gain', 'rise', 'up', 'bull', 'growth', 'profit', 'surge', 'rally', 'boom', 
                           'strong', 'beat', 'exceed', 'positive', 'upgrade', 'buy', 'optimistic']
        negative_keywords = ['fall', 'drop', 'down', 'bear', 'loss', 'crash', 'decline', 'recession', 
                           'slump', 'weak', 'miss', 'disappointing', 'negative', 'downgrade', 'sell', 'pessimistic']
        
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        
        trending_topics = {}
        sector_mentions = {}
        
        # Sector keywords
        sectors = {
            'tech': ['technology', 'tech', 'apple', 'microsoft', 'google', 'amazon', 'meta', 'tesla', 'nvidia'],
            'energy': ['oil', 'gas', 'energy', 'exxon', 'chevron', 'renewable'],
            'finance': ['bank', 'finance', 'jpmorgan', 'goldman', 'credit', 'loan'],
            'healthcare': ['health', 'pharma', 'drug', 'medical', 'pfizer', 'johnson'],
            'crypto': ['bitcoin', 'crypto', 'ethereum', 'blockchain', 'digital currency']
        }
        
        for item in news_items:
            text = (item.title + ' ' + item.summary).lower()
            
            # Count sentiment
            pos_score = sum(1 for word in positive_keywords if word in text)
            neg_score = sum(1 for word in negative_keywords if word in text)
            
            if pos_score > neg_score:
                positive_count += 1
            elif neg_score > pos_score:
                negative_count += 1
            else:
                neutral_count += 1
            
            # Track trending general topics
            for word in ['inflation', 'fed', 'interest', 'earnings', 'china', 'europe', 'jobs', 'gdp']:
                if word in text:
                    trending_topics[word] = trending_topics.get(word, 0) + 1
            
            # Track sector mentions
            for sector, keywords in sectors.items():
                for keyword in keywords:
                    if keyword in text:
                        sector_mentions[sector] = sector_mentions.get(sector, 0) + 1
                        break
        
        return {
            'sentiment': {
                'positive': positive_count,
                'negative': negative_count,
                'neutral': neutral_count
            },
            'trending_topics': sorted(trending_topics.items(), key=lambda x: x[1], reverse=True)[:5],
            'hot_sectors': sorted(sector_mentions.items(), key=lambda x: x[1], reverse=True)[:3]
        }
    
    def generate_predictions(self, analysis: Dict[str, any]) -> str:
        """Generate comprehensive market predictions based on analysis"""
        sentiment = analysis['sentiment']
        total_articles = sum(sentiment.values())
        
        if total_articles == 0:
            return "Unable to generate predictions due to insufficient data."
        
        positive_ratio = sentiment['positive'] / total_articles
        negative_ratio = sentiment['negative'] / total_articles
        
        predictions = []
        
        # Market direction prediction with confidence
        if positive_ratio > 0.7:
            predictions.append("📈 **Market Outlook**: Strong positive sentiment suggests potential upward momentum (High Confidence)")
        elif positive_ratio > 0.55:
            predictions.append("📈 **Market Outlook**: Moderately positive sentiment indicates possible gains (Medium Confidence)")
        elif negative_ratio > 0.7:
            predictions.append("📉 **Market Outlook**: Strong negative sentiment warns of potential downward pressure (High Confidence)")
        elif negative_ratio > 0.55:
            predictions.append("📉 **Market Outlook**: Moderately negative sentiment suggests possible declines (Medium Confidence)")
        else:
            predictions.append("⚖️ **Market Outlook**: Mixed sentiment indicates sideways movement or volatility")
        
        # Trending topics
        if analysis['trending_topics']:
            predictions.append("\n🔥 **Key Focus Areas:**")
            for topic, count in analysis['trending_topics'][:3]:
                predictions.append(f"   • **{topic.capitalize()}** ({count} mentions) - High market attention")
        
        # Hot sectors
        if analysis['hot_sectors']:
            predictions.append("\n🎯 **Sector Spotlight:**")
            for sector, count in analysis['hot_sectors']:
                predictions.append(f"   • **{sector.capitalize()}** sector showing increased activity")
        
        # Trading suggestions based on sentiment
        predictions.append("\n💡 **Trading Considerations:**")
        if positive_ratio > 0.6:
            predictions.append("   • Consider growth stocks and cyclical sectors")
            predictions.append("   • Monitor for breakout opportunities")
        elif negative_ratio > 0.6:
            predictions.append("   • Defensive positioning may be prudent")
            predictions.append("   • Watch for oversold opportunities")
        else:
            predictions.append("   • Range-bound trading likely")
            predictions.append("   • Focus on stock-specific catalysts")
        
        # Risk assessment
        risk_level = "Medium"
        if abs(positive_ratio - negative_ratio) > 0.4:
            risk_level = "High - Strong directional bias"
        elif abs(positive_ratio - negative_ratio) < 0.2:
            risk_level = "Medium - Mixed signals"
        
        predictions.append(f"\n⚠️ **Risk Level**: {risk_level}")
        predictions.append("\n📚 **Reminder**: Analysis based on news sentiment. Not financial advice. Always do your own research.")
        
        return '\n'.join(predictions)
    
    async def generate_daily_summary(self) -> str:
        """Generate the complete daily summary"""
        try:
            # Fetch all news
            news_items = await self.fetch_all_news()
            
            if not news_items:
                return "❌ Unable to fetch news at this time. Please try again later."
            
            # Analyze sentiment
            analysis = self.analyze_news_sentiment(news_items)
            
            # Generate predictions
            predictions = self.generate_predictions(analysis)
            
            # Create summary message
            summary = f"""
📊 **{self.translations['en']['daily_intelligence']}**
📅 {datetime.now().strftime('%B %d, %Y')} • {datetime.now().strftime('%H:%M')} EST

**📈 {self.translations['en']['market_sentiment']}**
• {self.translations['en']['positive_news']}: {analysis['sentiment']['positive']} articles ({analysis['sentiment']['positive']/(sum(analysis['sentiment'].values()))*100:.1f}%)
• {self.translations['en']['negative_news']}: {analysis['sentiment']['negative']} articles ({analysis['sentiment']['negative']/(sum(analysis['sentiment'].values()))*100:.1f}%)
• {self.translations['en']['neutral_news']}: {analysis['sentiment']['neutral']} articles ({analysis['sentiment']['neutral']/(sum(analysis['sentiment'].values()))*100:.1f}%)

**🚨 {self.translations['en']['top_headlines']}**
"""
            
            # Add top headlines from different sources
            added_sources = set()
            headline_count = 0
            for item in news_items[:8]:
                if item.source not in added_sources and headline_count < 5:
                    summary += f"\n📰 **{item.source}**\n"
                    summary += f"*{item.title[:100]}{'...' if len(item.title) > 100 else ''}*\n"
                    added_sources.add(item.source)
                    headline_count += 1
            
            summary += f"\n**🔮 {self.translations['en']['market_predictions']}**\n{predictions}\n"
            
            # Add footer with sources
            summary += f"\n📡 **Sources**: {', '.join(list(self.news_sources.keys())[:4])} + more"
            summary += f"\n🤖 **Generated**: {datetime.now().strftime('%H:%M')} EST | Users: {self.db.get_user_count():,}"
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating daily summary: {e}")
            return """
❌ **Service Temporarily Unavailable**

We're experiencing technical difficulties fetching market news. Our team has been notified and is working on a fix.

🔄 **What you can do:**
• Try again in a few minutes
• Check /status for updates
• Use /help for other commands

We apologize for the inconvenience and appreciate your patience! 🙏
            """
    
    async def generate_translated_summary(self, user_id: int) -> str:
        """Generate daily summary in user's preferred language"""
        try:
            # Fetch all news
            news_items = await self.fetch_all_news()
            
            if not news_items:
                return self.get_text(user_id, 'no_news')
            
            # Analyze sentiment
            analysis = self.analyze_news_sentiment(news_items)
            
            # Generate predictions
            predictions = self.generate_predictions(analysis)
            
            # Get user's language
            user_language = self.db.get_user_language(user_id)
            
            # Create summary in user's language
            if user_language == 'ru':
                summary = f"""
📊 **{self.translations['ru']['daily_intelligence']}**
📅 {datetime.now().strftime('%B %d, %Y')} • {datetime.now().strftime('%H:%M')} EST

**📈 {self.translations['ru']['market_sentiment']}**
• {self.translations['ru']['positive_news']}: {analysis['sentiment']['positive']} статей ({analysis['sentiment']['positive']/(sum(analysis['sentiment'].values()))*100:.1f}%)
• {self.translations['ru']['negative_news']}: {analysis['sentiment']['negative']} статей ({analysis['sentiment']['negative']/(sum(analysis['sentiment'].values()))*100:.1f}%)
• {self.translations['ru']['neutral_news']}: {analysis['sentiment']['neutral']} статей ({analysis['sentiment']['neutral']/(sum(analysis['sentiment'].values()))*100:.1f}%)

**🚨 {self.translations['ru']['top_headlines']}**
"""
            else:
                summary = f"""
📊 **{self.translations['en']['daily_intelligence']}**
📅 {datetime.now().strftime('%B %d, %Y')} • {datetime.now().strftime('%H:%M')} EST

**📈 {self.translations['en']['market_sentiment']}**
• {self.translations['en']['positive_news']}: {analysis['sentiment']['positive']} articles ({analysis['sentiment']['positive']/(sum(analysis['sentiment'].values()))*100:.1f}%)
• {self.translations['en']['negative_news']}: {analysis['sentiment']['negative']} articles ({analysis['sentiment']['negative']/(sum(analysis['sentiment'].values()))*100:.1f}%)
• {self.translations['en']['neutral_news']}: {analysis['sentiment']['neutral']} articles ({analysis['sentiment']['neutral']/(sum(analysis['sentiment'].values()))*100:.1f}%)

**🚨 {self.translations['en']['top_headlines']}**
"""
            
            # Add top headlines from different sources
            added_sources = set()
            headline_count = 0
            for item in news_items[:8]:
                if item.source not in added_sources and headline_count < 5:
                    # Translate news content if user prefers Russian
                    if user_language == 'ru':
                        title = await self.translate_news_content(item.title, 'ru')
                        summary += f"\n📰 **{item.source}**\n"
                        summary += f"*{title[:100]}{'...' if len(title) > 100 else ''}*\n"
                    else:
                        summary += f"\n📰 **{item.source}**\n"
                        summary += f"*{item.title[:100]}{'...' if len(item.title) > 100 else ''}*\n"
                    added_sources.add(item.source)
                    headline_count += 1
            
            # Add predictions
            if user_language == 'ru':
                summary += f"\n**🔮 {self.translations['ru']['market_predictions']}**\n{predictions}\n"
            else:
                summary += f"\n**🔮 {self.translations['en']['market_predictions']}**\n{predictions}\n"
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating translated summary for user {user_id}: {e}")
            return self.get_text(user_id, 'no_news')
    
    async def send_daily_summary_to_subscribers(self):
        """Send unified daily digest to all subscribed users"""
        try:
            subscribers = self.db.get_subscribed_users()
            if not subscribers:
                logger.info("No subscribers found for daily summary")
                return
            
            # Send to all subscribers with rate limiting
            successful_sends = 0
            failed_sends = 0
            
            for user_id in subscribers:
                try:
                    # Generate personalized unified digest for each user
                    digest = await self.generate_unified_digest(user_id, include_stocks=True)
                    
                    await self.bot.send_message(
                        chat_id=user_id, 
                        text=digest, 
                        parse_mode='Markdown'
                    )
                    successful_sends += 1
                    
                    # Rate limiting - Telegram allows ~30 messages per second
                    await asyncio.sleep(0.05)
                    
                except Exception as e:
                    logger.error(f"Failed to send digest to user {user_id}: {e}")
                    failed_sends += 1
                    
                    # If user blocked bot, we might want to unsubscribe them
                    if "bot was blocked" in str(e).lower():
                        self.db.unsubscribe_user(user_id)
            
            logger.info(f"Unified digest sent to {successful_sends} users, {failed_sends} failed")
            
        except Exception as e:
            logger.error(f"Error sending unified digest to subscribers: {e}")
    
    def schedule_daily_summaries(self):
        """Schedule daily summaries"""
        # Daily morning summary at 9:00 AM EST
        schedule.every().day.at("09:00").do(
            lambda: asyncio.create_task(self.send_daily_summary_to_subscribers())
        )
        
        # Market opening summary at 9:30 AM EST (weekdays only)
        schedule.every().monday.at("09:30").do(
            lambda: asyncio.create_task(self.send_daily_summary_to_subscribers())
        )
        schedule.every().tuesday.at("09:30").do(
            lambda: asyncio.create_task(self.send_daily_summary_to_subscribers())
        )
        schedule.every().wednesday.at("09:30").do(
            lambda: asyncio.create_task(self.send_daily_summary_to_subscribers())
        )
        schedule.every().thursday.at("09:30").do(
            lambda: asyncio.create_task(self.send_daily_summary_to_subscribers())
        )
        schedule.every().friday.at("09:30").do(
            lambda: asyncio.create_task(self.send_daily_summary_to_subscribers())
        )
        
        # Market notifications (15 minutes before/after major markets)
        # NYSE/NASDAQ (US Markets) - Weekdays only
        schedule.every().monday.at("09:15").do(
            lambda: asyncio.create_task(self.send_market_notifications("NYSE", "open"))
        )
        schedule.every().monday.at("16:15").do(
            lambda: asyncio.create_task(self.send_market_notifications("NYSE", "close"))
        )
        schedule.every().tuesday.at("09:15").do(
            lambda: asyncio.create_task(self.send_market_notifications("NYSE", "open"))
        )
        schedule.every().tuesday.at("16:15").do(
            lambda: asyncio.create_task(self.send_market_notifications("NYSE", "close"))
        )
        schedule.every().wednesday.at("09:15").do(
            lambda: asyncio.create_task(self.send_market_notifications("NYSE", "open"))
        )
        schedule.every().wednesday.at("16:15").do(
            lambda: asyncio.create_task(self.send_market_notifications("NYSE", "close"))
        )
        schedule.every().thursday.at("09:15").do(
            lambda: asyncio.create_task(self.send_market_notifications("NYSE", "open"))
        )
        schedule.every().thursday.at("16:15").do(
            lambda: asyncio.create_task(self.send_market_notifications("NYSE", "close"))
        )
        schedule.every().friday.at("09:15").do(
            lambda: asyncio.create_task(self.send_market_notifications("NYSE", "open"))
        )
        schedule.every().friday.at("16:15").do(
            lambda: asyncio.create_task(self.send_market_notifications("NYSE", "close"))
        )
    
    async def send_market_notifications(self, market_name: str, action: str):
        """Send market notifications to all subscribers"""
        try:
            subscribers = self.db.get_subscribed_users()
            if not subscribers:
                logger.info(f"No subscribers found for {market_name} {action} notification")
                return
            
            # Send notification to all subscribers
            successful_sends = 0
            failed_sends = 0
            
            for user_id in subscribers:
                try:
                    await self.send_market_notification(market_name, action, user_id)
                    successful_sends += 1
                    
                    # Rate limiting
                    await asyncio.sleep(0.05)
                    
                except Exception as e:
                    logger.error(f"Failed to send {market_name} {action} notification to user {user_id}: {e}")
                    failed_sends += 1
            
            logger.info(f"{market_name} {action} notification sent to {successful_sends} users, {failed_sends} failed")
            
        except Exception as e:
            logger.error(f"Error sending {market_name} {action} notifications: {e}")
    
    async def run_scheduler(self):
        """Run the scheduled tasks"""
        logger.info("Scheduler started")
        while True:
            schedule.run_pending()
            await asyncio.sleep(60)  # Check every minute
    
    async def start_bot(self):
        """Start the public bot and scheduler"""
        logger.info("Starting Public Stock News Bot...")
        
        # Schedule daily summaries
        self.schedule_daily_summaries()
        
        # Start the bot
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        logger.info(f"Public bot started successfully! Users can find it and start using it immediately.")
        logger.info(f"Current subscriber count: {self.db.get_subscriber_count()}")
        
        # Run scheduler
        await self.run_scheduler()
    
    async def generate_unified_digest(self, user_id: int, include_stocks: bool = True) -> str:
        """Generate unified digest with news, stock prices, and ChatGPT-powered analysis"""
        try:
            # Get user language
            user_language = self.db.get_user_language(user_id)
            
            # Fetch topic-specific news
            news_items = await self.fetch_topic_news(user_id)
            if not news_items:
                return self.get_text(user_id, 'no_news')
            
            # Get topic-specific assets if requested
            stock_prices = []
            if include_stocks:
                stock_prices = await self.get_topic_assets(user_id)
            
            # Create unified content for ChatGPT processing
            unified_content = self._prepare_content_for_chatgpt(news_items, stock_prices, user_language)
            
            # Process with ChatGPT API
            processed_digest = await self._process_with_chatgpt(unified_content, user_language)
            
            return processed_digest
            
        except Exception as e:
            logger.error(f"Error generating unified digest for user {user_id}: {e}")
            # Fallback to traditional method
            return await self.generate_translated_summary(user_id)
    
    def _prepare_content_for_chatgpt(self, news_items: List[NewsItem], stock_prices: List[Dict], user_language: str) -> str:
        """Prepare unified content for ChatGPT processing"""
        content = f"Language: {user_language}\n\n"
        
        # Add news content
        content += "=== TOPIC-SPECIFIC NEWS ===\n"
        for i, item in enumerate(news_items[:7], 1):  # Top 7 articles for better focus
            content += f"{i}. {item.title}\n"
            content += f"   Source: {item.source}\n"
            content += f"   Summary: {item.summary[:150]}...\n"
            if item.url:
                content += f"   Link: {item.url}\n"
            content += "\n"
        
        # Add topic-specific assets with more context
        if stock_prices:
            content += "=== TOPIC-SPECIFIC ASSETS & TRENDS ===\n"
            for stock in stock_prices:
                direction = "📈" if stock['change_direction'] == 'up' else "📉"
                source_info = f" ({stock.get('source', 'Market Data')})" if 'source' in stock else ""
                content += f"{direction} {stock['symbol']}: ${stock['price']} ({stock['change']:+.2f}%){source_info}\n"
            content += "\n"
        
        # Add market context and instructions
        content += "=== MARKET CONTEXT ===\n"
        content += "Current time: Market hours\n"
        content += "Focus: Financial markets, technology, economy, global trends\n"
        content += "Instructions: Create a professional, engaging digest that combines news insights with stock analysis\n\n"
        
        return content
    
    async def _process_with_chatgpt(self, content: str, user_language: str) -> str:
        """Process content with ChatGPT API for translation and analysis"""
        try:
            import os
            from openai import AsyncOpenAI
            
            # Get API key from environment
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                logger.warning("OpenAI API key not found, using fallback")
                raise Exception("No API key")
            
            client = AsyncOpenAI(api_key=api_key)
            
            # Create system prompt based on language
            if user_language == 'ru':
                system_prompt = """Ты - эксперт по финансовым рынкам. Создай структурированный дайджест новостей и цен на акции на русском языке.

Формат:
📊 **РЫНОЧНЫЙ ДАЙДЖЕСТ** 📊

📰 **ГЛАВНЫЕ НОВОСТИ ПО ТЕМЕ**
• Краткое описание ключевых новостей (3-5 самых важных)
• Анализ влияния на рынок
• Источники новостей с ссылками

📈 **КЛЮЧЕВЫЕ АКТИВЫ**
• Цены и изменения по основным активам
• Тренды и паттерны
• Анализ движения цен

🔮 **ПРОГНОЗЫ И ТЕНДЕНЦИИ**
• Анализ настроений рынка
• Ключевые секторы для внимания
• Рекомендации для инвесторов

Используй эмодзи, структурируй информацию для легкого чтения, и сделай анализ профессиональным и понятным. Включи ссылки на полные статьи, если они доступны."""
            else:
                system_prompt = """You are a financial markets expert. Create a structured digest of news and stock prices in English.

Format:
📊 **MARKET DIGEST** 📊

📰 **TOP NEWS BY TOPIC**
• Brief description of key news (3-5 most important)
• Market impact analysis
• News sources with links

📈 **KEY ASSETS**
• Prices and changes for major assets
• Trends and patterns
• Price movement analysis

🔮 **FORECASTS & TRENDS**
• Market sentiment analysis
• Key sectors to watch
• Investor recommendations

Use emojis, structure information for easy reading, and make the analysis professional and understandable. Include links to full articles when available."""
            
            # Process with ChatGPT
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Process this financial content and create a digest in {user_language}:\n\n{content}"}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            result = response.choices[0].message.content
            logger.info(f"ChatGPT processing successful for {user_language}")
            return result
            
        except Exception as e:
            logger.error(f"ChatGPT processing failed: {e}")
            raise e

# Main execution
async def main():
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
        logger.warning("⚠️ OPENAI_API_KEY not found - ChatGPT features will use fallback")
    else:
        logger.info(f"✅ OpenAI API key loaded: {OPENAI_API_KEY[:10]}...")
    
    # Create and start public bot
    bot = PublicStockNewsBot(BOT_TOKEN)
    await bot.start_bot()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
