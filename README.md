# SVG to TGS Telegram Bot

An advanced Telegram bot that converts SVG files to TGS (Telegram Sticker) format with comprehensive admin controls and user management.

## Features

- **Fast SVG to TGS Conversion**: Optimized conversion process with minimal delay
- **Batch Processing**: Support for multiple SVG files (up to 15) simultaneously
- **Admin Control System**: Complete user management with ban/unban, broadcasting
- **Clean User Experience**: Minimal messaging with instant feedback
- **Database Integration**: PostgreSQL for user tracking and analytics

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL database
- Telegram Bot Token (from @BotFather)

### Environment Variables

```bash
BOT_TOKEN=your_telegram_bot_token
DATABASE_URL=your_postgresql_connection_string
OWNER_ID=your_telegram_user_id  # Optional: for admin privileges
```

### Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd svg-to-tgs-bot
```

2. Install dependencies:
```bash
pip install -r deploy-requirements.txt
# or using uv:
uv install
```

3. Set up your environment variables (see Environment Variables section)

4. Run the bot:
```bash
python enhanced_bot.py
```

## Deployment

### Render Deployment

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Use the following settings:
   - **Build Command**: `pip install -r deploy-requirements.txt`
   - **Start Command**: `python enhanced_bot.py`
   - **Environment**: Add your environment variables

### Heroku Deployment

1. Create a new Heroku app
2. Add Heroku Postgres addon
3. Set environment variables in Heroku Config Vars
4. Deploy using Git or GitHub integration

### Manual Server Deployment

1. Set up Python 3.11+ environment
2. Install PostgreSQL
3. Clone repository and install dependencies
4. Set environment variables
5. Run with process manager (pm2, supervisor, etc.)

## Admin Commands

### Owner-Only Commands
- `/makeadmin [user_id]` - Grant admin privileges
- `/removeadmin [user_id]` - Remove admin privileges

### Admin Commands
- `/broadcast [message]` - Send message to all users
- `/ban [user_id]` - Ban a user
- `/unban [user_id]` - Unban a user
- `/stats` - View bot statistics
- `/adminhelp` - List all admin commands

## User Experience

When users send SVG files to the bot:

1. **Instant Feedback**: "Please wait, processing for 3 seconds..."
2. **Fast Processing**: Optimized conversion (typically 1-5 seconds)
3. **Completion Notice**: Original message updates to "Done — 100%"
4. **File Delivery**: TGS file sent without extra messages

## File Requirements

- **Format**: SVG files only
- **Size**: Maximum 10MB per file
- **Dimensions**: Automatically resized to 512x512 pixels
- **Output**: TGS format suitable for Telegram stickers

## Architecture

- `enhanced_bot.py` - Main bot implementation
- `converter.py` - SVG to TGS conversion engine
- `database.py` - PostgreSQL integration
- `config.py` - Configuration management
- `svg_validator.py` - File validation
- `batch_converter.py` - Batch processing logic

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues or questions:
1. Check the logs for error messages
2. Verify environment variables are set correctly
3. Ensure PostgreSQL database is accessible
4. Confirm bot token is valid and bot is active