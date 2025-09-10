"""
Pytest configuration and fixtures for poster analyzer tests.
"""

import pytest
import asyncio
import os
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any

from poster_analyzer.data_models import EventData, EventKategorie


@pytest.fixture
def sample_event_data() -> EventData:
    """Sample event data for testing."""
    return EventData(
        veranstaltungsname="Test Concert",
        ort={
            "veranstaltungsort": "Test Hall",
            "adresse": "Teststraße 123",
            "stadt": "Berlin",
            "postleitzahl": "10115"
        },
        termine={
            "beginn": "2024-12-01T20:00:00"
        },
        preise={
            "kostenlos": False,
            "preis": 25.50,
            "waehrung": "EUR"
        },
        kategorie=EventKategorie.MUSIK,
        metadaten={
            "vertrauenswuerdigkeit": 0.8
        }
    )


@pytest.fixture
def sample_image_path(tmp_path) -> str:
    """Create a sample image file for testing."""
    from PIL import Image
    
    # Create a simple test image
    img = Image.new('RGB', (800, 600), color='white')
    image_path = tmp_path / "test_poster.jpg"
    img.save(image_path)
    
    return str(image_path)


@pytest.fixture
def mock_claude_response() -> str:
    """Mock Claude API response."""
    return '''
    {
        "veranstaltungsname": "Rock Concert",
        "ort": {
            "veranstaltungsort": "Olympiahalle",
            "adresse": "Spiridon-Louis-Ring 21",
            "stadt": "München",
            "postleitzahl": "80809"
        },
        "termine": {
            "beginn": "2024-12-15T20:00:00",
            "einlass": "2024-12-15T19:00:00"
        },
        "preise": {
            "kostenlos": false,
            "preis": 45.00,
            "waehrung": "EUR",
            "vorverkauf": 42.00
        },
        "beschreibung": "Eine unvergessliche Rocknacht",
        "kategorie": "musik",
        "metadaten": {
            "kuenstler": [
                {"name": "Test Band", "info": "Deutsche Rockband"}
            ],
            "kontakt": {
                "veranstalter": "Test Events GmbH",
                "telefon": "+49 89 1234567",
                "email": "info@testevents.de"
            },
            "vertrauenswuerdigkeit": 0.85
        }
    }
    '''


@pytest.fixture
def mock_web_content() -> str:
    """Mock web page content."""
    return '''
    <html>
    <head>
        <title>Rock Concert - Olympiahalle München</title>
        <meta name="description" content="Rock Concert am 15.12.2024 in der Olympiahalle München">
    </head>
    <body>
        <h1>Rock Concert</h1>
        <p>Datum: 15. Dezember 2024, 20:00 Uhr</p>
        <p>Ort: Olympiahalle München, Spiridon-Louis-Ring 21, 80809 München</p>
        <p>Tickets: 42,00 € (VVK) / 45,00 € (AK)</p>
        <p>Kontakt: info@testevents.de, Tel: +49 89 1234567</p>
        <div itemscope itemtype="http://schema.org/Event">
            <span itemprop="name">Rock Concert</span>
            <span itemprop="startDate" content="2024-12-15T20:00:00">15. Dezember 2024</span>
            <span itemprop="location">Olympiahalle München</span>
        </div>
    </body>
    </html>
    '''


@pytest.fixture
def mock_qr_codes() -> list:
    """Mock QR code data."""
    return [
        "https://tickets.testevents.de/rock-concert-2024",
        "Contact: info@testevents.de"
    ]


@pytest.fixture
def mock_detected_urls() -> list:
    """Mock detected URLs."""
    return [
        "https://www.testevents.de/rock-concert",
        "https://tickets.testevents.de/rock-concert-2024"
    ]


@pytest.fixture
def api_key() -> str:
    """Get API key from environment or return mock key for testing."""
    return os.getenv('CLAUDE_API_KEY', 'mock-api-key-for-testing')


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.content = [Mock()]
    mock_response.content[0].text = '''
    {
        "veranstaltungsname": "Test Event",
        "kategorie": "musik",
        "metadaten": {
            "vertrauenswuerdigkeit": 0.8
        }
    }
    '''
    mock_client.messages.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp session for web scraping tests."""
    mock_session = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value="<html><body>Test content</body></html>")
    
    mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
    
    return mock_session


@pytest.fixture
def test_data_dir() -> Path:
    """Path to test data directory."""
    return Path(__file__).parent / "fixtures"


class MockImage:
    """Mock PIL Image for testing."""
    def __init__(self, size=(800, 600), mode='RGB'):
        self.size = size
        self.mode = mode
    
    def convert(self, mode):
        return MockImage(self.size, mode)
    
    def thumbnail(self, size, resample=None):
        self.size = size
    
    def save(self, fp, format=None, **params):
        pass