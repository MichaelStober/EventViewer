"""
Tests for main poster analyzer orchestrator.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

from poster_analyzer.analyzer import PosterAnalyzer
from poster_analyzer.data_models import EventData, EventKategorie


class TestPosterAnalyzer:
    """Test main poster analyzer functionality."""
    
    @pytest.fixture
    def mock_claude_analyzer(self, sample_event_data):
        """Mock Claude analyzer."""
        mock_analyzer = Mock()
        mock_analyzer.validate_api_key.return_value = True
        mock_analyzer.analyze_poster.return_value = sample_event_data
        return mock_analyzer
    
    @pytest.fixture
    def mock_qr_detector(self):
        """Mock QR detector."""
        mock_detector = Mock()
        mock_detector.detect_all.return_value = (
            ['https://tickets.test.de'],  # QR codes
            ['https://venue.test.de']     # URLs
        )
        mock_detector.validate_german_urls.return_value = ['https://venue.test.de']
        return mock_detector
    
    @pytest.fixture
    def analyzer(self, mock_claude_analyzer, mock_qr_detector):
        """Poster analyzer with mocked dependencies."""
        with patch('poster_analyzer.analyzer.ClaudeImageAnalyzer') as mock_claude_class, \
             patch('poster_analyzer.analyzer.QRCodeDetector') as mock_qr_class:
            
            mock_claude_class.return_value = mock_claude_analyzer
            mock_qr_class.return_value = mock_qr_detector
            
            return PosterAnalyzer('test-api-key')
    
    def test_initialization_success(self, mock_claude_analyzer):
        """Test successful analyzer initialization."""
        with patch('poster_analyzer.analyzer.ClaudeImageAnalyzer') as mock_claude_class, \
             patch('poster_analyzer.analyzer.QRCodeDetector'):
            
            mock_claude_class.return_value = mock_claude_analyzer
            
            analyzer = PosterAnalyzer('valid-api-key')
            
            assert analyzer.enable_web_scraping is True
            assert analyzer.scraping_timeout == 10
            mock_claude_analyzer.validate_api_key.assert_called_once()
    
    def test_initialization_invalid_api_key(self):
        """Test initialization with invalid API key."""
        mock_claude_analyzer = Mock()
        mock_claude_analyzer.validate_api_key.return_value = False
        
        with patch('poster_analyzer.analyzer.ClaudeImageAnalyzer') as mock_claude_class, \
             patch('poster_analyzer.analyzer.QRCodeDetector'):
            
            mock_claude_class.return_value = mock_claude_analyzer
            
            with pytest.raises(ValueError, match="Invalid Claude API key"):
                PosterAnalyzer('invalid-api-key')
    
    @pytest.mark.asyncio
    async def test_analyze_poster_success(self, analyzer, sample_event_data, sample_image_path):
        """Test successful poster analysis."""
        with patch('pathlib.Path.exists', return_value=True):
            result = await analyzer.analyze_poster(sample_image_path)
        
        assert result == sample_event_data
        analyzer.qr_detector.detect_all.assert_called_once_with(sample_image_path)
        analyzer.claude_analyzer.analyze_poster.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_poster_file_not_found(self, analyzer):
        """Test analysis with non-existent file."""
        with patch('pathlib.Path.exists', return_value=False):
            result = await analyzer.analyze_poster('nonexistent.jpg')
        
        assert result is None
        analyzer.qr_detector.detect_all.assert_not_called()
        analyzer.claude_analyzer.analyze_poster.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_analyze_poster_claude_failure(self, analyzer, sample_image_path):
        """Test analysis when Claude returns None."""
        analyzer.claude_analyzer.analyze_poster.return_value = None
        
        with patch('pathlib.Path.exists', return_value=True):
            result = await analyzer.analyze_poster(sample_image_path)
        
        assert result is None
    
    @pytest.mark.asyncio
    @patch('poster_analyzer.analyzer.WebScraper')
    async def test_analyze_poster_with_web_scraping(self, mock_web_scraper_class, 
                                                   analyzer, sample_event_data, sample_image_path):
        """Test poster analysis with web scraping enabled."""
        # Mock web scraper
        mock_scraper = AsyncMock()
        enhanced_data = sample_event_data.copy(deep=True)
        enhanced_data.metadaten.vertrauenswuerdigkeit = 0.9
        mock_scraper.enhance_event_data.return_value = enhanced_data
        
        mock_web_scraper_class.return_value.__aenter__ = AsyncMock(return_value=mock_scraper)
        mock_web_scraper_class.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('pathlib.Path.exists', return_value=True):
            result = await analyzer.analyze_poster(sample_image_path)
        
        assert result.metadaten.vertrauenswuerdigkeit == 0.9
        mock_scraper.enhance_event_data.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_poster_web_scraping_disabled(self, sample_event_data, sample_image_path):
        """Test analysis with web scraping disabled."""
        with patch('poster_analyzer.analyzer.ClaudeImageAnalyzer') as mock_claude_class, \
             patch('poster_analyzer.analyzer.QRCodeDetector') as mock_qr_class:
            
            mock_claude_analyzer = Mock()
            mock_claude_analyzer.validate_api_key.return_value = True
            mock_claude_analyzer.analyze_poster.return_value = sample_event_data
            mock_claude_class.return_value = mock_claude_analyzer
            
            mock_qr_detector = Mock()
            mock_qr_detector.detect_all.return_value = ([], [])
            mock_qr_detector.validate_german_urls.return_value = []
            mock_qr_class.return_value = mock_qr_detector
            
            analyzer = PosterAnalyzer('test-api-key', enable_web_scraping=False)
            
            with patch('pathlib.Path.exists', return_value=True), \
                 patch('poster_analyzer.analyzer.WebScraper') as mock_web_scraper:
                
                result = await analyzer.analyze_poster(sample_image_path)
                
                assert result == sample_event_data
                # Web scraper should not be instantiated
                mock_web_scraper.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_analyze_multiple_posters_success(self, analyzer, sample_event_data):
        """Test successful multiple poster analysis."""
        image_paths = ['image1.jpg', 'image2.jpg', 'image3.jpg']
        
        with patch.object(analyzer, 'analyze_poster') as mock_analyze:
            mock_analyze.return_value = sample_event_data
            
            results = await analyzer.analyze_multiple_posters(image_paths, max_concurrent=2)
        
        assert len(results) == 3
        assert all(isinstance(result, EventData) for result in results)
        assert mock_analyze.call_count == 3
    
    @pytest.mark.asyncio
    async def test_analyze_multiple_posters_partial_failure(self, analyzer, sample_event_data):
        """Test multiple poster analysis with some failures."""
        image_paths = ['image1.jpg', 'image2.jpg', 'image3.jpg']
        
        async def mock_analyze(path):
            if 'image2' in path:
                return None  # Simulate failure
            return sample_event_data
        
        with patch.object(analyzer, 'analyze_poster', side_effect=mock_analyze):
            results = await analyzer.analyze_multiple_posters(image_paths)
        
        assert len(results) == 2  # Only successful analyses
    
    @pytest.mark.asyncio
    async def test_analyze_multiple_posters_with_exceptions(self, analyzer, sample_event_data):
        """Test multiple poster analysis with exceptions."""
        image_paths = ['image1.jpg', 'image2.jpg']
        
        async def mock_analyze(path):
            if 'image2' in path:
                raise Exception("Simulated error")
            return sample_event_data
        
        with patch.object(analyzer, 'analyze_poster', side_effect=mock_analyze):
            results = await analyzer.analyze_multiple_posters(image_paths)
        
        assert len(results) == 1  # Only successful analysis
    
    @pytest.mark.asyncio
    @patch('poster_analyzer.analyzer.WebScraper')
    async def test_enhance_with_web_scraping_success(self, mock_web_scraper_class,
                                                    analyzer, sample_event_data):
        """Test successful web scraping enhancement."""
        mock_scraper = AsyncMock()
        enhanced_data = sample_event_data.copy(deep=True)
        enhanced_data.metadaten.vertrauenswuerdigkeit = 0.95
        mock_scraper.enhance_event_data.return_value = enhanced_data
        
        mock_web_scraper_class.return_value.__aenter__ = AsyncMock(return_value=mock_scraper)
        mock_web_scraper_class.return_value.__aexit__ = AsyncMock(return_value=None)
        
        urls = ['https://test.de']
        result = await analyzer._enhance_with_web_scraping(sample_event_data, urls)
        
        assert result.metadaten.vertrauenswuerdigkeit == 0.95
        mock_scraper.enhance_event_data.assert_called_once_with(sample_event_data, urls)
    
    @pytest.mark.asyncio
    @patch('poster_analyzer.analyzer.WebScraper')
    async def test_enhance_with_web_scraping_failure(self, mock_web_scraper_class,
                                                    analyzer, sample_event_data):
        """Test web scraping enhancement with failure."""
        mock_web_scraper_class.side_effect = Exception("Scraping failed")
        
        urls = ['https://test.de']
        result = await analyzer._enhance_with_web_scraping(sample_event_data, urls)
        
        # Should return original data on failure
        assert result == sample_event_data
    
    def test_assess_data_quality_complete_data(self, analyzer, sample_event_data):
        """Test data quality assessment with complete data."""
        # Add more complete data
        sample_event_data.metadaten.kontakt.telefon = "+49 30 1234567"
        sample_event_data.erkannte_links = ['https://test.de']
        sample_event_data.kategorie = EventKategorie.MUSIK
        
        original_confidence = sample_event_data.metadaten.vertrauenswuerdigkeit
        
        analyzer._assess_data_quality(sample_event_data)
        
        # Confidence should be improved for complete data
        assert sample_event_data.metadaten.vertrauenswuerdigkeit >= original_confidence
    
    def test_assess_data_quality_minimal_data(self, analyzer):
        """Test data quality assessment with minimal data."""
        minimal_event = EventData(veranstaltungsname="Minimal Event")
        
        analyzer._assess_data_quality(minimal_event)
        
        # Should have low confidence for minimal data
        assert minimal_event.metadaten.vertrauenswuerdigkeit <= 0.3
    
    def test_export_results_json(self, analyzer, sample_event_data, tmp_path):
        """Test exporting results to JSON."""
        output_path = tmp_path / "test_export.json"
        
        result = analyzer.export_results(sample_event_data, str(output_path), 'json')
        
        assert result is True
        assert output_path.exists()
        
        # Verify JSON content
        import json
        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert data['veranstaltungsname'] == sample_event_data.veranstaltungsname
    
    def test_export_results_csv(self, analyzer, sample_event_data, tmp_path):
        """Test exporting results to CSV."""
        output_path = tmp_path / "test_export.csv"
        
        result = analyzer.export_results(sample_event_data, str(output_path), 'csv')
        
        assert result is True
        assert output_path.exists()
        
        # Verify CSV content
        import csv
        with open(output_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            row = next(reader)
        
        assert row['veranstaltungsname'] == sample_event_data.veranstaltungsname
    
    def test_export_results_unsupported_format(self, analyzer, sample_event_data, tmp_path):
        """Test export with unsupported format."""
        output_path = tmp_path / "test_export.xml"
        
        result = analyzer.export_results(sample_event_data, str(output_path), 'xml')
        
        assert result is False
    
    def test_export_results_file_error(self, analyzer, sample_event_data):
        """Test export with file write error."""
        # Use an invalid path that can't be written to
        invalid_path = "/invalid/path/export.json"
        
        result = analyzer.export_results(sample_event_data, invalid_path, 'json')
        
        assert result is False
    
    def test_flatten_event_data(self, analyzer, sample_event_data):
        """Test event data flattening for CSV export."""
        # Add some complex data
        sample_event_data.metadaten.kuenstler = [
            {'name': 'Artist 1', 'info': 'Info 1'},
            {'name': 'Artist 2', 'info': 'Info 2'}
        ]
        
        flattened = analyzer._flatten_event_data(sample_event_data)
        
        assert isinstance(flattened, dict)
        assert flattened['veranstaltungsname'] == sample_event_data.veranstaltungsname
        assert flattened['kategorie'] == sample_event_data.kategorie.value
        assert 'Artist 1; Artist 2' in flattened['kuenstler']
    
    def test_flatten_event_data_with_datetime(self, analyzer):
        """Test flattening with datetime fields."""
        from datetime import datetime
        
        event = EventData(
            veranstaltungsname="Test Event",
            termine={
                'beginn': datetime(2024, 12, 1, 20, 0),
                'ende': datetime(2024, 12, 1, 23, 0)
            }
        )
        
        flattened = analyzer._flatten_event_data(event)
        
        assert flattened['beginn'] == '2024-12-01T20:00:00'
        assert flattened['ende'] == '2024-12-01T23:00:00'
    
    def test_error_handling_during_analysis(self, analyzer, sample_image_path):
        """Test error handling during analysis process."""
        # Mock an exception in QR detection
        analyzer.qr_detector.detect_all.side_effect = Exception("QR detection failed")
        
        with patch('pathlib.Path.exists', return_value=True):
            result = asyncio.run(analyzer.analyze_poster(sample_image_path))
        
        assert result is None
    
    def test_logging_during_analysis(self, analyzer, sample_event_data, sample_image_path):
        """Test that appropriate logging occurs during analysis."""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('poster_analyzer.analyzer.logger') as mock_logger:
            
            asyncio.run(analyzer.analyze_poster(sample_image_path))
            
            # Should log info messages about analysis progress
            mock_logger.info.assert_called()
            
            # Check for specific log messages
            log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
            assert any('Starting analysis' in msg for msg in log_calls)
            assert any('Analysis completed' in msg for msg in log_calls)