"""
Web scraper for gathering additional event information from URLs and QR codes.
"""

import asyncio
import aiohttp
import logging
import re
from typing import List, Dict, Optional, Any
from urllib.parse import urljoin, urlparse
from datetime import datetime

from bs4 import BeautifulSoup, NavigableString
import validators

from .data_models import EventData, Kuenstler, TicketInfo, Kontakt


logger = logging.getLogger(__name__)


class WebScraper:
    """Scrapes additional event information from detected URLs."""
    
    def __init__(self, timeout: int = 10, max_concurrent: int = 5):
        """
        Initialize web scraper.
        
        Args:
            timeout: Request timeout in seconds
            max_concurrent: Maximum concurrent requests
        """
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.session = None
        
        # German event-related keywords
        self.event_keywords = {
            'price': ['preis', 'kosten', 'eintritt', 'ticket', 'euro', '€', 'vvk', 'abendkasse'],
            'date': ['datum', 'wann', 'termin', 'uhr', 'einlass', 'beginn', 'start'],
            'location': ['wo', 'ort', 'adresse', 'location', 'venue', 'straße', 'plz'],
            'contact': ['kontakt', 'info', 'telefon', 'tel', 'email', 'mail', '@'],
            'artists': ['künstler', 'artist', 'band', 'dj', 'performer', 'act'],
            'tickets': ['tickets', 'karten', 'vorverkauf', 'reservierung', 'buchung']
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            connector=aiohttp.TCPConnector(limit=self.max_concurrent)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def enhance_event_data(self, event_data: EventData, 
                               urls: List[str]) -> EventData:
        """
        Enhance event data with information from URLs.
        
        Args:
            event_data: Initial event data
            urls: List of URLs to scrape
            
        Returns:
            Enhanced event data
        """
        if not urls:
            return event_data
        
        # Scrape all URLs concurrently
        scraped_data = await self._scrape_urls(urls)
        
        # Merge scraped data with existing event data
        enhanced_data = self._merge_scraped_data(event_data, scraped_data)
        
        return enhanced_data
    
    async def _scrape_urls(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Scrape multiple URLs concurrently.
        
        Args:
            urls: List of URLs to scrape
            
        Returns:
            List of scraped data dictionaries
        """
        valid_urls = [url for url in urls if validators.url(url)]
        
        if not valid_urls:
            return []
        
        # Create semaphore for concurrent requests
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        # Create tasks for all URLs
        tasks = [self._scrape_single_url(semaphore, url) for url in valid_urls]
        
        # Execute all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and None results
        scraped_data = [result for result in results 
                       if not isinstance(result, Exception) and result is not None]
        
        return scraped_data
    
    async def _scrape_single_url(self, semaphore: asyncio.Semaphore, 
                                url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape a single URL.
        
        Args:
            semaphore: Semaphore for rate limiting
            url: URL to scrape
            
        Returns:
            Scraped data dictionary or None
        """
        async with semaphore:
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                async with self.session.get(url, headers=headers) as response:
                    if response.status != 200:
                        logger.warning(f"HTTP {response.status} for {url}")
                        return None
                    
                    content = await response.text()
                    
                    # Parse HTML
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Extract structured data
                    data = {
                        'url': url,
                        'title': self._extract_title(soup),
                        'text_content': self._extract_text_content(soup),
                        'structured_data': self._extract_structured_data(soup),
                        'meta_data': self._extract_meta_data(soup)
                    }
                    
                    logger.info(f"Successfully scraped: {url}")
                    return data
                    
            except Exception as e:
                logger.error(f"Error scraping {url}: {e}")
                return None
    
    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract page title."""
        title_tag = soup.find('title')
        return title_tag.get_text().strip() if title_tag else None
    
    def _extract_text_content(self, soup: BeautifulSoup) -> str:
        """Extract all readable text content."""
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text
        text = soup.get_text()
        
        # Clean up text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def _extract_structured_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract structured data from HTML."""
        structured = {}
        
        # JSON-LD structured data
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, dict):
                    structured['json_ld'] = data
                break
            except (json.JSONDecodeError, TypeError):
                continue
        
        # Microdata
        microdata_items = soup.find_all(attrs={"itemtype": True})
        if microdata_items:
            structured['microdata'] = [self._parse_microdata(item) for item in microdata_items]
        
        return structured
    
    def _extract_meta_data(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract meta tags."""
        meta_data = {}
        
        # Standard meta tags
        for meta in soup.find_all('meta'):
            name = meta.get('name') or meta.get('property')
            content = meta.get('content')
            if name and content:
                meta_data[name] = content
        
        return meta_data
    
    def _parse_microdata(self, item) -> Dict[str, Any]:
        """Parse microdata item."""
        data = {'type': item.get('itemtype', '')}
        
        props = item.find_all(attrs={"itemprop": True})
        for prop in props:
            prop_name = prop.get('itemprop')
            prop_value = prop.get('content') or prop.get_text().strip()
            data[prop_name] = prop_value
        
        return data
    
    def _merge_scraped_data(self, event_data: EventData, 
                          scraped_data: List[Dict[str, Any]]) -> EventData:
        """
        Merge scraped data into event data.
        
        Args:
            event_data: Original event data
            scraped_data: List of scraped data from URLs
            
        Returns:
            Enhanced event data
        """
        enhanced = event_data.copy(deep=True)
        
        for data in scraped_data:
            try:
                # Extract and merge information
                self._merge_event_info(enhanced, data)
                self._merge_contact_info(enhanced, data)
                self._merge_ticket_info(enhanced, data)
                self._merge_artist_info(enhanced, data)
                
                # Add source
                if data['url'] not in enhanced.metadaten.quellen:
                    enhanced.metadaten.quellen.append(data['url'])
                    
            except Exception as e:
                logger.error(f"Error merging scraped data: {e}")
        
        # Update confidence score based on additional sources
        if scraped_data:
            original_confidence = enhanced.metadaten.vertrauenswuerdigkeit
            source_bonus = min(0.2, len(scraped_data) * 0.05)
            enhanced.metadaten.vertrauenswuerdigkeit = min(1.0, original_confidence + source_bonus)
        
        return enhanced
    
    def _merge_event_info(self, event_data: EventData, scraped: Dict[str, Any]):
        """Merge general event information."""
        text = scraped.get('text_content', '').lower()
        
        # Extract prices if missing
        if not event_data.preise.preis and not event_data.preise.kostenlos:
            price_match = re.search(r'(\d+(?:,\d+)?)\s*€|euro?\s*(\d+(?:,\d+)?)', text)
            if price_match:
                price_str = price_match.group(1) or price_match.group(2)
                try:
                    price = float(price_str.replace(',', '.'))
                    event_data.preise.preis = price
                    event_data.preise.kostenlos = False
                except ValueError:
                    pass
        
        # Extract location info if missing
        if not event_data.ort.adresse:
            # Look for German address patterns
            address_match = re.search(r'([A-ZÄÖÜ][a-zäöüß\-]+(?:\s+[A-ZÄÖÜ][a-zäöüß\-]+)*)\s+(\d+[a-z]?),?\s*(\d{5})\s+([A-ZÄÖÜ][a-zäöüß\-]+)', text)
            if address_match:
                street, number, plz, city = address_match.groups()
                event_data.ort.adresse = f"{street} {number}"
                event_data.ort.postleitzahl = plz
                event_data.ort.stadt = city
    
    def _merge_contact_info(self, event_data: EventData, scraped: Dict[str, Any]):
        """Merge contact information."""
        text = scraped.get('text_content', '')
        
        # Extract email
        if not event_data.metadaten.kontakt.email:
            email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
            if email_match:
                event_data.metadaten.kontakt.email = email_match.group(0)
        
        # Extract phone numbers
        if not event_data.metadaten.kontakt.telefon:
            phone_match = re.search(r'(?:\+49|0)[\s\-]?\d{2,5}[\s\-]?\d{3,8}', text)
            if phone_match:
                event_data.metadaten.kontakt.telefon = phone_match.group(0)
        
        # Extract website
        if not event_data.metadaten.kontakt.website:
            event_data.metadaten.kontakt.website = scraped['url']
    
    def _merge_ticket_info(self, event_data: EventData, scraped: Dict[str, Any]):
        """Merge ticket information."""
        text = scraped.get('text_content', '').lower()
        
        # Look for ticket keywords and extract relevant information
        for keyword in self.event_keywords['tickets']:
            if keyword in text:
                # Add URL as ticket source if it seems relevant
                if scraped['url'] not in event_data.metadaten.ticketinfo.online_links:
                    try:
                        event_data.metadaten.ticketinfo.online_links.append(scraped['url'])
                    except:
                        pass  # Handle validation errors
                break
    
    def _merge_artist_info(self, event_data: EventData, scraped: Dict[str, Any]):
        """Merge artist information."""
        # This would be more sophisticated in practice
        # Could use NLP to extract artist names and information
        pass