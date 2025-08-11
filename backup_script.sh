#!/bin/bash

# Stock News Bot Backup Script
# Backs up database and configuration files

# Configuration
BACKUP_DIR="backups"
DB_FILE="stock_bot.db"
CONFIG_FILES=(".env" "stock_bot.py" "requirements.txt")
DATE=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="stock_bot_backup_$DATE"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔄 Starting backup process...${NC}"

# Create backup directory if it doesn't exist
if [ ! -d "$BACKUP_DIR" ]; then
    echo -e "${YELLOW}📁 Creating backup directory: $BACKUP_DIR${NC}"
    mkdir -p "$BACKUP_DIR"
fi

# Create timestamped backup directory
FULL_BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"
mkdir -p "$FULL_BACKUP_PATH"

echo -e "${GREEN}📦 Backup location: $FULL_BACKUP_PATH${NC}"

# Backup database
if [ -f "$DB_FILE" ]; then
    echo -e "${GREEN}🗄️  Backing up database: $DB_FILE${NC}"
    cp "$DB_FILE" "$FULL_BACKUP_PATH/"
    
    # Get database stats
    if command -v sqlite3 &> /dev/null; then
        USER_COUNT=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "0")
        echo -e "${GREEN}   📊 Database contains $USER_COUNT users${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Warning: Database file $DB_FILE not found${NC}"
fi

# Backup configuration files
echo -e "${GREEN}📋 Backing up configuration files...${NC}"
for file in "${CONFIG_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}   ✅ $file${NC}"
        cp "$file" "$FULL_BACKUP_PATH/"
    else
        echo -e "${YELLOW}   ⚠️  $file not found${NC}"
    fi
done

# Backup logs if they exist
if [ -d "logs" ]; then
    echo -e "${GREEN}📝 Backing up logs...${NC}"
    cp -r logs "$FULL_BACKUP_PATH/"
fi

# Create backup info file
cat > "$FULL_BACKUP_PATH/backup_info.txt" << EOF
Stock News Bot Backup
====================
Date: $(date)
Hostname: $(hostname)
User: $(whoami)
Python Version: $(python3 --version 2>/dev/null || echo "Unknown")
Bot Status: $(pgrep -f "stock_bot.py" > /dev/null && echo "Running" || echo "Not running")

Files included:
$(ls -la "$FULL_BACKUP_PATH")

EOF

# Create compressed archive
echo -e "${GREEN}🗜️  Creating compressed archive...${NC}"
cd "$BACKUP_DIR"
tar -czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME"
ARCHIVE_SIZE=$(du -h "${BACKUP_NAME}.tar.gz" | cut -f1)

# Remove uncompressed backup directory
rm -rf "$BACKUP_NAME"

echo -e "${GREEN}✅ Backup completed successfully!${NC}"
echo -e "${GREEN}📁 Archive: $BACKUP_DIR/${BACKUP_NAME}.tar.gz ($ARCHIVE_SIZE)${NC}"

# Cleanup old backups (keep last 7 days)
echo -e "${GREEN}🧹 Cleaning up old backups (keeping last 7 days)...${NC}"
find "$BACKUP_DIR" -name "stock_bot_backup_*.tar.gz" -mtime +7 -delete 2>/dev/null

# Show remaining backups
BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/stock_bot_backup_*.tar.gz 2>/dev/null | wc -l)
echo -e "${GREEN}📦 Total backups: $BACKUP_COUNT${NC}"

echo -e "${GREEN}🎉 Backup process completed!${NC}"

# Exit with success
exit 0
