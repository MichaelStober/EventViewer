# Event Poster Analyzer

AI-powered event poster analysis system for extracting German event information using Claude Vision API.

## Features

- 🔍 **QR Code & URL Detection**: Automatically detects QR codes and URLs from poster images
- 🤖 **Claude AI Analysis**: Uses Claude Vision to extract structured event information  
- 🌐 **Web Scraping Enhancement**: Gathers additional details from detected URLs
- 🇩🇪 **German-Focused**: Optimized for German events, addresses, and date formats
- 📊 **Structured Output**: Consistent JSON format for easy post-processing
- 🧪 **Comprehensive Testing**: Full unit test coverage with pytest
- ⚡ **Async Processing**: Fast concurrent analysis of multiple posters

## Quick Start

### 1. Installation

```bash
# Clone and navigate to the project
cd investigations/

# Install dependencies
pip install -r requirements.txt
```

### 2. Set up Claude API Key

```bash
# Set environment variable
export CLAUDE_API_KEY="your-claude-api-key-here"

# Or use the --api-key parameter
```

### 3. Analyze a Poster

```bash
# Single poster analysis
python main.py --image test_data/20250627_181616.jpg --api-key YOUR_KEY

# Batch processing
python main.py --batch test_data/ --api-key YOUR_KEY --output results/

# With additional options
python main.py --image poster.jpg --api-key YOUR_KEY --no-web-scraping --verbose
```

## Usage Examples

### Single Image Analysis
```bash
python main.py --image poster.jpg --api-key sk-ant-...
```

### Batch Processing
```bash
python main.py --batch images/ --api-key sk-ant-... --output results/ --max-concurrent 5
```

### Programmatic Usage
```python
from poster_analyzer import PosterAnalyzer
import asyncio

async def analyze_poster():
    analyzer = PosterAnalyzer('your-claude-api-key')
    
    # Analyze single poster
    result = await analyzer.analyze_poster('poster.jpg')
    
    if result:
        print(f"Event: {result.veranstaltungsname}")
        print(f"Location: {result.ort.stadt}")
        print(f"Date: {result.termine.beginn}")
        print(f"Category: {result.kategorie.value}")
        
        # Export results
        analyzer.export_results(result, 'output.json', 'json')

# Run analysis
asyncio.run(analyze_poster())
```

## Output Format

The analyzer returns structured German event data:

```json
{
  "veranstaltungsname": "Rock Concert München",
  "ort": {
    "veranstaltungsort": "Olympiahalle", 
    "adresse": "Spiridon-Louis-Ring 21",
    "stadt": "München",
    "postleitzahl": "80809",
    "bundesland": "Bayern"
  },
  "termine": {
    "beginn": "2024-12-15T20:00:00",
    "ende": "2024-12-15T23:00:00",
    "einlass": "2024-12-15T19:00:00"
  },
  "preise": {
    "kostenlos": false,
    "preis": 45.00,
    "waehrung": "EUR",
    "vorverkauf": 42.00,
    "abendkasse": 45.00
  },
  "beschreibung": "Eine unvergessliche Rocknacht mit internationalen Stars",
  "kategorie": "musik",
  "metadaten": {
    "kuenstler": [
      {"name": "Rock Band", "info": "Internationale Rockband"}
    ],
    "ticketinfo": {
      "verkaufsstellen": ["Eventim", "Münchenticket"],
      "online_links": ["https://tickets.example.de"],
      "telefon": "+49 89 1234567"
    },
    "kontakt": {
      "veranstalter": "Live Nation",
      "telefon": "+49 89 1234567", 
      "email": "info@livenation.de",
      "website": "https://livenation.de"
    },
    "quellen": ["https://venue.de", "QR: ticket-link"],
    "vertrauenswuerdigkeit": 0.85
  },
  "erkannte_links": ["https://venue.de", "https://tickets.de"],
  "erkannte_qr_codes": ["https://tickets.de/event/123"],
  "sprache": "de"
}
```

## Event Categories

The system recognizes these German event categories:

- `musik` - Concerts, live music
- `comedy` - Stand-up, kabarett  
- `essen` - Food events, markets
- `party` - Clubs, DJ events
- `theater` - Theater, plays
- `sport` - Sports events
- `workshop` - Courses, seminars
- `festival` - Festivals, folk festivals
- `kultur` - Museums, exhibitions
- `andere` - Other events

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=poster_analyzer

# Run specific test file
pytest tests/test_analyzer.py

# Verbose output
pytest -v
```

## Configuration Options

### Command Line Arguments

- `--image` - Single poster image to analyze
- `--batch` - Directory containing poster images  
- `--api-key` - Claude API key (or use CLAUDE_API_KEY env var)
- `--output` - Output directory for results
- `--max-concurrent` - Maximum concurrent analyses (default: 3)
- `--no-web-scraping` - Disable web scraping enhancement
- `--verbose` - Enable verbose logging

### Environment Variables

- `CLAUDE_API_KEY` - Your Anthropic Claude API key

## Architecture

```
poster_analyzer/
├── analyzer.py        # Main orchestrator
├── claude_client.py   # Claude API integration  
├── qr_detector.py     # QR code and URL detection
├── web_scraper.py     # Web scraping enhancement
└── data_models.py     # German event data models

tests/                 # Comprehensive unit tests
├── test_analyzer.py
├── test_claude_client.py
├── test_qr_detector.py
├── test_web_scraper.py
└── test_data_models.py
```

## Requirements

- Python 3.8+
- Claude API key from Anthropic
- See `requirements.txt` for complete dependency list

## Error Handling

The system includes robust error handling:

- Invalid image files are gracefully skipped
- Network timeouts are handled with retries
- Malformed API responses are logged and ignored
- Missing data fields use sensible defaults

## Performance

- Concurrent processing for batch analysis
- Async web scraping with rate limiting
- Image preprocessing optimization for QR detection
- Intelligent caching to avoid duplicate API calls

## German Market Features

- German address parsing (Straße, PLZ, Stadt)
- German phone number validation (+49 format)
- German date/time parsing (DD.MM.YYYY, 20:00 Uhr)
- German domain prioritization (.de, .at, .ch)
- German event vocabulary recognition

## License

Part of the EventViewer project - see main project LICENSE.

## Support

For issues and feature requests, please use the main EventViewer GitHub repository.