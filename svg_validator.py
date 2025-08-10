"""
SVG Validator Module
Validates SVG files to ensure they meet the 512x512 pixel requirement for TGS conversion
"""

import xml.etree.ElementTree as ET
import re
import logging

logger = logging.getLogger(__name__)

class SVGValidator:
    def __init__(self):
        self.required_width = 512
        self.required_height = 512
    
    def validate_svg_file(self, svg_path: str) -> tuple[bool, str]:
        """
        Validate an SVG file to ensure it meets TGS requirements
        
        Args:
            svg_path (str): Path to the SVG file
            
        Returns:
            tuple[bool, str]: (is_valid, error_message)
        """
        try:
            # Parse the SVG file
            tree = ET.parse(svg_path)
            root = tree.getroot()
            
            # Check if it's actually an SVG
            if not self._is_svg_element(root):
                return False, "File is not a valid SVG format."
            
            # Extract dimensions
            width, height = self._extract_dimensions(root)
            
            # Validate dimensions
            if width is None or height is None:
                return False, "Could not determine SVG dimensions. Please ensure your SVG has explicit width and height attributes."
            
            if width != self.required_width or height != self.required_height:
                return False, f"SVG must be exactly {self.required_width}x{self.required_height} pixels. Your file is {width}x{height} pixels."
            
            # Additional validations
            if not self._validate_content(root):
                return False, "SVG content is too complex or contains unsupported elements for TGS conversion."
            
            return True, "SVG is valid for TGS conversion."
            
        except ET.ParseError as e:
            logger.error(f"XML parsing error: {e}")
            return False, "Invalid SVG file format. The file appears to be corrupted."
        
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False, f"Error validating SVG file: {str(e)}"
    
    def _is_svg_element(self, element) -> bool:
        """Check if the root element is an SVG element"""
        # Handle namespace
        tag = element.tag.lower()
        return tag == 'svg' or tag.endswith('}svg')
    
    def _extract_dimensions(self, root) -> tuple[int | None, int | None]:
        """
        Extract width and height from SVG root element
        
        Returns:
            tuple[int | None, int | None]: (width, height) or (None, None) if not found
        """
        try:
            # Try to get width and height attributes directly
            width = self._parse_dimension(root.get('width'))
            height = self._parse_dimension(root.get('height'))
            
            if width is not None and height is not None:
                return int(width), int(height)
            
            # Try to get from viewBox if width/height not present
            viewbox = root.get('viewBox')
            if viewbox:
                viewbox_values = viewbox.strip().split()
                if len(viewbox_values) == 4:
                    # viewBox format: min-x min-y width height
                    width = float(viewbox_values[2])
                    height = float(viewbox_values[3])
                    return int(width), int(height)
            
            return None, None
            
        except (ValueError, TypeError) as e:
            logger.error(f"Dimension parsing error: {e}")
            return None, None
    
    def _parse_dimension(self, dimension_str: str) -> float | None:
        """
        Parse dimension string and convert to pixels
        
        Args:
            dimension_str (str): Dimension string (e.g., "512px", "512", "100%")
            
        Returns:
            float | None: Dimension in pixels or None if invalid
        """
        if not dimension_str:
            return None
        
        # Remove whitespace and convert to lowercase
        dimension_str = dimension_str.strip().lower()
        
        # Handle percentage (not supported for our use case)
        if dimension_str.endswith('%'):
            return None
        
        # Remove unit suffixes and extract number
        # Common units: px, pt, pc, mm, cm, in
        number_match = re.match(r'^(\d*\.?\d+)', dimension_str)
        if number_match:
            return float(number_match.group(1))
        
        return None
    
    def _validate_content(self, root) -> bool:
        """
        Basic content validation to ensure SVG is suitable for TGS conversion
        
        Args:
            root: SVG root element
            
        Returns:
            bool: True if content is acceptable
        """
        try:
            # Check file size (basic heuristic)
            svg_string = ET.tostring(root, encoding='unicode')
            if len(svg_string) > 1024 * 1024:  # 1MB limit
                logger.warning("SVG file is very large and may cause conversion issues")
                return False
            
            # Count elements to avoid overly complex SVGs
            element_count = len(list(root.iter()))
            if element_count > 1000:  # Arbitrary limit
                logger.warning(f"SVG has {element_count} elements, which may be too complex")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Content validation error: {e}")
            return False