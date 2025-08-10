"""
Batch SVG to TGS Converter
Handles multiple SVG files conversion in a single request
"""

import os
import tempfile
import zipfile
import asyncio
import logging
from pathlib import Path
from converter import SVGToTGSConverter
from svg_validator import SVGValidator

logger = logging.getLogger(__name__)

class BatchConverter:
    def __init__(self):
        self.converter = SVGToTGSConverter()
        self.validator = SVGValidator()
        self.max_files = 15  # Maximum 15 files per batch
    
    async def convert_batch(self, file_paths, original_names):
        """
        Convert multiple SVG files to TGS format
        
        Args:
            file_paths: List of paths to SVG files
            original_names: List of original file names
            
        Returns:
            dict: Results with successful conversions and errors
        """
        if len(file_paths) > self.max_files:
            raise ValueError(f"Too many files. Maximum {self.max_files} files allowed per batch.")
        
        results = {
            'successful': [],
            'failed': [],
            'total_processed': 0,
            'success_count': 0,
            'error_count': 0
        }
        
        conversion_tasks = []
        
        # Create conversion tasks for all files
        for i, (file_path, original_name) in enumerate(zip(file_paths, original_names)):
            task = self._convert_single_file(file_path, original_name, i)
            conversion_tasks.append(task)
        
        # Run conversions concurrently
        conversion_results = await asyncio.gather(*conversion_tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(conversion_results):
            results['total_processed'] += 1
            
            if isinstance(result, Exception):
                results['failed'].append({
                    'file': original_names[i],
                    'error': str(result)
                })
                results['error_count'] += 1
            else:
                if result['success']:
                    results['successful'].append(result)
                    results['success_count'] += 1
                else:
                    results['failed'].append({
                        'file': original_names[i],
                        'error': result['error']
                    })
                    results['error_count'] += 1
        
        return results
    
    async def _convert_single_file(self, file_path, original_name, index):
        """Convert a single SVG file"""
        try:
            # Validate SVG file
            is_valid, error_message = self.validator.validate_svg_file(file_path)
            
            if not is_valid:
                return {
                    'success': False,
                    'file': original_name,
                    'error': error_message
                }
            
            # Convert to TGS
            tgs_path = await self.converter.convert(file_path)
            
            # Get file size
            tgs_size = os.path.getsize(tgs_path)
            
            return {
                'success': True,
                'file': original_name,
                'tgs_path': tgs_path,
                'tgs_size': tgs_size,
                'output_name': Path(original_name).stem + '.tgs'
            }
            
        except Exception as e:
            logger.error(f"Error converting {original_name}: {e}")
            return {
                'success': False,
                'file': original_name,
                'error': str(e)
            }
    
    def create_result_archive(self, successful_conversions, failed_conversions):
        """
        Create a ZIP archive with converted TGS files and error report
        
        Returns:
            str: Path to the ZIP archive
        """
        # Create temporary ZIP file
        zip_fd, zip_path = tempfile.mkstemp(suffix='.zip')
        os.close(zip_fd)
        
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add successful conversions
                for conversion in successful_conversions:
                    tgs_path = conversion['tgs_path']
                    output_name = conversion['output_name']
                    
                    if os.path.exists(tgs_path):
                        zipf.write(tgs_path, f"converted/{output_name}")
                
                # Add error report if there are failures
                if failed_conversions:
                    error_report = "CONVERSION ERRORS REPORT\n"
                    error_report += "=" * 30 + "\n\n"
                    
                    for i, failure in enumerate(failed_conversions, 1):
                        error_report += f"{i}. File: {failure['file']}\n"
                        error_report += f"   Error: {failure['error']}\n\n"
                    
                    # Add error report to ZIP
                    zipf.writestr("ERRORS.txt", error_report)
            
            return zip_path
            
        except Exception as e:
            logger.error(f"Error creating result archive: {e}")
            if os.path.exists(zip_path):
                os.unlink(zip_path)
            raise
    
    def cleanup_temp_files(self, file_paths, tgs_paths=None):
        """Clean up temporary files"""
        # Clean up input files
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except Exception as e:
                logger.warning(f"Could not delete temp file {file_path}: {e}")
        
        # Clean up TGS files
        if tgs_paths:
            for tgs_path in tgs_paths:
                try:
                    if os.path.exists(tgs_path):
                        os.unlink(tgs_path)
                except Exception as e:
                    logger.warning(f"Could not delete TGS file {tgs_path}: {e}")
    
    def extract_files_from_zip(self, zip_path, max_files=None):
        """
        Extract SVG files from uploaded ZIP archive
        
        Returns:
            tuple: (file_paths, original_names, errors)
        """
        max_files = max_files or self.max_files
        file_paths = []
        original_names = []
        errors = []
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                svg_files = [f for f in zipf.namelist() 
                           if f.lower().endswith('.svg') and not f.startswith('__MACOSX/')]
                
                if len(svg_files) > max_files:
                    errors.append(f"Too many SVG files in archive. Maximum {max_files} files allowed.")
                    svg_files = svg_files[:max_files]
                
                for file_info in svg_files:
                    try:
                        # Extract file to temporary location
                        file_data = zipf.read(file_info)
                        
                        # Create temporary file
                        temp_fd, temp_path = tempfile.mkstemp(suffix='.svg')
                        with os.fdopen(temp_fd, 'wb') as temp_file:
                            temp_file.write(file_data)
                        
                        file_paths.append(temp_path)
                        original_names.append(os.path.basename(file_info))
                        
                    except Exception as e:
                        errors.append(f"Could not extract {file_info}: {str(e)}")
                
        except Exception as e:
            errors.append(f"Could not read ZIP archive: {str(e)}")
        
        return file_paths, original_names, errors