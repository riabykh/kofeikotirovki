#!/usr/bin/env python3
"""
Admin Configuration for Stock Telegram Bot
This file allows you to easily configure admin users for the bot.
"""

# Admin User IDs
# Add the Telegram user IDs of users who should have admin access
# You can get a user's ID by asking them to send /start to the bot first
ADMIN_USER_IDS = {
    # Example: 123456789,  # Replace with actual user IDs
    # Example: 987654321,  # Replace with actual user IDs
}

# Bot Owner ID (optional)
# The first user to use /addadmin will automatically become admin
# You can also set a specific user as the owner here
BOT_OWNER_ID = None  # Replace with actual owner ID if desired

# Admin Permissions
ADMIN_PERMISSIONS = {
    'can_notify_all': True,      # Can send notifications to all subscribers
    'can_add_admins': True,      # Can add new admin users
    'can_view_stats': True,      # Can view detailed bot statistics
    'can_manage_users': True,    # Can manage user subscriptions
}

# Notification Settings
NOTIFICATION_SETTINGS = {
    'max_notifications_per_hour': 10,  # Limit manual notifications per hour
    'require_confirmation': True,      # Ask for confirmation before sending
    'include_admin_info': True,        # Include who triggered the notification
}

# Usage Instructions:
# 1. Add admin user IDs to ADMIN_USER_IDS set
# 2. Set BOT_OWNER_ID if you want a specific user to be the owner
# 3. Customize permissions and notification settings as needed
# 4. Restart the bot for changes to take effect

if __name__ == "__main__":
    print("Admin Configuration File")
    print("=" * 30)
    print(f"Admin Users: {len(ADMIN_USER_IDS)}")
    print(f"Bot Owner: {BOT_OWNER_ID or 'Auto-assigned'}")
    print(f"Max Notifications/Hour: {NOTIFICATION_SETTINGS['max_notifications_per_hour']}")
    print(f"Require Confirmation: {NOTIFICATION_SETTINGS['require_confirmation']}")
