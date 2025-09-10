"""
Tests for Claude API client.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import base64
from pathlib import Path

from poster_analyzer.claude_client import ClaudeImageAnalyzer
from poster_analyzer.data_models import EventData, EventKategorie


class TestClaudeImageAnalyzer:
    """Test Claude image analysis functionality."""
    
    @pytest.fixture
    def analyzer(self, api_key):
        """Claude analyzer instance with mock API key."""
        with patch('poster_analyzer.claude_client.anthropic.Anthropic'):
            return ClaudeImageAnalyzer(api_key)
    
    def test_initialization(self, api_key):
        """Test analyzer initialization."""
        with patch('poster_analyzer.claude_client.anthropic.Anthropic') as mock_anthropic:
            analyzer = ClaudeImageAnalyzer(api_key)
            
            assert analyzer.model == "claude-3-5-sonnet-20241022"
            mock_anthropic.assert_called_once_with(api_key=api_key)
    
    @patch('poster_analyzer.claude_client.Image.open')
    def test_prepare_image_success(self, mock_image_open, analyzer, sample_image_path):
        """Test successful image preparation."""
        # Mock PIL Image
        mock_img = Mock()
        mock_img.mode = 'RGB'
        mock_img.size = (800, 600)
        
        # Mock BytesIO
        mock_buffer = Mock()
        mock_buffer.getvalue.return_value = b'fake_image_data'
        
        with patch('poster_analyzer.claude_client.io.BytesIO') as mock_bytesio, \
             patch('poster_analyzer.claude_client.base64.b64encode') as mock_b64encode:
            
            mock_image_open.return_value.__enter__.return_value = mock_img
            mock_bytesio.return_value = mock_buffer
            mock_b64encode.return_value = b'encoded_data'
            
            result = analyzer._prepare_image(sample_image_path)
            
            assert result == 'encoded_data'
            mock_img.save.assert_called_once()
    
    @patch('poster_analyzer.claude_client.Image.open')
    def test_prepare_image_resize_large(self, mock_image_open, analyzer, sample_image_path):
        """Test image resizing for large images."""
        mock_img = Mock()
        mock_img.mode = 'RGB'
        mock_img.size = (2000, 1500)  # Larger than max_size
        
        mock_buffer = Mock()
        mock_buffer.getvalue.return_value = b'fake_image_data'
        
        with patch('poster_analyzer.claude_client.io.BytesIO') as mock_bytesio, \
             patch('poster_analyzer.claude_client.base64.b64encode') as mock_b64encode:
            
            mock_image_open.return_value.__enter__.return_value = mock_img
            mock_bytesio.return_value = mock_buffer
            mock_b64encode.return_value = b'encoded_data'
            
            result = analyzer._prepare_image(sample_image_path)
            
            # Should call thumbnail to resize
            mock_img.thumbnail.assert_called_once()
            assert result == 'encoded_data'
    
    @patch('poster_analyzer.claude_client.Image.open')
    def test_prepare_image_convert_mode(self, mock_image_open, analyzer, sample_image_path):
        """Test image mode conversion."""
        mock_img = Mock()
        mock_img.mode = 'RGBA'  # Not RGB
        mock_img.size = (800, 600)
        
        mock_converted = Mock()
        mock_converted.mode = 'RGB'
        mock_converted.size = (800, 600)
        mock_img.convert.return_value = mock_converted
        
        mock_buffer = Mock()
        mock_buffer.getvalue.return_value = b'fake_image_data'
        
        with patch('poster_analyzer.claude_client.io.BytesIO') as mock_bytesio, \
             patch('poster_analyzer.claude_client.base64.b64encode') as mock_b64encode:
            
            mock_image_open.return_value.__enter__.return_value = mock_img
            mock_bytesio.return_value = mock_buffer
            mock_b64encode.return_value = b'encoded_data'
            
            result = analyzer._prepare_image(sample_image_path)
            
            # Should convert to RGB
            mock_img.convert.assert_called_once_with('RGB')
            assert result == 'encoded_data'
    
    def test_prepare_image_file_not_found(self, analyzer):
        """Test image preparation with non-existent file."""
        result = analyzer._prepare_image('nonexistent.jpg')
        assert result is None
    
    def test_create_analysis_prompt_basic(self, analyzer):
        """Test basic prompt creation."""
        prompt = analyzer._create_analysis_prompt()
        
        assert 'Analysiere dieses deutsche Veranstaltungsplakat' in prompt
        assert 'JSON-Format' in prompt
        assert 'veranstaltungsname' in prompt
        assert 'kategorie' in prompt
    
    def test_create_analysis_prompt_with_additional_info(self, analyzer):
        """Test prompt creation with QR codes and URLs."""
        qr_codes = ['https://tickets.example.de']
        urls = ['https://venue.example.de', 'https://artist.example.de']
        
        prompt = analyzer._create_analysis_prompt(qr_codes, urls)
        
        assert 'Detected QR codes: https://tickets.example.de' in prompt
        assert 'Detected URLs: https://venue.example.de, https://artist.example.de' in prompt
    
    def test_parse_response_success(self, analyzer, mock_claude_response):
        """Test successful response parsing."""
        qr_codes = ['QR: event info']
        urls = ['https://test.de']
        
        result = analyzer._parse_response(mock_claude_response, qr_codes, urls)
        
        assert result is not None
        assert isinstance(result, EventData)
        assert result.veranstaltungsname == "Rock Concert"
        assert result.kategorie == EventKategorie.MUSIK
        assert result.erkannte_qr_codes == qr_codes
        assert result.erkannte_links == urls
    
    def test_parse_response_invalid_json(self, analyzer):
        """Test parsing invalid JSON response."""
        invalid_response = "This is not JSON data"
        
        result = analyzer._parse_response(invalid_response)
        
        assert result is None
    
    def test_parse_response_missing_required_field(self, analyzer):
        """Test parsing response missing required field."""
        response_without_name = '''
        {
            "kategorie": "musik",
            "metadaten": {
                "vertrauenswuerdigkeit": 0.8
            }
        }
        '''
        
        result = analyzer._parse_response(response_without_name)
        
        assert result is None
    
    def test_parse_response_json_in_text(self, analyzer):
        """Test extracting JSON from response with extra text."""
        response_with_text = '''
        Here is the analysis result:
        
        {
            "veranstaltungsname": "Test Event",
            "kategorie": "musik",
            "metadaten": {
                "vertrauenswuerdigkeit": 0.8
            }
        }
        
        That concludes the analysis.
        '''
        
        result = analyzer._parse_response(response_with_text)
        
        assert result is not None
        assert result.veranstaltungsname == "Test Event"
    
    @patch('poster_analyzer.claude_client.ClaudeImageAnalyzer._prepare_image')
    @patch('poster_analyzer.claude_client.ClaudeImageAnalyzer._parse_response')
    def test_analyze_poster_success(self, mock_parse, mock_prepare, analyzer, sample_event_data):
        """Test successful poster analysis."""
        # Mock image preparation
        mock_prepare.return_value = 'base64_image_data'
        
        # Mock response parsing
        mock_parse.return_value = sample_event_data
        
        # Mock Claude API call
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = '{"test": "response"}'
        analyzer.client.messages.create.return_value = mock_response
        
        result = analyzer.analyze_poster('test_image.jpg')
        
        assert result == sample_event_data
        mock_prepare.assert_called_once_with('test_image.jpg')
        analyzer.client.messages.create.assert_called_once()
    
    @patch('poster_analyzer.claude_client.ClaudeImageAnalyzer._prepare_image')
    def test_analyze_poster_image_prep_failure(self, mock_prepare, analyzer):
        """Test poster analysis when image preparation fails."""
        mock_prepare.return_value = None
        
        result = analyzer.analyze_poster('test_image.jpg')
        
        assert result is None
        # Should not call Claude API if image prep fails
        analyzer.client.messages.create.assert_not_called()
    
    @patch('poster_analyzer.claude_client.ClaudeImageAnalyzer._prepare_image')
    def test_analyze_poster_api_error(self, mock_prepare, analyzer):
        """Test poster analysis when Claude API fails."""
        mock_prepare.return_value = 'base64_image_data'
        analyzer.client.messages.create.side_effect = Exception("API Error")
        
        result = analyzer.analyze_poster('test_image.jpg')
        
        assert result is None
    
    def test_validate_api_key_success(self, analyzer):
        """Test successful API key validation."""
        mock_response = Mock()
        analyzer.client.messages.create.return_value = mock_response
        
        result = analyzer.validate_api_key()
        
        assert result is True
        analyzer.client.messages.create.assert_called_once()
    
    def test_validate_api_key_failure(self, analyzer):
        """Test API key validation failure."""
        analyzer.client.messages.create.side_effect = Exception("Invalid API key")
        
        result = analyzer.validate_api_key()
        
        assert result is False
    
    def test_api_call_parameters(self, analyzer, sample_image_path):
        """Test that API call uses correct parameters."""
        with patch('poster_analyzer.claude_client.ClaudeImageAnalyzer._prepare_image') as mock_prepare, \
             patch('poster_analyzer.claude_client.ClaudeImageAnalyzer._parse_response') as mock_parse:
            
            mock_prepare.return_value = 'base64_data'
            mock_parse.return_value = None
            
            mock_response = Mock()
            mock_response.content = [Mock()]
            mock_response.content[0].text = '{}'
            analyzer.client.messages.create.return_value = mock_response
            
            analyzer.analyze_poster(sample_image_path)
            
            # Check API call parameters
            call_args = analyzer.client.messages.create.call_args
            assert call_args[1]['model'] == analyzer.model
            assert call_args[1]['temperature'] == 0.1  # Low temperature for consistency
            assert call_args[1]['max_tokens'] == 2000
            
            # Check message structure
            messages = call_args[1]['messages']
            assert len(messages) == 1
            assert messages[0]['role'] == 'user'
            assert len(messages[0]['content']) == 2  # Image + text
            
            # Check image content
            image_content = next(c for c in messages[0]['content'] if c['type'] == 'image')
            assert image_content['source']['type'] == 'base64'
            assert image_content['source']['media_type'] == 'image/jpeg'
            assert image_content['source']['data'] == 'base64_data'