#!/bin/bash

# Кофе и Котировки - Safe Bot Starter
# Prevents multiple instances and handles conflicts

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PIDFILE="bot.pid"
LOGFILE="bot.log"

echo "🚀 Кофе и Котировки - Bot Starter"
echo "================================"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping bot..."
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID"
            echo "✅ Bot stopped (PID: $PID)"
        fi
        rm -f "$PIDFILE"
    fi
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Check if bot is already running
if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "⚠️  Bot is already running (PID: $PID)"
        echo "💡 To stop it, run: kill $PID"
        echo "💡 Or use: pkill -f stock_bot.py"
        exit 1
    else
        echo "🔄 Removing stale PID file"
        rm -f "$PIDFILE"
    fi
fi

# Kill any existing instances
echo "🔍 Checking for existing bot instances..."
EXISTING_PIDS=$(pgrep -f "stock_bot.py")
if [ ! -z "$EXISTING_PIDS" ]; then
    echo "🛑 Stopping existing instances: $EXISTING_PIDS"
    pkill -f stock_bot.py
    sleep 2
    
    # Force kill if still running
    REMAINING=$(pgrep -f "stock_bot.py")
    if [ ! -z "$REMAINING" ]; then
        echo "💀 Force stopping remaining instances: $REMAINING"
        pkill -9 -f stock_bot.py
        sleep 1
    fi
fi

# Clear webhook and pending updates to avoid conflicts
echo "🧹 Clearing webhook and pending updates..."
python3 clear_webhook.py

echo "🚀 Starting bot..."
echo "📝 Logs will be written to: $LOGFILE"
echo "🛑 Press Ctrl+C to stop"
echo ""

# Start the bot
python3 stock_bot.py >> "$LOGFILE" 2>&1 &
BOT_PID=$!

# Save PID
echo $BOT_PID > "$PIDFILE"
echo "✅ Bot started with PID: $BOT_PID"

# Monitor the bot
while kill -0 "$BOT_PID" 2>/dev/null; do
    sleep 1
done

echo "❌ Bot process ended unexpectedly"
rm -f "$PIDFILE"