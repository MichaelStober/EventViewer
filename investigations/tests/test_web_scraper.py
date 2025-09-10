"""
Tests for web scraping functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from bs4 import BeautifulSoup

from poster_analyzer.web_scraper import WebScraper
from poster_analyzer.data_models import EventData, EventKategorie


class TestWebScraper:
    """Test web scraping functionality."""
    
    @pytest.fixture
    async def scraper(self):
        """Web scraper instance."""
        scraper = WebScraper(timeout=5, max_concurrent=2)
        async with scraper:
            yield scraper
    
    def test_initialization(self):
        """Test scraper initialization."""
        scraper = WebScraper(timeout=10, max_concurrent=5)
        
        assert scraper.timeout == 10
        assert scraper.max_concurrent == 5
        assert len(scraper.event_keywords) > 0
        assert 'price' in scraper.event_keywords
        assert 'date' in scraper.event_keywords
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        scraper = WebScraper()
        
        async with scraper:
            assert scraper.session is not None
        
        # Session should be closed after exiting context
        assert scraper.session is None or scraper.session.closed
    
    @pytest.mark.asyncio
    @patch('poster_analyzer.web_scraper.aiohttp.ClientSession')
    async def test_scrape_single_url_success(self, mock_session_class):
        """Test successful single URL scraping."""
        # Mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="""
        <html>
        <head><title>Test Event</title></head>
        <body><p>Event details here</p></body>
        </html>
        """)
        
        # Mock session
        mock_session = AsyncMock()
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session
        
        scraper = WebScraper()
        scraper.session = mock_session
        
        semaphore = asyncio.Semaphore(1)
        result = await scraper._scrape_single_url(semaphore, 'https://test.de')
        
        assert result is not None
        assert result['url'] == 'https://test.de'
        assert result['title'] == 'Test Event'
        assert 'Event details here' in result['text_content']
    
    @pytest.mark.asyncio
    @patch('poster_analyzer.web_scraper.aiohttp.ClientSession')
    async def test_scrape_single_url_http_error(self, mock_session_class):
        """Test URL scraping with HTTP error."""
        mock_response = AsyncMock()
        mock_response.status = 404
        
        mock_session = AsyncMock()
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session
        
        scraper = WebScraper()
        scraper.session = mock_session
        
        semaphore = asyncio.Semaphore(1)
        result = await scraper._scrape_single_url(semaphore, 'https://test.de')
        
        assert result is None
    
    @pytest.mark.asyncio
    @patch('poster_analyzer.web_scraper.aiohttp.ClientSession')
    async def test_scrape_single_url_exception(self, mock_session_class):
        """Test URL scraping with exception."""
        mock_session = AsyncMock()
        mock_session.get.side_effect = Exception("Network error")
        mock_session_class.return_value = mock_session
        
        scraper = WebScraper()
        scraper.session = mock_session
        
        semaphore = asyncio.Semaphore(1)
        result = await scraper._scrape_single_url(semaphore, 'https://test.de')
        
        assert result is None
    
    def test_extract_title(self):
        """Test title extraction from HTML."""
        scraper = WebScraper()
        html = "<html><head><title>Rock Concert München</title></head></html>"
        soup = BeautifulSoup(html, 'html.parser')
        
        title = scraper._extract_title(soup)
        
        assert title == "Rock Concert München"
    
    def test_extract_title_no_title(self):
        """Test title extraction when no title tag exists."""
        scraper = WebScraper()
        html = "<html><head></head></html>"
        soup = BeautifulSoup(html, 'html.parser')
        
        title = scraper._extract_title(soup)
        
        assert title is None
    
    def test_extract_text_content(self):
        """Test text content extraction."""
        scraper = WebScraper()
        html = """
        <html>
        <head><title>Event</title></head>
        <body>
            <script>console.log('remove me');</script>
            <style>.hidden { display: none; }</style>
            <h1>Rock Concert</h1>
            <p>Date: 15. Dezember 2024</p>
            <p>Location: München</p>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        text = scraper._extract_text_content(soup)
        
        assert 'Rock Concert' in text
        assert '15. Dezember 2024' in text
        assert 'München' in text
        assert 'console.log' not in text  # Scripts should be removed
        assert 'display: none' not in text  # Styles should be removed
    
    def test_extract_structured_data_json_ld(self):
        """Test JSON-LD structured data extraction."""
        scraper = WebScraper()
        html = '''
        <html>
        <body>
            <script type="application/ld+json">
            {
                "@context": "http://schema.org",
                "@type": "Event",
                "name": "Rock Concert",
                "startDate": "2024-12-15T20:00:00"
            }
            </script>
        </body>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        structured = scraper._extract_structured_data(soup)
        
        assert 'json_ld' in structured
        assert structured['json_ld']['name'] == 'Rock Concert'
        assert structured['json_ld']['startDate'] == '2024-12-15T20:00:00'
    
    def test_extract_structured_data_microdata(self):
        """Test microdata extraction."""
        scraper = WebScraper()
        html = '''
        <html>
        <body>
            <div itemscope itemtype="http://schema.org/Event">
                <span itemprop="name">Concert</span>
                <span itemprop="startDate" content="2024-12-15">15. Dezember</span>
            </div>
        </body>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        structured = scraper._extract_structured_data(soup)
        
        assert 'microdata' in structured
        assert len(structured['microdata']) == 1
        microdata = structured['microdata'][0]
        assert microdata['type'] == 'http://schema.org/Event'
        assert microdata['name'] == 'Concert'
    
    def test_extract_meta_data(self):
        """Test meta tag extraction."""
        scraper = WebScraper()
        html = '''
        <html>
        <head>
            <meta name="description" content="Rock concert in München">
            <meta property="og:title" content="Rock Concert">
            <meta name="keywords" content="musik, rock, konzert">
        </head>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        meta = scraper._extract_meta_data(soup)
        
        assert meta['description'] == 'Rock concert in München'
        assert meta['og:title'] == 'Rock Concert'
        assert meta['keywords'] == 'musik, rock, konzert'
    
    @pytest.mark.asyncio
    async def test_enhance_event_data_no_urls(self, sample_event_data):
        """Test enhancement with no URLs."""
        scraper = WebScraper()
        
        result = await scraper.enhance_event_data(sample_event_data, [])
        
        assert result == sample_event_data
    
    @pytest.mark.asyncio
    @patch('poster_analyzer.web_scraper.WebScraper._scrape_urls')
    async def test_enhance_event_data_with_urls(self, mock_scrape, sample_event_data):
        """Test event data enhancement with URLs."""
        # Mock scraped data
        mock_scraped_data = [{
            'url': 'https://test.de',
            'text_content': 'Preis: 30€ Tel: +49 30 123456 Email: info@test.de',
            'title': 'Event Details',
            'structured_data': {},
            'meta_data': {}
        }]
        mock_scrape.return_value = mock_scraped_data
        
        scraper = WebScraper()
        urls = ['https://test.de']
        
        result = await scraper.enhance_event_data(sample_event_data, urls)
        
        # Should have enhanced confidence score
        assert result.metadaten.vertrauenswuerdigkeit > sample_event_data.metadaten.vertrauenswuerdigkeit
        # Should have added source
        assert 'https://test.de' in result.metadaten.quellen
    
    def test_merge_event_info_price(self, sample_event_data):
        """Test merging price information."""
        scraper = WebScraper()
        
        # Remove existing price to test extraction
        sample_event_data.preise.preis = None
        sample_event_data.preise.kostenlos = False
        
        scraped_data = {
            'text_content': 'Der Eintritt kostet 35,50€ an der Abendkasse.',
            'url': 'https://test.de'
        }
        
        scraper._merge_event_info(sample_event_data, scraped_data)
        
        assert sample_event_data.preise.preis == 35.50
        assert sample_event_data.preise.kostenlos is False
    
    def test_merge_event_info_address(self, sample_event_data):
        """Test merging address information."""
        scraper = WebScraper()
        
        # Remove existing address to test extraction
        sample_event_data.ort.adresse = None
        sample_event_data.ort.postleitzahl = None
        sample_event_data.ort.stadt = None
        
        scraped_data = {
            'text_content': 'Veranstaltungsort: Musterstraße 42, 80331 München',
            'url': 'https://test.de'
        }
        
        scraper._merge_event_info(sample_event_data, scraped_data)
        
        assert sample_event_data.ort.adresse == "Musterstraße 42"
        assert sample_event_data.ort.postleitzahl == "80331"
        assert sample_event_data.ort.stadt == "München"
    
    def test_merge_contact_info_email(self, sample_event_data):
        """Test merging email contact information."""
        scraper = WebScraper()
        
        scraped_data = {
            'text_content': 'Für Fragen kontaktieren Sie uns unter info@venue.de',
            'url': 'https://test.de'
        }
        
        scraper._merge_contact_info(sample_event_data, scraped_data)
        
        assert sample_event_data.metadaten.kontakt.email == 'info@venue.de'
    
    def test_merge_contact_info_phone(self, sample_event_data):
        """Test merging phone contact information."""
        scraper = WebScraper()
        
        scraped_data = {
            'text_content': 'Reservierungen unter +49 89 1234567',
            'url': 'https://test.de'
        }
        
        scraper._merge_contact_info(sample_event_data, scraped_data)
        
        assert sample_event_data.metadaten.kontakt.telefon == '+49 89 1234567'
    
    def test_merge_ticket_info(self, sample_event_data):
        """Test merging ticket information."""
        scraper = WebScraper()
        
        scraped_data = {
            'text_content': 'tickets online verfügbar karten im vorverkauf',
            'url': 'https://tickets.test.de'
        }
        
        scraper._merge_ticket_info(sample_event_data, scraped_data)
        
        assert 'https://tickets.test.de' in sample_event_data.metadaten.ticketinfo.online_links
    
    @pytest.mark.asyncio
    async def test_scrape_urls_invalid_urls(self):
        """Test scraping with invalid URLs."""
        scraper = WebScraper()
        invalid_urls = ['not-a-url', 'ftp://invalid.protocol']
        
        with patch.object(scraper, 'session'):
            result = await scraper._scrape_urls(invalid_urls)
        
        assert result == []
    
    @pytest.mark.asyncio
    @patch('poster_analyzer.web_scraper.validators.url')
    async def test_scrape_urls_with_valid_urls(self, mock_validator):
        """Test scraping with valid URLs."""
        scraper = WebScraper()
        mock_validator.return_value = True
        
        urls = ['https://test1.de', 'https://test2.de']
        
        with patch.object(scraper, '_scrape_single_url') as mock_scrape_single:
            mock_scrape_single.return_value = {'url': 'https://test1.de', 'content': 'test'}
            
            # Mock session
            scraper.session = AsyncMock()
            
            result = await scraper._scrape_urls(urls)
            
            assert len(result) == 2  # Should call for each URL