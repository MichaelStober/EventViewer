"""
Main poster analyzer orchestrator that coordinates all analysis components.
"""

import asyncio
import logging
import time
from typing import Optional, List, Dict, Any
from pathlib import Path

from .qr_detector import QRCodeDetector
from .claude_client import ClaudeImageAnalyzer
from .web_scraper import WebScraper
from .data_models import EventData


logger = logging.getLogger(__name__)


class PosterAnalyzer:
    """Main orchestrator for event poster analysis."""
    
    def __init__(self, claude_api_key: str, enable_web_scraping: bool = True,
                 scraping_timeout: int = 10):
        """
        Initialize poster analyzer.
        
        Args:
            claude_api_key: Anthropic API key for Claude
            enable_web_scraping: Whether to enable web scraping
            scraping_timeout: Timeout for web scraping requests
        """
        self.qr_detector = QRCodeDetector()
        self.claude_analyzer = ClaudeImageAnalyzer(claude_api_key)
        self.enable_web_scraping = enable_web_scraping
        self.scraping_timeout = scraping_timeout
        
        # Validate API key
        if not self.claude_analyzer.validate_api_key():
            raise ValueError("Invalid Claude API key")
        
        logger.info("PosterAnalyzer initialized successfully")
    
    async def analyze_poster(self, image_path: str) -> Optional[EventData]:
        """
        Analyze a poster image and extract event information.
        
        Args:
            image_path: Path to the poster image file
            
        Returns:
            EventData object with extracted information or None if analysis fails
        """
        start_time = time.time()
        
        try:
            # Validate image path
            if not Path(image_path).exists():
                logger.error(f"Image file not found: {image_path}")
                return None
            
            logger.info(f"Starting analysis of: {image_path}")
            
            # Phase 1: QR Code and URL Detection
            logger.info("Phase 1: Detecting QR codes and URLs...")
            qr_codes, urls = self.qr_detector.detect_all(image_path)
            
            # Validate and filter URLs
            valid_urls = self.qr_detector.validate_german_urls(urls)
            
            logger.info(f"Detected {len(qr_codes)} QR codes and {len(valid_urls)} valid URLs")
            
            # Phase 2: Claude AI Analysis
            logger.info("Phase 2: Analyzing poster with Claude AI...")
            event_data = self.claude_analyzer.analyze_poster(
                image_path, qr_codes, valid_urls
            )
            
            if not event_data:
                logger.error("Claude analysis failed")
                return None
            
            logger.info(f"Claude extracted event: {event_data.veranstaltungsname}")
            
            # Phase 3: Web Scraping Enhancement (if enabled)
            if self.enable_web_scraping and valid_urls:
                logger.info("Phase 3: Enhancing data with web scraping...")
                event_data = await self._enhance_with_web_scraping(event_data, valid_urls)
            else:
                logger.info("Phase 3: Web scraping disabled or no URLs to scrape")
            
            # Phase 4: Final Quality Assessment
            logger.info("Phase 4: Final quality assessment...")
            self._assess_data_quality(event_data)
            
            analysis_time = time.time() - start_time
            logger.info(f"Analysis completed in {analysis_time:.2f} seconds")
            
            return event_data
            
        except Exception as e:
            logger.error(f"Error during poster analysis: {e}")
            return None
    
    async def analyze_multiple_posters(self, image_paths: List[str],
                                     max_concurrent: int = 3) -> List[EventData]:
        """
        Analyze multiple posters concurrently.
        
        Args:
            image_paths: List of paths to poster images
            max_concurrent: Maximum concurrent analyses
            
        Returns:
            List of EventData objects for successful analyses
        """
        logger.info(f"Starting analysis of {len(image_paths)} posters")
        
        # Create semaphore for concurrent analyses
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def analyze_with_semaphore(path: str) -> Optional[EventData]:
            async with semaphore:
                return await self.analyze_poster(path)
        
        # Execute all analyses
        tasks = [analyze_with_semaphore(path) for path in image_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful results
        event_data_list = []
        for i, result in enumerate(results):
            if isinstance(result, EventData):
                event_data_list.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Error analyzing {image_paths[i]}: {result}")
        
        logger.info(f"Successfully analyzed {len(event_data_list)} out of {len(image_paths)} posters")
        return event_data_list
    
    async def _enhance_with_web_scraping(self, event_data: EventData, 
                                       urls: List[str]) -> EventData:
        """
        Enhance event data using web scraping.
        
        Args:
            event_data: Initial event data
            urls: URLs to scrape for additional information
            
        Returns:
            Enhanced event data
        """
        try:
            async with WebScraper(timeout=self.scraping_timeout) as scraper:
                enhanced_data = await scraper.enhance_event_data(event_data, urls)
                logger.info(f"Web scraping enhanced confidence to {enhanced_data.metadaten.vertrauenswuerdigkeit:.2f}")
                return enhanced_data
        except Exception as e:
            logger.error(f"Web scraping failed: {e}")
            return event_data
    
    def _assess_data_quality(self, event_data: EventData) -> None:
        """
        Assess and log data quality metrics.
        
        Args:
            event_data: Event data to assess
        """
        quality_factors = []
        
        # Required field present
        if event_data.veranstaltungsname:
            quality_factors.append("event_name")
        
        # Location information
        if event_data.ort.veranstaltungsort or event_data.ort.adresse:
            quality_factors.append("location")
        
        # Date/time information
        if event_data.termine.beginn:
            quality_factors.append("datetime")
        
        # Pricing information
        if event_data.preise.kostenlos or event_data.preise.preis:
            quality_factors.append("pricing")
        
        # Contact information
        if (event_data.metadaten.kontakt.telefon or 
            event_data.metadaten.kontakt.email or 
            event_data.metadaten.kontakt.website):
            quality_factors.append("contact")
        
        # Additional sources
        if event_data.erkannte_qr_codes or event_data.erkannte_links:
            quality_factors.append("sources")
        
        # Category classification
        if event_data.kategorie and event_data.kategorie.value != "andere":
            quality_factors.append("category")
        
        quality_score = len(quality_factors) / 7  # 7 possible factors
        
        logger.info(f"Data quality score: {quality_score:.2f}")
        logger.info(f"Quality factors present: {', '.join(quality_factors)}")
        
        # Update confidence score based on data completeness
        if quality_score > event_data.metadaten.vertrauenswuerdigkeit:
            event_data.metadaten.vertrauenswuerdigkeit = min(1.0, 
                (event_data.metadaten.vertrauenswuerdigkeit + quality_score) / 2)
    
    def export_results(self, event_data: EventData, output_path: str,
                      format: str = 'json') -> bool:
        """
        Export analysis results to file.
        
        Args:
            event_data: Event data to export
            output_path: Output file path
            format: Export format ('json' or 'csv')
            
        Returns:
            True if export successful
        """
        try:
            import json
            from pathlib import Path
            
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            if format.lower() == 'json':
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(event_data.to_dict(), f, ensure_ascii=False, 
                             indent=2, default=str)
            
            elif format.lower() == 'csv':
                import csv
                # Flatten data for CSV export
                flattened = self._flatten_event_data(event_data)
                
                with open(output_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=flattened.keys())
                    writer.writeheader()
                    writer.writerow(flattened)
            
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            logger.info(f"Results exported to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False
    
    def _flatten_event_data(self, event_data: EventData) -> Dict[str, Any]:
        """Flatten event data for CSV export."""
        flattened = {
            'veranstaltungsname': event_data.veranstaltungsname,
            'kategorie': event_data.kategorie.value,
            'beschreibung': event_data.beschreibung,
            'veranstaltungsort': event_data.ort.veranstaltungsort,
            'adresse': event_data.ort.adresse,
            'stadt': event_data.ort.stadt,
            'postleitzahl': event_data.ort.postleitzahl,
            'bundesland': event_data.ort.bundesland,
            'beginn': event_data.termine.beginn.isoformat() if event_data.termine.beginn else None,
            'ende': event_data.termine.ende.isoformat() if event_data.termine.ende else None,
            'kostenlos': event_data.preise.kostenlos,
            'preis': event_data.preise.preis,
            'vorverkauf': event_data.preise.vorverkauf,
            'abendkasse': event_data.preise.abendkasse,
            'veranstalter': event_data.metadaten.kontakt.veranstalter,
            'telefon': event_data.metadaten.kontakt.telefon,
            'email': event_data.metadaten.kontakt.email,
            'website': str(event_data.metadaten.kontakt.website) if event_data.metadaten.kontakt.website else None,
            'vertrauenswuerdigkeit': event_data.metadaten.vertrauenswuerdigkeit,
            'erkannte_links': '; '.join(event_data.erkannte_links),
            'erkannte_qr_codes': '; '.join(event_data.erkannte_qr_codes),
            'kuenstler': '; '.join([k.name for k in event_data.metadaten.kuenstler])
        }
        
        return flattened