"""
Database module for user management and statistics
"""

import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.connection_string = os.environ.get('DATABASE_URL')
        if not self.connection_string:
            raise ValueError("DATABASE_URL environment variable not found")
        
        self.init_tables()
    
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.connection_string)
    
    def init_tables(self):
        """Initialize database tables"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Users table
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS users (
                            user_id BIGINT PRIMARY KEY,
                            username VARCHAR(255),
                            first_name VARCHAR(255),
                            last_name VARCHAR(255),
                            is_banned BOOLEAN DEFAULT FALSE,
                            is_admin BOOLEAN DEFAULT FALSE,
                            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # Conversions table
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS conversions (
                            id SERIAL PRIMARY KEY,
                            user_id BIGINT REFERENCES users(user_id),
                            file_name VARCHAR(255),
                            file_size INTEGER,
                            conversion_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            success BOOLEAN DEFAULT TRUE
                        )
                    """)
                    
                    # Broadcast messages table
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS broadcasts (
                            id SERIAL PRIMARY KEY,
                            admin_id BIGINT,
                            message_text TEXT,
                            media_type VARCHAR(50),
                            media_file_id VARCHAR(255),
                            sent_count INTEGER DEFAULT 0,
                            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                conn.commit()
                logger.info("Database tables initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def add_user(self, user_id, username=None, first_name=None, last_name=None):
        """Add or update user in database"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO users (user_id, username, first_name, last_name, last_active)
                        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (user_id) 
                        DO UPDATE SET 
                            username = EXCLUDED.username,
                            first_name = EXCLUDED.first_name,
                            last_name = EXCLUDED.last_name,
                            last_active = CURRENT_TIMESTAMP
                    """, (user_id, username, first_name, last_name))
                conn.commit()
        except Exception as e:
            logger.error(f"Error adding user {user_id}: {e}")
    
    def ban_user(self, user_id):
        """Ban a user"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "UPDATE users SET is_banned = TRUE WHERE user_id = %s",
                        (user_id,)
                    )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error banning user {user_id}: {e}")
            return False
    
    def unban_user(self, user_id):
        """Unban a user"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "UPDATE users SET is_banned = FALSE WHERE user_id = %s",
                        (user_id,)
                    )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error unbanning user {user_id}: {e}")
            return False
    
    def is_user_banned(self, user_id):
        """Check if user is banned"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT is_banned FROM users WHERE user_id = %s",
                        (user_id,)
                    )
                    result = cursor.fetchone()
                    return result[0] if result else False
        except Exception as e:
            logger.error(f"Error checking ban status for user {user_id}: {e}")
            return False
    
    def is_admin(self, user_id):
        """Check if user is admin"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT is_admin FROM users WHERE user_id = %s",
                        (user_id,)
                    )
                    result = cursor.fetchone()
                    return result[0] if result else False
        except Exception as e:
            logger.error(f"Error checking admin status for user {user_id}: {e}")
            return False
    
    def set_admin(self, user_id, is_admin=True):
        """Set admin status for user"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "UPDATE users SET is_admin = %s WHERE user_id = %s",
                        (is_admin, user_id)
                    )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error setting admin status for user {user_id}: {e}")
            return False
    
    def add_conversion(self, user_id, file_name, file_size, success=True):
        """Log a conversion"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO conversions (user_id, file_name, file_size, success)
                        VALUES (%s, %s, %s, %s)
                    """, (user_id, file_name, file_size, success))
                conn.commit()
        except Exception as e:
            logger.error(f"Error logging conversion for user {user_id}: {e}")
    
    def get_stats(self):
        """Get bot statistics"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Total users
                    cursor.execute("SELECT COUNT(*) as total_users FROM users")
                    total_users = cursor.fetchone()['total_users']
                    
                    # Active users (last 7 days)
                    cursor.execute("""
                        SELECT COUNT(*) as active_users 
                        FROM users 
                        WHERE last_active >= CURRENT_TIMESTAMP - INTERVAL '7 days'
                    """)
                    active_users = cursor.fetchone()['active_users']
                    
                    # Total conversions
                    cursor.execute("SELECT COUNT(*) as total_conversions FROM conversions")
                    total_conversions = cursor.fetchone()['total_conversions']
                    
                    # Successful conversions
                    cursor.execute("SELECT COUNT(*) as success_conversions FROM conversions WHERE success = TRUE")
                    success_conversions = cursor.fetchone()['success_conversions']
                    
                    # Banned users
                    cursor.execute("SELECT COUNT(*) as banned_users FROM users WHERE is_banned = TRUE")
                    banned_users = cursor.fetchone()['banned_users']
                    
                    return {
                        'total_users': total_users,
                        'active_users': active_users,
                        'total_conversions': total_conversions,
                        'success_conversions': success_conversions,
                        'banned_users': banned_users,
                        'success_rate': round((success_conversions / total_conversions * 100) if total_conversions > 0 else 0, 2)
                    }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}
    
    def get_all_users(self):
        """Get all active users for broadcasting"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT user_id FROM users WHERE is_banned = FALSE")
                    return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []
    
    def log_broadcast(self, admin_id, message_text, media_type=None, media_file_id=None):
        """Log broadcast message"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO broadcasts (admin_id, message_text, media_type, media_file_id)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id
                    """, (admin_id, message_text, media_type, media_file_id))
                    return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error logging broadcast: {e}")
            return None
    
    def update_broadcast_count(self, broadcast_id, sent_count):
        """Update broadcast sent count"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "UPDATE broadcasts SET sent_count = %s WHERE id = %s",
                        (sent_count, broadcast_id)
                    )
                conn.commit()
        except Exception as e:
            logger.error(f"Error updating broadcast count: {e}")