"""
Poster Analyzer - AI-powered event poster analysis system for German events.

This package provides tools for:
- QR code and link detection from event posters
- Claude AI-based event information extraction  
- Web scraping for additional event details
- German-focused event data structuring
"""

__version__ = "0.1.0"
__author__ = "EventViewer Team"

from .analyzer import PosterAnalyzer
from .data_models import EventData

__all__ = ["PosterAnalyzer", "EventData"]