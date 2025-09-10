"""
Claude API client for event poster analysis.
"""

import json
import logging
import base64
from typing import Optional, Dict, Any
from pathlib import Path

import anthropic
from PIL import Image

from .data_models import EventData, EventKategorie


logger = logging.getLogger(__name__)


class ClaudeImageAnalyzer:
    """Claude AI client for analyzing event posters."""
    
    def __init__(self, api_key: str):
        """
        Initialize Claude client.
        
        Args:
            api_key: Anthropic API key
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"
        
    def analyze_poster(self, image_path: str, detected_qr_codes: list = None, 
                      detected_urls: list = None) -> Optional[EventData]:
        """
        Analyze event poster using Claude vision.
        
        Args:
            image_path: Path to poster image
            detected_qr_codes: Previously detected QR codes
            detected_urls: Previously detected URLs
            
        Returns:
            EventData object or None if analysis fails
        """
        try:
            # Prepare image
            image_data = self._prepare_image(image_path)
            if not image_data:
                return None
                
            # Create structured prompt
            prompt = self._create_analysis_prompt(detected_qr_codes, detected_urls)
            
            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.1,  # Low temperature for consistent output
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_data
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }]
            )
            
            # Parse response
            return self._parse_response(response.content[0].text, detected_qr_codes, detected_urls)
            
        except Exception as e:
            logger.error(f"Error analyzing poster with Claude: {e}")
            return None
    
    def _prepare_image(self, image_path: str) -> Optional[str]:
        """
        Prepare image for Claude API.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Base64 encoded image data or None
        """
        try:
            # Open and potentially resize image
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if too large (Claude has size limits)
                max_size = 1568  # Claude's max dimension
                if max(img.size) > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # Save to bytes
                import io
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=85)
                
                # Encode to base64
                return base64.b64encode(buffer.getvalue()).decode('utf-8')
                
        except Exception as e:
            logger.error(f"Error preparing image: {e}")
            return None
    
    def _create_analysis_prompt(self, qr_codes: list = None, urls: list = None) -> str:
        """
        Create structured prompt for event analysis.
        
        Args:
            qr_codes: Previously detected QR codes
            urls: Previously detected URLs
            
        Returns:
            Formatted prompt string
        """
        additional_info = ""
        if qr_codes:
            additional_info += f"\n\nDetected QR codes: {', '.join(qr_codes)}"
        if urls:
            additional_info += f"\n\nDetected URLs: {', '.join(urls)}"
        
        prompt = f"""
Analysiere dieses deutsche Veranstaltungsplakat und extrahiere alle Event-Informationen. 
Gib die Daten im folgenden exakten JSON-Format zurück:

{{
    "veranstaltungsname": "Name der Veranstaltung (PFLICHT)",
    "ort": {{
        "veranstaltungsort": "Name der Location",
        "adresse": "Straße und Hausnummer",
        "stadt": "Stadt",
        "postleitzahl": "5-stellige PLZ",
        "bundesland": "Deutsches Bundesland"
    }},
    "termine": {{
        "beginn": "YYYY-MM-DDTHH:MM:SS (ISO format)",
        "ende": "YYYY-MM-DDTHH:MM:SS (optional)",
        "einlass": "YYYY-MM-DDTHH:MM:SS (optional)"
    }},
    "preise": {{
        "kostenlos": false,
        "preis": 25.50,
        "waehrung": "EUR",
        "vorverkauf": 20.00,
        "abendkasse": 25.50
    }},
    "beschreibung": "Event-Beschreibung vom Plakat",
    "kategorie": "musik|comedy|essen|party|theater|sport|workshop|festival|kultur|andere",
    "metadaten": {{
        "kuenstler": [
            {{"name": "Künstlername", "info": "Zusatzinfo über Künstler"}}
        ],
        "ticketinfo": {{
            "verkaufsstellen": ["Verkaufsstelle 1", "Verkaufsstelle 2"],
            "online_links": ["https://tickets.example.com"],
            "telefon": "Telefonnummer für Tickets"
        }},
        "kontakt": {{
            "veranstalter": "Name des Veranstalters",
            "telefon": "Kontakt-Telefon",
            "email": "kontakt@example.de",
            "website": "https://example.de"
        }},
        "quellen": ["Quellenangaben"],
        "vertrauenswuerdigkeit": 0.85
    }}
}}{additional_info}

WICHTIGE REGELN:
1. Gib NUR gültiges JSON zurück, keine zusätzlichen Texte
2. Verwende null für fehlende Werte, nicht leere Strings
3. Datums-/Zeitangaben immer im ISO-Format (YYYY-MM-DDTHH:MM:SS)
4. Deutsche Telefonnummern im Format +49 oder mit Vorwahl
5. Preise als Zahlen, nicht als Strings
6. Bei unklaren Kategorien verwende "andere"
7. Vertrauenswürdigkeit zwischen 0.0 und 1.0
8. Extrahiere ALLE sichtbaren Informationen vom Plakat
"""
        
        return prompt
    
    def _parse_response(self, response_text: str, qr_codes: list = None, 
                       urls: list = None) -> Optional[EventData]:
        """
        Parse Claude's JSON response into EventData.
        
        Args:
            response_text: Raw response from Claude
            qr_codes: Detected QR codes to include
            urls: Detected URLs to include
            
        Returns:
            EventData object or None
        """
        try:
            # Clean response text - remove any non-JSON content
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                logger.error("No JSON found in Claude response")
                return None
            
            json_text = response_text[json_start:json_end]
            
            # Parse JSON
            event_dict = json.loads(json_text)
            
            # Add detected QR codes and URLs
            if qr_codes:
                event_dict['erkannte_qr_codes'] = qr_codes
            if urls:
                event_dict['erkannte_links'] = urls
                
            # Ensure required fields exist
            if 'veranstaltungsname' not in event_dict or not event_dict['veranstaltungsname']:
                logger.error("Missing required field: veranstaltungsname")
                return None
            
            # Create EventData object with validation
            event_data = EventData.from_dict(event_dict)
            
            logger.info(f"Successfully parsed event: {event_data.veranstaltungsname}")
            return event_data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            logger.debug(f"Raw response: {response_text}")
            return None
        except Exception as e:
            logger.error(f"Error parsing Claude response: {e}")
            return None
    
    def validate_api_key(self) -> bool:
        """
        Validate the API key by making a simple request.
        
        Returns:
            True if API key is valid
        """
        try:
            # Make a minimal request to test the API key
            response = self.client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Test"}]
            )
            return True
        except Exception as e:
            logger.error(f"API key validation failed: {e}")
            return False