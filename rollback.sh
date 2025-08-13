#!/bin/bash

# Кофе и Котировки - Rollback Script
# This script helps you rollback to the backup version if needed

echo "🔄 Кофе и Котировки - Rollback Utility"
echo "=================================="

# Find the most recent backup
BACKUP_FILE=$(ls -t stock_bot_backup_*.py 2>/dev/null | head -1)

if [ -z "$BACKUP_FILE" ]; then
    echo "❌ No backup files found!"
    echo "💡 Backup files should be named: stock_bot_backup_YYYYMMDD_HHMMSS.py"
    exit 1
fi

echo "📋 Found backup: $BACKUP_FILE"
echo "📅 Current version: stock_bot.py"
echo ""

# Show file sizes for comparison
echo "📊 File comparison:"
ls -lh stock_bot.py $BACKUP_FILE | awk '{print $5 " " $9}'
echo ""

read -p "❓ Do you want to rollback to $BACKUP_FILE? (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Stop the bot if running
    echo "🛑 Stopping bot..."
    pkill -f stock_bot.py 2>/dev/null || true
    sleep 2
    
    # Create a backup of current version
    CURRENT_BACKUP="stock_bot_before_rollback_$(date +%Y%m%d_%H%M%S).py"
    echo "💾 Backing up current version to: $CURRENT_BACKUP"
    cp stock_bot.py "$CURRENT_BACKUP"
    
    # Rollback
    echo "🔄 Rolling back to: $BACKUP_FILE"
    cp "$BACKUP_FILE" stock_bot.py
    
    echo ""
    echo "✅ Rollback completed!"
    echo "📁 Current version backed up as: $CURRENT_BACKUP"
    echo "🚀 You can now start the bot with: python3 stock_bot.py"
    echo ""
    echo "🔧 To restore the newest version later:"
    echo "   cp $CURRENT_BACKUP stock_bot.py"
else
    echo "❌ Rollback cancelled."
fi
