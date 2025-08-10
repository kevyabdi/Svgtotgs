# Overview

This project is an advanced Telegram bot that converts SVG files to TGS (Telegram Sticker) format. The bot provides both simple single-file conversion and advanced batch processing capabilities, supporting up to 15 SVG files at once through ZIP archives. It includes comprehensive user management, admin controls, broadcasting features, and detailed analytics for monitoring bot performance.

## Recent Changes (August 10, 2025)

✅ **Enhanced Owner Control System Successfully Deployed**
- Fixed admin control system with proper owner privileges
- Configured owner ID (1096693642) with full administrative access
- Enhanced admin commands: /broadcast, /ban, /unban, /stats working
- Owner-only commands: /makeadmin, /removeadmin implemented
- Bot running successfully as @warer2023bot
- PostgreSQL database connected with all user management tables created
- All dependencies installed and SVG to TGS conversion engine operational

✅ **Message Flow Optimized for Clean User Experience**
- Shows "Please wait, processing for 3 seconds..." when SVG uploaded
- Shows "Done — 100%" when TGS file is ready and sent
- Silent conversion process with no spam or extra messages
- Clean two-message flow as requested by user
- No confirmations, progress updates, or captions

✅ **Performance Optimizations for Instant Processing**
- Removed processing delay - instant message when SVG uploaded
- Optimized conversion settings for maximum speed
- Removed unnecessary optimization flags from converter
- Faster FPS processing (30 instead of 60) for quicker results
- Cleaned up project structure by removing extra folders

✅ **Deployment Setup Complete**
- Created comprehensive README with installation instructions
- Added Render deployment configuration (render.yaml)
- Added Heroku deployment support (Procfile, runtime.txt)
- Created deployment requirements file
- Ready for GitHub upload and cloud deployment

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Bot Framework Architecture

**Modular Design**: The application follows a comprehensive separation of concerns with specialized modules:
- `enhanced_bot.py` - Main bot implementation with advanced features including batch processing, admin controls, and user management
- `simple_bot.py` - Basic bot implementation for reference and fallback scenarios
- `app.py` - Web server wrapper providing health check endpoints for deployment platforms

**Message Handling**: Built using asynchronous long polling with the Telegram Bot API, implementing custom request handling rather than the python-telegram-bot library. The bot processes document messages, validates SVG files, and manages user interactions through a state-driven approach.

**Batch Processing System**: Implements concurrent SVG conversion using asyncio for processing up to 15 files simultaneously from ZIP archives. The system includes automatic result packaging, detailed error reporting per file, and progress tracking.

## Data Storage and User Management

**Database Layer**: PostgreSQL integration through psycopg2 with comprehensive user tracking including:
- User registration and profile management
- Conversion history and statistics
- Admin permissions and ban/unban functionality
- Activity monitoring and analytics

**File Management**: Temporary file handling with automatic cleanup, size validation (10MB limit), and secure file processing in isolated directories.

## Conversion Pipeline

**SVG Validation**: Strict validation system that enforces 512x512 pixel requirements, checks SVG format compliance, and validates content complexity before conversion attempts.

**TGS Conversion**: Utilizes python-lottie's `lottie_convert.py` command-line tool for SVG to TGS conversion, with fallback path detection and error handling for missing dependencies.

**Quality Control**: Implements conversion verification, file size optimization, and format validation to ensure TGS files meet Telegram's sticker requirements.

## Administrative Features

**User Management**: Complete admin system with ban/unban capabilities, user statistics, and permission management. Supports multiple admin users with configurable owner privileges.

**Broadcasting System**: Mass communication features supporting text messages, photos, videos, and documents with real-time progress tracking and delivery statistics.

**Analytics Dashboard**: Comprehensive statistics including user counts, conversion rates, success metrics, and system health monitoring.

## Deployment Architecture

**Platform Flexibility**: Configured for deployment on GitHub, Render, and Heroku with Flask-based health check endpoints and environment variable management.

**Process Management**: Threading approach with the Telegram bot running as a daemon thread while Flask handles HTTP health checks and monitoring endpoints.

**Configuration Management**: Environment-based configuration system supporting multiple token variable names and fallback mechanisms for development environments.

# External Dependencies

## Core Dependencies
- **python-lottie**: Primary conversion engine for SVG to TGS transformation
- **psycopg2-binary**: PostgreSQL database connectivity and operations
- **Flask**: Web server framework for deployment platform health checks
- **requests**: HTTP client for Telegram Bot API communication

## System Requirements
- **Python 3.11+**: Runtime environment with asyncio support
- **PostgreSQL**: Database server for user management and analytics
- **Telegram Bot API**: External service integration requiring bot token

## Environment Variables
- **BOT_TOKEN/TELEGRAM_BOT_TOKEN**: Telegram bot authentication token
- **DATABASE_URL**: PostgreSQL connection string
- **OWNER_ID**: Optional owner user ID for admin initialization
- **TEMP_DIR**: Temporary file storage directory (defaults to /tmp)

## Deployment Platforms
- **Render**: Primary deployment target with automatic PostgreSQL addon
- **Heroku**: Secondary deployment option with Heroku Postgres
- **GitHub**: Repository hosting with automated deployment workflows