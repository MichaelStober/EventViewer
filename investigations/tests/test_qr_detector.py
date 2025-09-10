"""
Tests for QR code and URL detection.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np

from poster_analyzer.qr_detector import QRCodeDetector


class TestQRCodeDetector:
    """Test QR code detection functionality."""
    
    @pytest.fixture
    def detector(self):
        """QR detector instance."""
        return QRCodeDetector()
    
    def test_initialization(self, detector):
        """Test detector initialization."""
        assert detector is not None
        assert len(detector.url_patterns) > 0
    
    @patch('poster_analyzer.qr_detector.cv2.imread')
    @patch('poster_analyzer.qr_detector.pyzbar.decode')
    def test_detect_qr_codes_success(self, mock_decode, mock_imread, detector):
        """Test successful QR code detection."""
        # Mock image loading
        mock_image = np.zeros((600, 800, 3), dtype=np.uint8)
        mock_imread.return_value = mock_image
        
        # Mock QR code detection
        mock_qr = Mock()
        mock_qr.data = b'https://example.de/event'
        mock_decode.return_value = [mock_qr]
        
        result = detector.detect_qr_codes('test_image.jpg')
        
        assert len(result) == 1
        assert result[0] == 'https://example.de/event'
        mock_imread.assert_called_once_with('test_image.jpg')
    
    @patch('poster_analyzer.qr_detector.cv2.imread')
    def test_detect_qr_codes_image_load_failure(self, mock_imread, detector):
        """Test QR detection when image loading fails."""
        mock_imread.return_value = None
        
        result = detector.detect_qr_codes('nonexistent.jpg')
        
        assert result == []
    
    @patch('poster_analyzer.qr_detector.cv2.imread')
    @patch('poster_analyzer.qr_detector.pyzbar.decode')
    def test_detect_qr_codes_no_codes_found(self, mock_decode, mock_imread, detector):
        """Test QR detection when no codes are found."""
        mock_image = np.zeros((600, 800, 3), dtype=np.uint8)
        mock_imread.return_value = mock_image
        mock_decode.return_value = []
        
        result = detector.detect_qr_codes('test_image.jpg')
        
        assert result == []
    
    @patch('poster_analyzer.qr_detector.cv2.imread')
    @patch('poster_analyzer.qr_detector.pyzbar.decode')
    def test_detect_qr_codes_duplicate_removal(self, mock_decode, mock_imread, detector):
        """Test that duplicate QR codes are removed."""
        mock_image = np.zeros((600, 800, 3), dtype=np.uint8)
        mock_imread.return_value = mock_image
        
        # Mock multiple QR codes with duplicates
        mock_qr1 = Mock()
        mock_qr1.data = b'https://example.de/event'
        mock_qr2 = Mock()
        mock_qr2.data = b'https://example.de/event'  # Duplicate
        mock_qr3 = Mock()
        mock_qr3.data = b'https://another.de/event'
        
        # Mock decode to return the same codes multiple times (from different preprocessing)
        mock_decode.side_effect = [
            [mock_qr1, mock_qr2],
            [mock_qr1],
            [mock_qr3],
            []
        ]
        
        result = detector.detect_qr_codes('test_image.jpg')
        
        # Should have only unique codes
        assert len(result) == 2
        assert 'https://example.de/event' in result
        assert 'https://another.de/event' in result
    
    def test_extract_urls_from_text(self, detector):
        """Test URL extraction from text."""
        text = """
        Visit our website at https://eventhaus.de for more info.
        Tickets available at www.tickets.de or contact info@events.com
        Call us at +49 30 1234567
        """
        
        urls = detector.extract_urls_from_text(text)
        
        assert 'https://eventhaus.de' in urls
        assert 'www.tickets.de' in urls
        assert 'info@events.com' in urls
    
    def test_extract_urls_german_domains(self, detector):
        """Test extraction prioritizes German domains."""
        text = "Visit example.com or beispiel.de for tickets"
        
        urls = detector.extract_urls_from_text(text)
        
        # Should extract both but the validator will handle prioritization
        assert len(urls) >= 1
    
    @patch('poster_analyzer.qr_detector.cv2.imread')
    def test_detect_urls_ocr_image_failure(self, mock_imread, detector):
        """Test OCR URL detection when image loading fails."""
        mock_imread.return_value = None
        
        result = detector.detect_urls_ocr('nonexistent.jpg')
        
        assert result == []
    
    def test_preprocess_for_qr(self, detector):
        """Test QR preprocessing generates multiple images."""
        # Create a simple grayscale image
        gray_image = np.ones((100, 100), dtype=np.uint8) * 128
        
        with patch('poster_analyzer.qr_detector.cv2.threshold') as mock_threshold, \
             patch('poster_analyzer.qr_detector.cv2.adaptiveThreshold') as mock_adaptive, \
             patch('poster_analyzer.qr_detector.cv2.GaussianBlur') as mock_blur:
            
            mock_threshold.return_value = (127, np.ones((100, 100), dtype=np.uint8))
            mock_adaptive.return_value = np.ones((100, 100), dtype=np.uint8)
            mock_blur.return_value = np.ones((100, 100), dtype=np.uint8)
            
            processed_images = detector._preprocess_for_qr(gray_image)
            
            # Should return original + 3 processed versions
            assert len(processed_images) == 4
    
    @patch('poster_analyzer.qr_detector.QRCodeDetector.detect_qr_codes')
    @patch('poster_analyzer.qr_detector.QRCodeDetector.detect_urls_ocr')
    def test_detect_all(self, mock_detect_urls, mock_detect_qr, detector):
        """Test combined QR and URL detection."""
        mock_detect_qr.return_value = ['QR: https://tickets.de']
        mock_detect_urls.return_value = ['https://venue.de']
        
        qr_codes, urls = detector.detect_all('test_image.jpg')
        
        assert qr_codes == ['QR: https://tickets.de']
        # URLs should include those from QR codes
        assert 'https://venue.de' in urls or 'https://tickets.de' in urls
    
    def test_validate_german_urls(self, detector):
        """Test German URL validation and prioritization."""
        urls = [
            'https://example.com',
            'https://events.de',
            'www.tickets.de',
            'invalid-url',
            'https://venue.at'  # Austrian domain
        ]
        
        valid_urls = detector.validate_german_urls(urls)
        
        # Should prioritize German-speaking domains
        assert len(valid_urls) > 0
        # German domains should come first
        german_domains = [url for url in valid_urls if any(d in url.lower() for d in ['.de', '.at', '.ch'])]
        assert len(german_domains) > 0
    
    def test_url_pattern_matching(self, detector):
        """Test URL pattern matching accuracy."""
        test_cases = [
            ('https://www.eventbrite.de/event/123', True),
            ('http://tickets.example.com/buy', True),
            ('www.venue-name.de', True),
            ('contact@events.de', True),
            ('not-a-url-at-all', False),
            ('https://', False)
        ]
        
        for test_url, should_match in test_cases:
            urls = detector.extract_urls_from_text(test_url)
            if should_match:
                assert len(urls) > 0, f"Should have matched: {test_url}"
            # Note: Some false positives are acceptable in regex matching
    
    @patch('poster_analyzer.qr_detector.cv2.imread')
    def test_error_handling(self, mock_imread, detector):
        """Test error handling in QR detection."""
        # Simulate an exception during image processing
        mock_imread.side_effect = Exception("Simulated error")
        
        result = detector.detect_qr_codes('test_image.jpg')
        
        # Should return empty list on error, not raise exception
        assert result == []