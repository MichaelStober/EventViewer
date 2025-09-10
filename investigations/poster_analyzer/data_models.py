"""
Data models for German event information extraction.
"""

from typing import List, Optional, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator, HttpUrl


class EventKategorie(str, Enum):
    """German event categories."""
    MUSIK = "musik"
    COMEDY = "comedy"
    ESSEN = "essen"
    PARTY = "party"
    THEATER = "theater"
    SPORT = "sport"
    WORKSHOP = "workshop"
    FESTIVAL = "festival"
    KULTUR = "kultur"
    ANDERE = "andere"


class Ort(BaseModel):
    """Event location information."""
    veranstaltungsort: Optional[str] = Field(None, description="Name of the venue")
    adresse: Optional[str] = Field(None, description="Street address")
    stadt: Optional[str] = Field(None, description="City name")
    postleitzahl: Optional[str] = Field(None, description="German postal code")
    bundesland: Optional[str] = Field(None, description="German state")

    @validator('postleitzahl')
    def validate_plz(cls, v):
        if v and not (v.isdigit() and len(v) == 5):
            raise ValueError('PLZ must be 5 digits')
        return v


class Termine(BaseModel):
    """Event timing information."""
    beginn: Optional[datetime] = Field(None, description="Event start time")
    ende: Optional[datetime] = Field(None, description="Event end time")
    einlass: Optional[datetime] = Field(None, description="Door opening time")

    @validator('ende')
    def validate_end_after_start(cls, v, values):
        if v and 'beginn' in values and values['beginn'] and v < values['beginn']:
            raise ValueError('Ende must be after Beginn')
        return v


class Preise(BaseModel):
    """Event pricing information."""
    kostenlos: bool = Field(False, description="Is the event free")
    preis: Optional[float] = Field(None, description="Regular ticket price")
    waehrung: str = Field("EUR", description="Currency code")
    vorverkauf: Optional[float] = Field(None, description="Advance sale price")
    abendkasse: Optional[float] = Field(None, description="Box office price")

    @validator('preis', 'vorverkauf', 'abendkasse')
    def validate_positive_price(cls, v):
        if v is not None and v < 0:
            raise ValueError('Price must be positive')
        return v


class Kuenstler(BaseModel):
    """Artist information."""
    name: str = Field(..., description="Artist name")
    info: Optional[str] = Field(None, description="Additional artist information")


class TicketInfo(BaseModel):
    """Ticket sales information."""
    verkaufsstellen: List[str] = Field(default_factory=list, description="Ticket outlets")
    online_links: List[HttpUrl] = Field(default_factory=list, description="Online ticket links")
    telefon: Optional[str] = Field(None, description="Phone number for tickets")


class Kontakt(BaseModel):
    """Contact information."""
    veranstalter: Optional[str] = Field(None, description="Event organizer")
    telefon: Optional[str] = Field(None, description="Contact phone")
    email: Optional[str] = Field(None, description="Contact email")
    website: Optional[HttpUrl] = Field(None, description="Website URL")


class Metadaten(BaseModel):
    """Event metadata."""
    kuenstler: List[Kuenstler] = Field(default_factory=list, description="Artists list")
    ticketinfo: TicketInfo = Field(default_factory=TicketInfo, description="Ticket information")
    kontakt: Kontakt = Field(default_factory=Kontakt, description="Contact details")
    quellen: List[str] = Field(default_factory=list, description="Information sources")
    vertrauenswuerdigkeit: float = Field(0.0, ge=0.0, le=1.0, description="Confidence score")


class EventData(BaseModel):
    """Complete German event data structure."""
    veranstaltungsname: str = Field(..., description="Event name")
    ort: Ort = Field(default_factory=Ort, description="Location information")
    termine: Termine = Field(default_factory=Termine, description="Event timing")
    preise: Preise = Field(default_factory=Preise, description="Pricing information")
    beschreibung: Optional[str] = Field(None, description="Event description")
    kategorie: EventKategorie = Field(EventKategorie.ANDERE, description="Event category")
    metadaten: Metadaten = Field(default_factory=Metadaten, description="Additional metadata")
    erkannte_links: List[str] = Field(default_factory=list, description="Detected URLs")
    erkannte_qr_codes: List[str] = Field(default_factory=list, description="Detected QR codes")
    sprache: str = Field("de", description="Language code")

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return self.dict(exclude_none=False, by_alias=True)

    @classmethod
    def from_dict(cls, data: dict) -> 'EventData':
        """Create EventData from dictionary."""
        return cls.parse_obj(data)