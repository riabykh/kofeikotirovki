# 📱 Usage Examples - Stock Telegram Bot

This document provides practical examples of how to use the bot's features, including the new manual notification system.

## 🚀 Getting Started

### Basic Commands
```
/start          - Initialize the bot and get welcome message
/news           - Get current market news and predictions
/help           - Show all available commands
/status         - Check bot health and market status
```

### Subscription Management
```
/subscribe      - Enable daily automatic updates
/unsubscribe    - Disable daily automatic updates
/stats          - View bot usage statistics
```

## 🔐 Admin Commands

### Becoming an Admin
The first user to use `/addadmin` automatically becomes an admin:

```
/addadmin       - First user becomes admin automatically
```

### Adding Other Admins
Once you're an admin, you can add others:

```
/addadmin 123456789    - Grant admin access to user ID 123456789
```

### Manual Notifications
Admins can trigger notifications anytime:

```
/notify         - Send news update to all subscribers immediately
```

## 📊 Manual Notification Examples

### Scenario 1: Breaking News Alert
When important market news breaks outside of scheduled times:

1. **Admin sends**: `/notify`
2. **Bot responds**: Generates fresh news summary
3. **All subscribers receive**: Immediate notification with latest news
4. **Admin gets confirmation**: Summary of delivery results

### Scenario 2: Market Opening Update
If you want to send an update before the scheduled 9:30 AM time:

1. **Admin sends**: `/notify`
2. **Bot processes**: Current market sentiment and news
3. **Subscribers get**: Real-time market intelligence
4. **Admin sees**: Delivery statistics and confirmation

### Scenario 3: Custom Market Analysis
For special market conditions or events:

1. **Admin sends**: `/notify`
2. **Bot analyzes**: Latest news and market data
3. **Subscribers receive**: Timely market insights
4. **Admin tracks**: Notification delivery success

## 🔒 Security Features

### Access Control
- **Admin-only**: `/notify` and `/addadmin` commands
- **User verification**: Bot checks permissions before executing
- **Audit logging**: All admin actions are recorded

### Rate Limiting
- **Message limits**: Respects Telegram API limits (30 msg/sec)
- **User protection**: Prevents spam notifications
- **Error handling**: Graceful degradation on failures

## 📈 Notification Flow

```
Admin Command → Permission Check → News Generation → Subscriber Delivery → Confirmation
     ↓              ↓              ↓              ↓              ↓
  /notify      Admin Verify    Fetch RSS      Send to All    Success Report
```

## 🎯 Best Practices

### For Admins
1. **Use sparingly**: Don't spam subscribers with notifications
2. **Timing matters**: Send during market hours for relevance
3. **Monitor results**: Check delivery statistics after each notification
4. **Manage access**: Only grant admin to trusted users

### For Users
1. **Stay subscribed**: Get both scheduled and manual updates
2. **Engage actively**: Use `/news` for on-demand updates
3. **Provide feedback**: Let admins know about notification preferences

## 🚨 Troubleshooting

### Common Issues

**"Access Denied" error:**
- You need admin privileges to use `/notify`
- Contact the bot administrator for access

**No subscribers found:**
- Users must send `/start` and `/subscribe` first
- Check bot statistics with `/stats`

**Notification failed:**
- Some users may have blocked the bot
- Bot automatically unsubscribes blocked users
- Check logs for specific error details

### Getting Help
- **Check status**: Use `/status` to verify bot health
- **View logs**: Check console output for error messages
- **Test commands**: Use `/news` to verify news fetching works
- **Contact admin**: Ask bot administrator for assistance

## 📋 Example Session

Here's a typical admin session:

```
Admin: /start
Bot: Welcome message with admin features

Admin: /addadmin
Bot: You are now an administrator!

Admin: /notify
Bot: 🔔 MANUAL NOTIFICATION TRIGGERED
     [News summary sent to all subscribers]

Bot: ✅ Manual Notification Sent Successfully!
     • Successfully sent to: 15 users
     • Failed to send: 0 users
     • Total subscribers: 15 users
     • Sent at: January 15, 2025 at 14:30:25 EST
```

## 🔮 Advanced Usage

### Custom Notification Times
While the bot sends automatic updates at 9:00 AM and 9:30 AM, admins can:

- **Send updates anytime** using `/notify`
- **React to market events** with immediate notifications
- **Provide weekend updates** outside of weekday schedules
- **Send breaking news** as soon as it happens

### Admin Management
- **Grant access** to team members with `/addadmin`
- **Monitor usage** with `/stats` command
- **Control notifications** to prevent spam
- **Maintain security** with permission-based access

---

**💡 Tip**: The manual notification feature is perfect for sending timely market updates when important news breaks outside of scheduled times. Use it wisely to keep your subscribers informed!
