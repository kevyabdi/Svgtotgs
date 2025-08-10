"""
SVG to TGS Converter Module
Handles the conversion process from SVG files to TGS format using python-lottie
"""

import os
import subprocess
import tempfile
import logging
import asyncio
from pathlib import Path

logger = logging.getLogger(__name__)

class SVGToTGSConverter:
    def __init__(self):
        self.lottie_convert_path = self._find_lottie_convert()
    
    def _find_lottie_convert(self) -> str:
        """Find the lottie_convert.py executable"""
        # Common locations for lottie_convert.py
        possible_paths = [
            'lottie_convert.py',
            '/usr/local/bin/lottie_convert.py',
            '/usr/bin/lottie_convert.py',
            os.path.expanduser('~/.local/bin/lottie_convert.py')
        ]
        
        for path in possible_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                logger.info(f"Found lottie_convert.py at: {path}")
                return path
        
        # Try to find it in PATH
        try:
            result = subprocess.run(['which', 'lottie_convert.py'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                path = result.stdout.strip()
                logger.info(f"Found lottie_convert.py in PATH: {path}")
                return path
        except Exception:
            pass
        
        logger.warning("lottie_convert.py not found, will try 'lottie_convert.py' directly")
        return 'lottie_convert.py'
    
    async def convert(self, svg_path: str) -> str:
        """
        Convert SVG file to TGS format
        
        Args:
            svg_path (str): Path to the input SVG file
            
        Returns:
            str: Path to the generated TGS file
            
        Raises:
            Exception: If conversion fails
        """
        # Create temporary file for TGS output
        tgs_fd, tgs_path = tempfile.mkstemp(suffix='.tgs')
        os.close(tgs_fd)  # Close the file descriptor, we just need the path
        
        try:
            # Prepare conversion command with speed optimization
            cmd = [
                self.lottie_convert_path,
                svg_path,
                tgs_path,
                '--sanitize',           # Apply Telegram sticker requirements
                '--optimize', '0',      # No optimization for fastest speed
                '--fps', '30',          # Lower FPS for faster processing
                '--width', '512',       # Force width to 512
                '--height', '512'       # Force height to 512
            ]
            
            logger.info(f"Running conversion command: {' '.join(cmd)}")
            
            # Run conversion in subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            # Check if conversion was successful
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8') if stderr else "Unknown error"
                logger.error(f"Conversion failed with return code {process.returncode}: {error_msg}")
                raise Exception(f"Conversion failed: {error_msg}")
            
            # Check if output file exists and has content
            if not os.path.exists(tgs_path) or os.path.getsize(tgs_path) == 0:
                raise Exception("Conversion completed but no TGS file was generated")
            
            # Validate TGS file size (should be under 64KB for Telegram)
            file_size = os.path.getsize(tgs_path)
            if file_size > 64 * 1024:  # 64KB limit
                logger.warning(f"Generated TGS file is {file_size} bytes, which exceeds Telegram's 64KB limit")
                # Don't fail, but log the warning
            
            logger.info(f"Successfully converted SVG to TGS. Output file: {tgs_path} ({file_size} bytes)")
            return tgs_path
            
        except subprocess.SubprocessError as e:
            logger.error(f"Subprocess error during conversion: {e}")
            if os.path.exists(tgs_path):
                os.unlink(tgs_path)
            raise Exception(f"Conversion process failed: {str(e)}")
        
        except Exception as e:
            logger.error(f"Conversion error: {e}")
            if os.path.exists(tgs_path):
                os.unlink(tgs_path)
            raise
    
    def validate_dependencies(self) -> tuple[bool, str]:
        """
        Validate that all required dependencies are available
        
        Returns:
            tuple[bool, str]: (is_valid, error_message)
        """
        try:
            # Test lottie_convert.py
            result = subprocess.run([self.lottie_convert_path, '--help'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                return False, f"lottie_convert.py is not working properly: {result.stderr}"
            
            return True, "All dependencies are available"
            
        except subprocess.TimeoutExpired:
            return False, "lottie_convert.py is not responding"
        
        except FileNotFoundError:
            return False, "lottie_convert.py is not installed or not in PATH"
        
        except Exception as e:
            return False, f"Error checking dependencies: {str(e)}"