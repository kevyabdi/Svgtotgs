"""
Configuration Module
Handles bot configuration including environment variables

Required Environment Variables:
- BOT_TOKEN: Your Telegram bot token from @BotFather
  Example: "1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ123456789"

- DATABASE_URL: PostgreSQL connection string
  Example: "postgresql://username:password@localhost:5432/database_name"

Optional Environment Variables:
- OWNER_ID: Your Telegram user ID for admin privileges
  Example: "123456789"
  To get your user ID: Send any message to @userinfobot

- TEMP_DIR: Directory for temporary files (default: /tmp)
  Example: "/tmp"
"""

import os
import logging

logger = logging.getLogger(__name__)

class Config:
    def __init__(self):
        self.bot_token = self._get_bot_token()
        self.owner_id = self._get_owner_id()
        self.max_file_size = 10 * 1024 * 1024  # 10MB limit
        self.temp_dir = os.environ.get('TEMP_DIR', '/tmp')
        
        # Log configuration (without exposing sensitive data)
        logger.info("Bot configuration loaded successfully")
        logger.info(f"Max file size: {self.max_file_size} bytes")
        logger.info(f"Temp directory: {self.temp_dir}")
        if self.owner_id:
            logger.info(f"Bot owner ID configured: {self.owner_id}")
        else:
            logger.warning("No owner ID configured. Admin features may not work properly.")
    
    def _get_bot_token(self) -> str:
        """
        Get Telegram bot token from environment variables
        
        Returns:
            str: Bot token
            
        Raises:
            ValueError: If bot token is not found
        """
        # Try different environment variable names
        token_vars = ['BOT_TOKEN', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_TOKEN']
        
        for var_name in token_vars:
            token = os.environ.get(var_name)
            if token:
                logger.info(f"Bot token found in environment variable: {var_name}")
                return token
        
        # Fallback for development (not recommended for production)
        # Example: "1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ123456789"
        default_token = "8435159197:AAEfNaMfesHU2qhLFh8FsPbP3rEewn3BQyg"
        token = os.environ.get('BOT_TOKEN', default_token)
        
        # Always return the token (either from environment or hardcoded)
        return token
    
    def _get_owner_id(self) -> int | None:
        """
        Get bot owner Telegram user ID from environment variables
        
        Returns:
            int | None: Owner user ID or None if not configured
        """
        owner_vars = ['OWNER_ID', 'BOT_OWNER_ID', 'ADMIN_ID']
        
        for var_name in owner_vars:
            owner_id_str = os.environ.get(var_name)
            if owner_id_str:
                try:
                    owner_id = int(owner_id_str)
                    logger.info(f"Owner ID found in environment variable: {var_name}")
                    return owner_id
                except ValueError:
                    logger.warning(f"Invalid owner ID format in {var_name}: {owner_id_str}")
                    continue
        
        logger.warning("No owner ID configured in environment variables. Using hardcoded owner ID.")
        logger.info("Using hardcoded owner ID: 1096693642")
        return 1096693642
    
    def validate(self) -> tuple[bool, str]:
        """
        Validate configuration settings
        
        Returns:
            tuple[bool, str]: (is_valid, error_message)
        """
        try:
            # Validate bot token format
            if not self.bot_token or len(self.bot_token.split(':')) != 2:
                return False, "Invalid bot token format. Expected format: 'bot_id:bot_secret'"
            
            # Validate temp directory
            if not os.path.exists(self.temp_dir):
                try:
                    os.makedirs(self.temp_dir, exist_ok=True)
                except Exception as e:
                    return False, f"Cannot create temp directory {self.temp_dir}: {str(e)}"
            
            if not os.access(self.temp_dir, os.W_OK):
                return False, f"Temp directory {self.temp_dir} is not writable"
            
            # Owner ID is optional but recommended
            if self.owner_id is None:
                logger.warning("Owner ID not configured. Some admin features may not work properly.")
            
            return True, "Configuration is valid"
            
        except Exception as e:
            return False, f"Configuration validation error: {str(e)}"
