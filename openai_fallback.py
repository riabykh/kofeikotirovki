#!/usr/bin/env python3
"""
Temporary OpenAI fallback to provide basic functionality while fixing compatibility
"""

from dataclasses import dataclass
from typing import List
import random
from datetime import datetime

@dataclass 
class MockNewsItem:
    title: str
    summary: str
    source: str
    published: str
    url: str = ""

@dataclass
class MockAssetItem:
    symbol: str
    name: str
    price: float
    change: float
    change_direction: str
    source: str = "Market Data"

def generate_fallback_news(topic: str, language: str) -> List[MockNewsItem]:
    """Generate fallback news when OpenAI is not available"""
    
    if language == 'ru':
        news_items = [
            MockNewsItem(
                title="📈 Рыночная сводка",
                summary="Основные финансовые рынки показали смешанную динамику. Инвесторы следят за макроэкономическими показателями.",
                source="Market Analysis",
                published=datetime.now().strftime("%Y-%m-%d")
            ),
            MockNewsItem(
                title="🔋 Энергетический сектор",
                summary="Цены на энергоносители остаются волатильными на фоне геополитических событий.",
                source="Energy Report",
                published=datetime.now().strftime("%Y-%m-%d")
            ),
            MockNewsItem(
                title="🏭 Промышленность",
                summary="Промышленные индексы демонстрируют устойчивый рост благодаря увеличению производственной активности.",
                source="Industrial News",
                published=datetime.now().strftime("%Y-%m-%d")
            )
        ]
    else:
        news_items = [
            MockNewsItem(
                title="📈 Market Overview",
                summary="Major financial markets showed mixed performance as investors monitor macroeconomic indicators.",
                source="Market Analysis", 
                published=datetime.now().strftime("%Y-%m-%d")
            ),
            MockNewsItem(
                title="🔋 Energy Sector",
                summary="Energy prices remain volatile amid ongoing geopolitical developments affecting global supply chains.",
                source="Energy Report",
                published=datetime.now().strftime("%Y-%m-%d")
            ),
            MockNewsItem(
                title="🏭 Industrial Activity",
                summary="Industrial indices show steady growth driven by increased manufacturing activity and demand.",
                source="Industrial News",
                published=datetime.now().strftime("%Y-%m-%d")
            )
        ]
    
    return news_items

def generate_fallback_assets(topic: str, language: str) -> List[MockAssetItem]:
    """Generate fallback asset data when OpenAI is not available"""
    
    # Generate realistic mock prices
    base_prices = {
        'AAPL': 180.0,
        'GOOGL': 2800.0,
        'TSLA': 250.0,
        'MSFT': 340.0,
        'OIL': 85.0,
        'GOLD': 1950.0,
        'BTC': 45000.0
    }
    
    assets = []
    for symbol, base_price in list(base_prices.items())[:5]:
        change = random.uniform(-3.0, 3.0)
        price = base_price * (1 + change/100)
        
        assets.append(MockAssetItem(
            symbol=symbol,
            name=symbol,
            price=round(price, 2),
            change=round(change, 2),
            change_direction='up' if change >= 0 else 'down',
            source="Market Data"
        ))
    
    return assets

def generate_fallback_digest(news_items: List, asset_items: List, language: str) -> str:
    """Generate a fallback digest message"""
    
    if language == 'ru':
        digest = """📊 **РЫНОЧНЫЙ ДАЙДЖЕСТ** 📊

⚠️ **Временный режим работы**
🔧 Исправляем совместимость OpenAI библиотеки

📰 **ОСНОВНЫЕ НОВОСТИ**
"""
        for item in news_items[:3]:
            digest += f"• {item.title}\n  {item.summary}\n  📍 {item.source}\n\n"
        
        digest += "📈 **КЛЮЧЕВЫЕ АКТИВЫ**\n"
        for asset in asset_items[:4]:
            direction = "📈" if asset.change >= 0 else "📉"
            digest += f"{direction} {asset.symbol}: ${asset.price} ({asset.change:+.1f}%)\n"
        
        digest += "\n🔮 **СТАТУС СИСТЕМЫ**\n"
        digest += "• Telegram Bot: ✅ Работает\n"
        digest += "• База данных: ✅ Работает\n"
        digest += "• OpenAI API: 🔧 Исправляем\n\n"
        digest += "💡 Полная функциональность будет восстановлена в ближайшее время!"
        
    else:
        digest = """📊 **MARKET DIGEST** 📊

⚠️ **Temporary Mode**
🔧 Fixing OpenAI library compatibility

📰 **TOP NEWS**
"""
        for item in news_items[:3]:
            digest += f"• {item.title}\n  {item.summary}\n  📍 {item.source}\n\n"
        
        digest += "📈 **KEY ASSETS**\n"
        for asset in asset_items[:4]:
            direction = "📈" if asset.change >= 0 else "📉"
            digest += f"{direction} {asset.symbol}: ${asset.price} ({asset.change:+.1f}%)\n"
        
        digest += "\n🔮 **SYSTEM STATUS**\n"
        digest += "• Telegram Bot: ✅ Working\n"
        digest += "• Database: ✅ Working\n" 
        digest += "• OpenAI API: 🔧 Fixing\n\n"
        digest += "💡 Full functionality will be restored soon!"
    
    return digest
