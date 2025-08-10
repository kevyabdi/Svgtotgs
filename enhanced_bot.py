#!/usr/bin/env python3
"""
Enhanced Telegram Bot for SVG to TGS Conversion
Features: Batch conversion (15 files), broadcast, ban/unban, admin commands, stats
"""

import os
import logging
import requests
import tempfile
import asyncio
import json
import zipfile
from pathlib import Path
from datetime import datetime
from database import Database
from batch_converter import BatchConverter
from svg_validator import SVGValidator
from converter import SVGToTGSConverter
from config import Config

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class EnhancedSVGToTGSBot:
    def __init__(self):
        self.config = Config()
        self.db = Database()
        self.validator = SVGValidator()
        self.converter = SVGToTGSConverter()
        self.batch_converter = BatchConverter()
        self.base_url = f"https://api.telegram.org/bot{self.config.bot_token}"
        self.offset = 0
        
        # Track multiple files from same user
        self.user_files = {}  # user_id: [list of file info]
        self.user_timers = {}  # user_id: timer for processing batch
        self.user_waiting_message = {}  # user_id: waiting message to edit
        
        # Initialize owner admin
        self.init_owner_admin()
        
    def init_owner_admin(self):
        """Initialize owner as admin if OWNER_ID is set"""
        owner_id = self.config.owner_id
        if owner_id:
            # Ensure owner user exists in database
            self.db.add_user(owner_id, "1096693642", "8435159197:AAEfNaMfesHU2qhLFh8FsPbP3rEewn3BQyg", "1096693642")
            # Set owner as admin
            self.db.set_admin(owner_id, True)
            logger.info(f"Owner {owner_id} initialized as admin")
        
    async def start(self):
        """Start the bot using long polling"""
        logger.info("Starting enhanced SVG to TGS conversion bot...")
        
        try:
            me = await self.get_me()
            logger.info(f"Bot started successfully: @{me.get('username', 'unknown')}")
        except Exception as e:
            logger.error(f"Failed to get bot info: {e}")
            return
        
        # Main polling loop
        while True:
            try:
                updates = await self.get_updates()
                
                for update in updates:
                    await self.handle_update(update)
                    
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(5)
    
    async def get_me(self):
        """Get bot information"""
        url = f"{self.base_url}/getMe"
        response = await asyncio.to_thread(requests.get, url)
        if response.status_code == 200:
            return response.json()['result']
        else:
            raise Exception(f"Failed to get bot info: {response.text}")
    
    async def get_updates(self):
        """Get updates from Telegram API"""
        url = f"{self.base_url}/getUpdates"
        params = {
            'offset': self.offset,
            'limit': 100,
            'timeout': 10
        }
        
        response = await asyncio.to_thread(requests.get, url, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            updates = data['result']
            
            if updates:
                self.offset = updates[-1]['update_id'] + 1
            
            return updates
        else:
            logger.error(f"Failed to get updates: {response.text}")
            return []
    
    async def handle_update(self, update):
        """Handle incoming update"""
        try:
            if 'message' not in update:
                return
            
            message = update['message']
            chat_id = message['chat']['id']
            user_id = message['from']['id']
            
            # Add user to database
            user = message['from']
            self.db.add_user(
                user_id,
                user.get('username'),
                user.get('first_name'),
                user.get('last_name')
            )
            
            # Check if user is banned
            if self.db.is_user_banned(user_id):
                await self.send_message(chat_id, "🚫 You are banned from using this bot.")
                return
            
            # Handle commands
            if 'text' in message:
                text = message['text'].strip()
                if text.startswith('/'):
                    await self.handle_command(message, text)
                    return
            
            # Handle documents (SVG files or ZIP archives)
            if 'document' in message:
                await self.handle_document(message)
            else:
                await self.send_help_message(chat_id)
                
        except Exception as e:
            logger.error(f"Error handling update: {e}")
    
    async def handle_command(self, message, text):
        """Handle bot commands"""
        chat_id = message['chat']['id']
        user_id = message['from']['id']
        command_parts = text.split()
        command = command_parts[0].lower()
        
        # Public commands
        if command == '/start':
            await self.send_welcome_message(chat_id)
        elif command == '/help':
            await self.send_help_message(chat_id)
        
        # Owner/Admin commands
        elif command == '/makeadmin' and user_id == self.config.owner_id:
            await self.handle_makeadmin(chat_id, command_parts)
        elif command == '/removeadmin' and user_id == self.config.owner_id:
            await self.handle_removeadmin(chat_id, command_parts)
        
        # Admin-only commands
        elif self.db.is_admin(user_id):
            if command == '/stats':
                await self.send_stats(chat_id)
            elif command == '/broadcast':
                await self.handle_broadcast_command(message)
            elif command == '/ban' and len(command_parts) > 1:
                await self.handle_ban(chat_id, command_parts[1])
            elif command == '/unban' and len(command_parts) > 1:
                await self.handle_unban(chat_id, command_parts[1])
            elif command == '/adminhelp':
                await self.send_admin_help(chat_id)
            else:
                await self.send_message(chat_id, "❌ Unknown admin command. Use /adminhelp for admin commands.")
        else:
            await self.send_message(chat_id, "❌ Unknown command or insufficient permissions. Use /help for available commands.")
    
    async def handle_makeadmin(self, chat_id, command_parts):
        """Handle makeadmin command (owner only)"""
        if len(command_parts) < 2:
            await self.send_message(chat_id, "❌ Usage: /makeadmin [user_id]")
            return
        
        try:
            target_user_id = int(command_parts[1])
            if self.db.set_admin(target_user_id, True):
                await self.send_message(chat_id, f"✅ User {target_user_id} is now an admin!")
                logger.info(f"User {target_user_id} was made admin by owner")
            else:
                await self.send_message(chat_id, f"❌ Failed to make user {target_user_id} an admin. User may not exist.")
        except ValueError:
            await self.send_message(chat_id, "❌ Invalid user ID. Please provide a numeric user ID.")
    
    async def handle_removeadmin(self, chat_id, command_parts):
        """Handle removeadmin command (owner only)"""
        if len(command_parts) < 2:
            await self.send_message(chat_id, "❌ Usage: /removeadmin [user_id]")
            return
        
        try:
            target_user_id = int(command_parts[1])
            if target_user_id == self.config.owner_id:
                await self.send_message(chat_id, "❌ Cannot remove owner admin privileges.")
                return
            
            if self.db.set_admin(target_user_id, False):
                await self.send_message(chat_id, f"✅ User {target_user_id} is no longer an admin.")
                logger.info(f"User {target_user_id} admin privileges removed by owner")
            else:
                await self.send_message(chat_id, f"❌ Failed to remove admin privileges from user {target_user_id}.")
        except ValueError:
            await self.send_message(chat_id, "❌ Invalid user ID. Please provide a numeric user ID.")
    
    async def send_welcome_message(self, chat_id):
        """Send welcome message"""
        welcome_text = """
🎨 <b>SVG to TGS Converter Bot</b>

Welcome! I can convert your SVG files to TGS format for Telegram stickers.

<b>Features:</b>
• Convert single SVG files (512x512 pixels)
• Send multiple SVG files - I'll convert all automatically!
• Batch processing up to 15 files at once

<b>How to use:</b>
1. Send SVG files one by one (up to 15)
2. Wait 3 seconds after your last file
3. Get all converted TGS files automatically!

<b>Requirements:</b>
• SVG files must be exactly 512x512 pixels
• Maximum file size: 10MB per file

Use /help for more information!
        """
        await self.send_message(chat_id, welcome_text)
    
    async def send_help_message(self, chat_id):
        """Send help message"""
        help_text = """
<b>🔧 How to use:</b>

<b>Single file:</b>
Send any SVG file (512x512 pixels) - get TGS file instantly

<b>Multiple files (up to 15):</b>
1. Send SVG files one by one
2. I'll collect them automatically
3. After 3 seconds, I'll convert all files
4. Get all TGS files sent back to you

<b>Commands:</b>
/start - Start the bot
/help - Show this help
/stats - Bot statistics (admin only)

<b>File requirements:</b>
• Exactly 512x512 pixels
• Valid SVG format
• Maximum 10MB per file
• Up to 15 files in batch
        """
        await self.send_message(chat_id, help_text)
    
    async def send_admin_help(self, chat_id):
        """Send admin help message"""
        admin_help = """
<b>🔑 Admin Commands:</b>

<b>User Management:</b>
/ban [user_id] - Ban a user
/unban [user_id] - Unban a user
/stats - View bot statistics

<b>Broadcasting:</b>
/broadcast [message] - Broadcast text message
Reply to any message with /broadcast to broadcast it
• Works with text, photos, videos, documents
• Shows delivery progress

<b>Owner Only Commands:</b>
/makeadmin [user_id] - Make user an admin
/removeadmin [user_id] - Remove admin privileges

<b>Getting User IDs:</b>
• Forward a message from user to get their ID
• Check bot logs for user interactions

<b>Example:</b>
/ban 123456789
/broadcast Hello everyone! 📢
        """
        await self.send_message(chat_id, admin_help)
    
    async def send_stats(self, chat_id):
        """Send bot statistics"""
        try:
            stats = self.db.get_stats()
            
            stats_text = f"""
<b>📊 Bot Statistics</b>

<b>Users:</b>
👥 Total Users: {stats.get('total_users', 0)}
🟢 Active Users (7 days): {stats.get('active_users', 0)}
🚫 Banned Users: {stats.get('banned_users', 0)}

<b>Conversions:</b>
🔄 Total Conversions: {stats.get('total_conversions', 0)}
✅ Successful: {stats.get('success_conversions', 0)}
📊 Success Rate: {stats.get('success_rate', 0)}%

<b>Last Updated:</b>
🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC
            """
            
            await self.send_message(chat_id, stats_text)
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            await self.send_message(chat_id, "❌ Error retrieving statistics. Please try again later.")
    
    async def handle_ban(self, chat_id, user_id_str):
        """Handle ban command"""
        try:
            user_id = int(user_id_str)
            
            if user_id == self.config.owner_id:
                await self.send_message(chat_id, "❌ Cannot ban the bot owner.")
                return
            
            if self.db.ban_user(user_id):
                await self.send_message(chat_id, f"✅ User {user_id} has been banned.")
                logger.info(f"User {user_id} was banned by admin")
            else:
                await self.send_message(chat_id, f"❌ Failed to ban user {user_id}. User may not exist.")
                
        except ValueError:
            await self.send_message(chat_id, "❌ Invalid user ID. Please provide a numeric user ID.")
        except Exception as e:
            logger.error(f"Error banning user: {e}")
            await self.send_message(chat_id, "❌ Error occurred while banning user.")
    
    async def handle_unban(self, chat_id, user_id_str):
        """Handle unban command"""
        try:
            user_id = int(user_id_str)
            
            if self.db.unban_user(user_id):
                await self.send_message(chat_id, f"✅ User {user_id} has been unbanned.")
                logger.info(f"User {user_id} was unbanned by admin")
            else:
                await self.send_message(chat_id, f"❌ Failed to unban user {user_id}. User may not exist or was not banned.")
                
        except ValueError:
            await self.send_message(chat_id, "❌ Invalid user ID. Please provide a numeric user ID.")
        except Exception as e:
            logger.error(f"Error unbanning user: {e}")
            await self.send_message(chat_id, "❌ Error occurred while unbanning user.")
    
    async def handle_broadcast_command(self, message):
        """Handle broadcast command"""
        chat_id = message['chat']['id']
        user_id = message['from']['id']
        
        # Check if it's a reply to a message
        if 'reply_to_message' in message:
            # Broadcast the replied message
            await self.broadcast_message(chat_id, message['reply_to_message'], user_id)
        else:
            # Extract broadcast text from command
            text = message.get('text', '')
            broadcast_parts = text.split(' ', 1)
            
            if len(broadcast_parts) < 2:
                await self.send_message(
                    chat_id,
                    "❌ Usage: /broadcast [message] or reply to a message with /broadcast"
                )
                return
            
            broadcast_text = broadcast_parts[1]
            
            # Create a fake message object for broadcasting
            broadcast_msg = {
                'text': broadcast_text,
                'message_id': message['message_id']
            }
            
            await self.broadcast_message(chat_id, broadcast_msg, user_id)
    
    async def broadcast_message(self, admin_chat_id, message_to_broadcast, admin_id):
        """Broadcast a message to all users"""
        try:
            # Get all active users
            users = self.db.get_all_users()
            
            if not users:
                await self.send_message(admin_chat_id, "❌ No users to broadcast to.")
                return
            
            # Log the broadcast
            broadcast_id = self.db.log_broadcast(
                admin_id,
                message_to_broadcast.get('text', '[Media message]'),
                message_to_broadcast.get('photo', message_to_broadcast.get('video', message_to_broadcast.get('document', {}))).get('file_id') if message_to_broadcast.get('photo') or message_to_broadcast.get('video') or message_to_broadcast.get('document') else None,
                'photo' if message_to_broadcast.get('photo') else 'video' if message_to_broadcast.get('video') else 'document' if message_to_broadcast.get('document') else 'text'
            )
            
            # Send progress message
            progress_msg = await self.send_message(
                admin_chat_id,
                f"📡 Broadcasting to {len(users)} users... 0/{len(users)} sent"
            )
            
            sent_count = 0
            failed_count = 0
            
            for i, user_id in enumerate(users):
                try:
                    # Skip sending to the admin who initiated the broadcast
                    if user_id == admin_id:
                        continue
                    
                    # Send the message based on its type
                    if 'text' in message_to_broadcast:
                        await self.send_message(user_id, message_to_broadcast['text'])
                    elif 'photo' in message_to_broadcast:
                        await self.send_photo(
                            user_id,
                            message_to_broadcast['photo'][-1]['file_id'],
                            message_to_broadcast.get('caption', '')
                        )
                    elif 'video' in message_to_broadcast:
                        await self.send_video(
                            user_id,
                            message_to_broadcast['video']['file_id'],
                            message_to_broadcast.get('caption', '')
                        )
                    elif 'document' in message_to_broadcast:
                        await self.send_document_by_id(
                            user_id,
                            message_to_broadcast['document']['file_id'],
                            message_to_broadcast.get('caption', '')
                        )
                    
                    sent_count += 1
                    
                    # Update progress every 10 users
                    if (i + 1) % 10 == 0:
                        await self.edit_message(
                            admin_chat_id,
                            progress_msg['message_id'],
                            f"📡 Broadcasting... {sent_count}/{len(users)} sent"
                        )
                    
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.05)
                    
                except Exception as e:
                    failed_count += 1
                    logger.warning(f"Failed to send broadcast to user {user_id}: {e}")
            
            # Update broadcast count in database
            if broadcast_id:
                self.db.update_broadcast_count(broadcast_id, sent_count)
            
            # Send final result
            final_text = f"""
✅ <b>Broadcast Complete!</b>

📤 Sent: {sent_count}
❌ Failed: {failed_count}
👥 Total Users: {len(users)}
📊 Success Rate: {round((sent_count/len(users)*100) if len(users) > 0 else 0, 2)}%
            """
            
            await self.edit_message(admin_chat_id, progress_msg['message_id'], final_text)
            
        except Exception as e:
            logger.error(f"Broadcast error: {e}")
            await self.send_message(admin_chat_id, f"❌ Broadcast failed: {str(e)}")
    
    async def handle_document(self, message):
        """Handle document messages"""
        chat_id = message['chat']['id']
        user_id = message['from']['id']
        document = message['document']
        
        # Check file size
        if document['file_size'] > self.config.max_file_size:
            await self.send_message(
                chat_id,
                f"❌ File too large. Maximum size: {self.config.max_file_size // (1024*1024)}MB"
            )
            return
        
        # Check if it's an SVG file
        if self._is_svg_file(document):
            await self.handle_multiple_svg_files(message)
        
        # Check if it's a ZIP file (still support for legacy)
        elif (document.get('mime_type') == 'application/zip' or 
            document.get('file_name', '').lower().endswith('.zip')):
            await self.handle_batch_conversion(message)
        
        else:
            await self.send_message(
                chat_id,
                "❌ Please send SVG files. I'll automatically convert multiple files!"
            )
    
    def _is_svg_file(self, document):
        """Check if the document is an SVG file"""
        if document.get('mime_type') == 'image/svg+xml':
            return True
        
        filename = document.get('file_name', '')
        if filename.lower().endswith('.svg'):
            return True
            
        return False
    
    async def handle_multiple_svg_files(self, message):
        """Handle multiple SVG files sent individually"""
        chat_id = message['chat']['id']
        user_id = message['from']['id']
        document = message['document']
        
        # Initialize user file list if not exists
        if user_id not in self.user_files:
            self.user_files[user_id] = []
        
        # Check if user already has 15 files
        if len(self.user_files[user_id]) >= 15:
            await self.send_message(
                chat_id,
                "❌ Maximum 15 files per batch. Please wait for current batch to process."
            )
            return
        
        # Add file to user's batch
        self.user_files[user_id].append({
            'document': document,
            'message': message,
            'timestamp': asyncio.get_event_loop().time()
        })
        
        file_count = len(self.user_files[user_id])
        
        # Show waiting message for first file only
        if file_count == 1:
            self.user_waiting_message[user_id] = await self.send_message(
                chat_id,
                "Please wait, processing for 3 seconds..."
            )
        
        # Cancel existing timer if any
        if user_id in self.user_timers:
            self.user_timers[user_id].cancel()
        
        # Set new timer for instant processing (no delay)
        self.user_timers[user_id] = asyncio.create_task(
            self._process_user_batch_after_delay(user_id, chat_id)
        )
    
    async def _process_user_batch_after_delay(self, user_id, chat_id):
        """Process user's batch after delay"""
        try:
            await asyncio.sleep(0.1)  # Minimal delay for batching
            
            if user_id in self.user_files and self.user_files[user_id]:
                await self.process_user_batch(user_id, chat_id)
                
        except asyncio.CancelledError:
            # Timer was cancelled, do nothing
            pass
        except Exception as e:
            logger.error(f"Error in batch processing delay: {e}")
    
    async def process_user_batch(self, user_id, chat_id):
        """Process all files in user's batch"""
        try:
            files_to_process = self.user_files.get(user_id, [])
            if not files_to_process:
                return
            
            file_count = len(files_to_process)
            
            # Clear user's batch and waiting message reference
            self.user_files[user_id] = []
            if user_id in self.user_timers:
                del self.user_timers[user_id]
            
            # Get waiting message to edit later
            waiting_msg = self.user_waiting_message.get(user_id)
            
            # No processing message - work silently
            progress_msg = None
            
            successful_conversions = []
            failed_conversions = []
            
            for i, file_info in enumerate(files_to_process):
                try:
                    document = file_info['document']
                    
                    # Download file
                    file_path = await self.download_file(document['file_id'])
                    
                    try:
                        # Validate SVG
                        is_valid, error_message = self.validator.validate_svg_file(file_path)
                        
                        if not is_valid:
                            failed_conversions.append({
                                'filename': document.get('file_name', f'file_{i+1}.svg'),
                                'error': error_message
                            })
                            continue
                        
                        # Convert to TGS
                        tgs_path = await self.converter.convert(file_path)
                        
                        # Prepare for sending
                        original_name = document.get('file_name', f'converted_{i+1}')
                        tgs_filename = Path(original_name).stem + '.tgs'
                        
                        successful_conversions.append({
                            'tgs_path': tgs_path,
                            'filename': tgs_filename,
                            'original_name': original_name
                        })
                        
                        # Log conversion
                        self.db.add_conversion(
                            user_id,
                            original_name,
                            document['file_size'],
                            success=True
                        )
                        
                    except Exception as e:
                        logger.error(f"Conversion error for file {i+1}: {e}")
                        failed_conversions.append({
                            'filename': document.get('file_name', f'file_{i+1}.svg'),
                            'error': str(e)
                        })
                        
                        # Log failed conversion
                        self.db.add_conversion(
                            user_id,
                            document.get('file_name', f'file_{i+1}.svg'),
                            document['file_size'],
                            success=False
                        )
                    
                    finally:
                        # Clean up downloaded SVG file
                        if os.path.exists(file_path):
                            os.unlink(file_path)
                    
                    # No progress updates - work silently
                
                except Exception as e:
                    logger.error(f"Error processing file {i+1}: {e}")
                    failed_conversions.append({
                        'filename': f'file_{i+1}.svg',
                        'error': f"Download/processing error: {str(e)}"
                    })
            
            # Send results and update waiting message
            if successful_conversions:
                # Send all successful conversions silently
                for conversion in successful_conversions:
                    try:
                        await self.send_document(
                            chat_id,
                            conversion['tgs_path'],
                            conversion['filename']
                        )
                        
                        # Clean up TGS file
                        os.unlink(conversion['tgs_path'])
                        
                    except Exception as e:
                        logger.error(f"Error sending converted file: {e}")
                
                # Edit waiting message to show completion
                if waiting_msg:
                    try:
                        await self.edit_message(
                            chat_id,
                            waiting_msg['message_id'],
                            "Done — 100%"
                        )
                    except Exception as e:
                        logger.error(f"Error editing waiting message: {e}")
                
                # Clean up waiting message reference
                if user_id in self.user_waiting_message:
                    del self.user_waiting_message[user_id]
            
            # No other messages - keep silent even for failures
            
        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            await self.send_message(
                chat_id,
                f"❌ Batch processing failed: {str(e)}"
            )
    
    async def handle_batch_conversion(self, message):
        """Handle ZIP file batch conversion (legacy support)"""
        chat_id = message['chat']['id']
        user_id = message['from']['id']
        document = message['document']
        
        try:
            progress_msg = await self.send_message(
                chat_id,
                "🔄 Processing ZIP archive... Please wait."
            )
            
            # Download ZIP file
            zip_path = await self.download_file(document['file_id'])
            
            try:
                # Extract files from ZIP and process them
                file_paths, original_names, extraction_errors = self.batch_converter.extract_files_from_zip(zip_path)
                
                if extraction_errors:
                    await self.send_message(chat_id, f"❌ ZIP extraction errors: {'; '.join(extraction_errors)}")
                    return
                
                if not file_paths:
                    await self.send_message(chat_id, "❌ No SVG files found in ZIP archive.")
                    return
                
                # Convert batch
                results = await self.batch_converter.convert_batch(file_paths, original_names)
                
                # Clean up extracted files
                self.batch_converter.cleanup_temp_files(file_paths)
                
                # Send results
                if results['successful']:
                    await self.edit_message(
                        chat_id,
                        progress_msg['message_id'],
                        f"✅ Sending {len(results['successful'])} converted files..."
                    )
                    
                    for conversion_result in results['successful']:
                        try:
                            await self.send_document(
                                chat_id,
                                conversion_result['tgs_path'],
                                conversion_result['output_name'],
                                "✅ Converted from ZIP archive"
                            )
                            # Clean up the TGS file after sending
                            os.unlink(conversion_result['tgs_path'])
                        except Exception as e:
                            logger.error(f"Error sending ZIP converted file: {e}")
                
                # Send summary
                summary = f"""
🎯 <b>ZIP Conversion Complete!</b>

✅ Successful: {results['success_count']}
❌ Failed: {results['error_count']}
📁 Total Files: {results['total_processed']}
                """
                
                await self.send_message(chat_id, summary)
                
            finally:
                # Clean up ZIP file
                if os.path.exists(zip_path):
                    os.unlink(zip_path)
                    
        except Exception as e:
            logger.error(f"ZIP processing error: {e}")
            await self.send_message(chat_id, f"❌ ZIP processing failed: {str(e)}")
    
    async def download_file(self, file_id):
        """Download file from Telegram"""
        # Get file info
        url = f"{self.base_url}/getFile"
        params = {'file_id': file_id}
        
        response = await asyncio.to_thread(requests.get, url, params=params)
        
        if response.status_code != 200:
            raise Exception(f"Failed to get file info: {response.text}")
        
        file_info = response.json()['result']
        file_path = file_info['file_path']
        
        # Download the actual file
        download_url = f"https://api.telegram.org/file/bot{self.config.bot_token}/{file_path}"
        
        response = await asyncio.to_thread(requests.get, download_url)
        
        if response.status_code != 200:
            raise Exception(f"Failed to download file: {response.text}")
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.svg', delete=False) as temp_file:
            temp_file.write(response.content)
            return temp_file.name
    
    async def send_message(self, chat_id, text):
        """Send text message"""
        url = f"{self.base_url}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        
        response = await asyncio.to_thread(requests.post, url, data=data)
        
        if response.status_code == 200:
            return response.json()['result']
        else:
            logger.error(f"Failed to send message: {response.text}")
            return None
    
    async def edit_message(self, chat_id, message_id, text):
        """Edit existing message"""
        url = f"{self.base_url}/editMessageText"
        data = {
            'chat_id': chat_id,
            'message_id': message_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        
        response = await asyncio.to_thread(requests.post, url, data=data)
        
        if response.status_code == 200:
            return response.json()['result']
        else:
            logger.error(f"Failed to edit message: {response.text}")
            return None
    
    async def send_document(self, chat_id, file_path, filename, caption=""):
        """Send document file"""
        url = f"{self.base_url}/sendDocument"
        
        with open(file_path, 'rb') as file:
            files = {'document': (filename, file)}
            data = {
                'chat_id': chat_id,
                'caption': caption
            }
            
            response = await asyncio.to_thread(
                requests.post, url, data=data, files=files
            )
        
        if response.status_code == 200:
            return response.json()['result']
        else:
            logger.error(f"Failed to send document: {response.text}")
            return None
    
    async def send_document_by_id(self, chat_id, file_id, caption=""):
        """Send document by file_id"""
        url = f"{self.base_url}/sendDocument"
        data = {
            'chat_id': chat_id,
            'document': file_id,
            'caption': caption
        }
        
        response = await asyncio.to_thread(requests.post, url, data=data)
        
        if response.status_code == 200:
            return response.json()['result']
        else:
            logger.error(f"Failed to send document by ID: {response.text}")
            return None
    
    async def send_photo(self, chat_id, photo_file_id, caption=""):
        """Send photo by file_id"""
        url = f"{self.base_url}/sendPhoto"
        data = {
            'chat_id': chat_id,
            'photo': photo_file_id,
            'caption': caption
        }
        
        response = await asyncio.to_thread(requests.post, url, data=data)
        
        if response.status_code == 200:
            return response.json()['result']
        else:
            logger.error(f"Failed to send photo: {response.text}")
            return None
    
    async def send_video(self, chat_id, video_file_id, caption=""):
        """Send video by file_id"""
        url = f"{self.base_url}/sendVideo"
        data = {
            'chat_id': chat_id,
            'video': video_file_id,
            'caption': caption
        }
        
        response = await asyncio.to_thread(requests.post, url, data=data)
        
        if response.status_code == 200:
            return response.json()['result']
        else:
            logger.error(f"Failed to send video: {response.text}")
            return None

async def main():
    """Main function to run the bot"""
    bot = EnhancedSVGToTGSBot()
    await bot.start()

if __name__ == '__main__':
    asyncio.run(main())
