#!/bin/bash

# Stock News Bot Startup Script
# Usage: ./start_bot.sh

echo "🚀 Starting Stock News Bot..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📋 Installing dependencies..."
pip install -r requirements.txt

# Check environment variables
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    if [ -f ".env" ]; then
        echo "📁 Loading environment variables from .env..."
        export $(grep -v '^#' .env | xargs)
    else
        echo "❌ Error: TELEGRAM_BOT_TOKEN not set and no .env file found"
        echo "Please set environment variables or create .env file"
        exit 1
    fi
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ Error: OPENAI_API_KEY not set"
    exit 1
fi

# Create necessary directories
mkdir -p logs data backups

# Check if database exists, if not create it
if [ ! -f "stock_bot.db" ]; then
    echo "🗄️ Database will be created on first run..."
fi

# Start the bot
echo "🤖 Starting bot..."
echo "📊 Bot token: ${TELEGRAM_BOT_TOKEN:0:10}..."
echo "🧠 OpenAI key: ${OPENAI_API_KEY:0:10}..."
echo "⏰ Started at: $(date)"

# Run the bot with error handling
python stock_bot.py

# If bot exits, show exit code
EXIT_CODE=$?
echo "🛑 Bot stopped with exit code: $EXIT_CODE"
echo "⏰ Stopped at: $(date)"

if [ $EXIT_CODE -ne 0 ]; then
    echo "❌ Bot exited with error. Check logs for details."
fi

exit $EXIT_CODE