"""
QR code and link detection from event poster images.
"""

import re
import logging
from typing import List, Tuple, Optional
from PIL import Image
import cv2
import numpy as np
from pyzbar import pyzbar
import validators


logger = logging.getLogger(__name__)


class QRCodeDetector:
    """Detects QR codes and URLs from event poster images."""
    
    def __init__(self):
        self.url_patterns = [
            # Standard HTTP/HTTPS URLs
            r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w*))?)?',
            # German domain patterns
            r'www\.[\w\-]+\.(?:de|com|org|net|info)',
            # Email addresses
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        ]
        
    def detect_qr_codes(self, image_path: str) -> List[str]:
        """
        Detect and decode QR codes from image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            List of decoded QR code data
        """
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Could not load image: {image_path}")
                return []
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply image preprocessing to improve QR detection
            preprocessed_images = self._preprocess_for_qr(gray)
            
            qr_data = []
            for processed_img in preprocessed_images:
                # Detect QR codes
                qr_codes = pyzbar.decode(processed_img)
                for qr in qr_codes:
                    decoded_data = qr.data.decode('utf-8')
                    if decoded_data not in qr_data:
                        qr_data.append(decoded_data)
                        logger.info(f"QR code detected: {decoded_data}")
            
            return qr_data
            
        except Exception as e:
            logger.error(f"Error detecting QR codes: {e}")
            return []
    
    def detect_urls_ocr(self, image_path: str) -> List[str]:
        """
        Detect URLs from image using OCR.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            List of detected URLs
        """
        try:
            # This is a simplified version - in production you'd use 
            # a more sophisticated OCR like pytesseract or EasyOCR
            image = cv2.imread(image_path)
            if image is None:
                return []
                
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply threshold to get black and white image
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # For now, returning empty list - OCR integration would go here
            # This would integrate with pytesseract to extract text
            # then apply URL pattern matching
            
            return []
            
        except Exception as e:
            logger.error(f"Error in OCR URL detection: {e}")
            return []
    
    def extract_urls_from_text(self, text: str) -> List[str]:
        """
        Extract URLs from text using regex patterns.
        
        Args:
            text: Text to search for URLs
            
        Returns:
            List of detected URLs
        """
        urls = []
        
        for pattern in self.url_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Validate URL
                if validators.url(match) or validators.domain(match):
                    if match not in urls:
                        urls.append(match)
        
        return urls
    
    def _preprocess_for_qr(self, gray_image: np.ndarray) -> List[np.ndarray]:
        """
        Apply various preprocessing techniques to improve QR detection.
        
        Args:
            gray_image: Grayscale image
            
        Returns:
            List of preprocessed images
        """
        images = [gray_image]  # Original
        
        # Binary threshold
        _, binary = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        images.append(binary)
        
        # Adaptive threshold
        adaptive = cv2.adaptiveThreshold(gray_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                       cv2.THRESH_BINARY, 11, 2)
        images.append(adaptive)
        
        # Gaussian blur + threshold
        blur = cv2.GaussianBlur(gray_image, (3, 3), 0)
        _, blur_thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        images.append(blur_thresh)
        
        return images
    
    def detect_all(self, image_path: str) -> Tuple[List[str], List[str]]:
        """
        Detect both QR codes and URLs from image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Tuple of (qr_codes, urls)
        """
        qr_codes = self.detect_qr_codes(image_path)
        urls = self.detect_urls_ocr(image_path)
        
        # Also extract URLs from QR code data
        for qr_data in qr_codes:
            qr_urls = self.extract_urls_from_text(qr_data)
            urls.extend(qr_urls)
        
        # Remove duplicates
        unique_urls = list(set(urls))
        
        return qr_codes, unique_urls
    
    def validate_german_urls(self, urls: List[str]) -> List[str]:
        """
        Filter and validate URLs, prioritizing German domains.
        
        Args:
            urls: List of URLs to validate
            
        Returns:
            List of valid URLs
        """
        valid_urls = []
        german_domains = ['.de', '.at', '.ch']  # German-speaking countries
        
        for url in urls:
            if validators.url(url):
                valid_urls.append(url)
            elif any(domain in url.lower() for domain in german_domains):
                # Try to fix common URL issues
                if not url.startswith(('http://', 'https://')):
                    fixed_url = f"https://{url}"
                    if validators.url(fixed_url):
                        valid_urls.append(fixed_url)
        
        # Sort by German domains first
        valid_urls.sort(key=lambda x: not any(domain in x.lower() for domain in german_domains))
        
        return valid_urls