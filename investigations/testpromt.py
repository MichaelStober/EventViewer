import anthropic
import base64
import json
from pathlib import Path
from typing import Dict, List, Optional
import requests
from datetime import datetime

class EventExtractor:
    """
    Automatisierte Event-Extraktion aus Bildern und Webseiten mit Claude API
    """
    
    def __init__(self, api_key: str):
        """
        Initialisiert den EventExtractor mit Anthropic API Key
        
        Args:
            api_key: Ihr Anthropic API Key
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"  # oder "claude-3-opus-20240229"
        
    def encode_image(self, image_path: str) -> str:
        """
        Kodiert ein Bild in Base64 für die API
        
        Args:
            image_path: Pfad zum Bild
            
        Returns:
            Base64-kodiertes Bild
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def extract_events_from_image_and_web(self, 
                                         image_path: str, 
                                         website_url: Optional[str] = None,
                                         additional_context: str = "") -> Dict:
        """
        Extrahiert Event-Informationen aus einem Bild und optional einer Webseite
        
        Args:
            image_path: Pfad zum Event-Plakat/Bild
            website_url: Optionale URL für zusätzliche Informationen
            additional_context: Zusätzlicher Kontext für die Extraktion
            
        Returns:
            Dictionary mit extrahierten Event-Daten im JSON-Format
        """
        
        # Bild vorbereiten
        image_base64 = self.encode_image(image_path)
        
        # System-Prompt für strukturierte Ausgabe
        system_prompt = """Du bist ein Experte für die Extraktion von Event-Informationen aus Bildern und Webseiten.
        Deine Aufgabe ist es, alle relevanten Veranstaltungsinformationen zu erfassen und in einem strukturierten JSON-Format zurückzugeben.
        
        Extrahiere folgende Informationen wenn verfügbar:
        - Eventname
        - Veranstalter
        - Ort/Adresse (strukturiert)
        - Datum und Uhrzeit
        - Preise
        - Beschreibung
        - Künstler/Teilnehmer
        - Kontaktinformationen
        
        Gib die Daten IMMER im folgenden JSON-Schema zurück:
        {
            "events": [
                {
                    "eventname": "string",
                    "veranstalter": "string",
                    "kategorie": "string",
                    "ort": {
                        "name": "string",
                        "adresse": {
                            "strasse": "string",
                            "plz": "string",
                            "stadt": "string"
                        }
                    },
                    "datum": "YYYY-MM-DD",
                    "zeiten": {
                        "einlass": "HH:MM",
                        "beginn": "HH:MM"
                    },
                    "preise": {
                        "normal": float or null,
                        "ermaessigt": float or null,
                        "waehrung": "EUR"
                    },
                    "beschreibung": "string",
                    "kuenstler": []
                }
            ]
        }"""
        
        # User-Prompt erstellen
        user_message = f"""Bitte analysiere das beigefügte Bild eines Event-Plakats.
        {f'Zusätzliche Informationen findest du unter: {website_url}' if website_url else ''}
        {additional_context}
        
        Extrahiere ALLE sichtbaren Event-Informationen und gib sie im JSON-Format zurück.
        Wenn du die Webseite nicht direkt abrufen kannst, nutze die Informationen vom Bild."""
        
        # Nachricht mit Bild erstellen
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",  # oder image/png je nach Bildtyp
                            "data": image_base64
                        }
                    },
                    {
                        "type": "text",
                        "text": user_message
                    }
                ]
            }
        ]
        
        try:
            # API-Aufruf
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=0.1,  # Niedrige Temperatur für konsistente Strukturierung
                system=system_prompt,
                messages=messages
            )
            
            # Antwort verarbeiten
            response_text = response.content[0].text
            
            # JSON aus der Antwort extrahieren
            # Claude könnte den JSON in Markdown-Codeblöcken zurückgeben
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
            else:
                # Versuche direkt zu parsen
                json_str = response_text
            
            # JSON parsen
            event_data = json.loads(json_str)
            
            # Metadaten hinzufügen
            event_data['meta'] = {
                'extraction_date': datetime.now().isoformat(),
                'source_image': image_path,
                'source_url': website_url
            }
            
            return event_data
            
        except json.JSONDecodeError as e:
            print(f"Fehler beim Parsen der JSON-Antwort: {e}")
            print(f"Rohantwort: {response_text}")
            return {"error": "JSON parsing failed", "raw_response": response_text}
        except Exception as e:
            print(f"Fehler bei der API-Anfrage: {e}")
            return {"error": str(e)}
    
    def save_to_file(self, data: Dict, output_path: str = "extracted_events.json"):
        """
        Speichert die extrahierten Daten in einer JSON-Datei
        
        Args:
            data: Extrahierte Event-Daten
            output_path: Ausgabepfad für die JSON-Datei
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Daten gespeichert in: {output_path}")
    
    def process_multiple_images(self, image_paths: List[str], 
                              website_url: Optional[str] = None) -> List[Dict]:
        """
        Verarbeitet mehrere Event-Bilder
        
        Args:
            image_paths: Liste von Bildpfaden
            website_url: Optionale gemeinsame Webseite
            
        Returns:
            Liste von extrahierten Event-Daten
        """
        all_events = []
        
        for image_path in image_paths:
            print(f"Verarbeite: {image_path}")
            result = self.extract_events_from_image_and_web(image_path, website_url)
            
            if 'events' in result:
                all_events.extend(result['events'])
            else:
                print(f"Warnung: Keine Events in {image_path} gefunden")
        
        return {
            "events": all_events,
            "meta": {
                "total_events": len(all_events),
                "extraction_date": datetime.now().isoformat(),
                "sources": image_paths
            }
        }


# Beispiel-Verwendung
def main():
    """
    Beispiel für die Verwendung des EventExtractors
    """
    
    # API Key aus Umgebungsvariable oder direkt setzen
    import os
    api_key = os.getenv("ANTHROPIC_API_KEY")  # Oder direkt: "sk-ant-..."
    
    if not api_key:
        print("Bitte setzen Sie ANTHROPIC_API_KEY als Umgebungsvariable")
        return
    
    # Extractor initialisieren
    extractor = EventExtractor(api_key)
    
    # Einzelnes Bild verarbeiten
    image_path = "path/to/your/event_poster.jpg"
    website_url = "https://diekultourmacher.magic-ticketing.com/"
    
    # Events extrahieren
    print("Extrahiere Events aus Bild und Webseite...")
    events = extractor.extract_events_from_image_and_web(
        image_path=image_path,
        website_url=website_url,
        additional_context="Fokus auf Events im August 2025, besonders Comedy und Poetry Slam"
    )
    
    # Ergebnisse anzeigen
    if 'events' in events:
        print(f"\n✅ {len(events['events'])} Events gefunden:")
        for event in events['events']:
            print(f"  - {event.get('eventname', 'Unbekannt')} am {event.get('datum', 'Datum unbekannt')}")
    
    # In Datei speichern
    extractor.save_to_file(events, "sommer_am_see_2025.json")
    
    # Mehrere Bilder verarbeiten (optional)
    # multiple_images = ["poster1.jpg", "poster2.jpg", "poster3.jpg"]
    # all_events = extractor.process_multiple_images(multiple_images, website_url)
    # extractor.save_to_file(all_events, "all_events_2025.json")
    
    # Daten weiterverarbeiten
    if 'events' in events:
        # Beispiel: Nach Datum sortieren
        sorted_events = sorted(events['events'], 
                              key=lambda x: x.get('datum', '9999-12-31'))
        
        # Beispiel: Preisanalyse
        prices = [e['preise']['normal'] for e in events['events'] 
                 if e.get('preise', {}).get('normal')]
        if prices:
            avg_price = sum(prices) / len(prices)
            print(f"\n📊 Durchschnittspreis: {avg_price:.2f} EUR")


if __name__ == "__main__":
    main()


# ============= ALTERNATIVE: Verwendung mit lokaler Bildanalyse =============
# Falls Sie die Bilder lokal vorverarbeiten möchten:

class LocalEventExtractor:
    """
    Alternative Implementierung mit lokaler Vorverarbeitung
    """
    
    def __init__(self):
        # Hier könnten Sie OCR-Tools wie Tesseract einbinden
        pass
    
    def preprocess_image_with_ocr(self, image_path: str) -> str:
        """
        Extrahiert Text aus Bild mit OCR
        """
        try:
            from PIL import Image
            import pytesseract
            
            # OCR durchführen
            img = Image.open(image_path)
            text = pytesseract.image_to_string(img, lang='deu')
            return text
        except ImportError:
            print("Bitte installieren: pip install pillow pytesseract")
            return ""
    
    def extract_with_local_preprocessing(self, image_path: str) -> Dict:
        """
        Kombiniert lokale OCR mit strukturierter Extraktion
        """
        # Text aus Bild extrahieren
        ocr_text = self.preprocess_image_with_ocr(image_path)
        
        # Dann mit regulären Ausdrücken oder NLP weiterverarbeiten
        import re
        
        events = []
        # Beispiel: Datum-Muster finden
        date_pattern = r'\d{1,2}\.\d{1,2}\.\d{4}'
        dates = re.findall(date_pattern, ocr_text)
        
        # Weitere Extraktion...
        
        return {"events": events, "raw_text": ocr_text}