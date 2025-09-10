"""
Tests for data models and validation.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from poster_analyzer.data_models import (
    EventData, EventKategorie, Ort, Termine, Preise, Kuenstler, 
    TicketInfo, Kontakt, Metadaten
)


class TestEventData:
    """Test EventData model."""
    
    def test_create_minimal_event(self):
        """Test creating event with minimal required data."""
        event = EventData(veranstaltungsname="Test Event")
        
        assert event.veranstaltungsname == "Test Event"
        assert event.kategorie == EventKategorie.ANDERE
        assert event.sprache == "de"
        assert event.metadaten.vertrauenswuerdigkeit == 0.0
    
    def test_create_complete_event(self, sample_event_data):
        """Test creating complete event data."""
        assert sample_event_data.veranstaltungsname == "Test Concert"
        assert sample_event_data.kategorie == EventKategorie.MUSIK
        assert sample_event_data.ort.stadt == "Berlin"
        assert sample_event_data.preise.preis == 25.50
    
    def test_missing_required_field(self):
        """Test validation fails for missing required field."""
        with pytest.raises(ValidationError):
            EventData()  # Missing veranstaltungsname
    
    def test_to_dict_conversion(self, sample_event_data):
        """Test converting to dictionary."""
        data_dict = sample_event_data.to_dict()
        
        assert isinstance(data_dict, dict)
        assert data_dict['veranstaltungsname'] == "Test Concert"
        assert data_dict['kategorie'] == "musik"
    
    def test_from_dict_creation(self):
        """Test creating from dictionary."""
        data_dict = {
            "veranstaltungsname": "Dict Event",
            "kategorie": "comedy",
            "metadaten": {"vertrauenswuerdigkeit": 0.7}
        }
        
        event = EventData.from_dict(data_dict)
        assert event.veranstaltungsname == "Dict Event"
        assert event.kategorie == EventKategorie.COMEDY


class TestOrt:
    """Test location model."""
    
    def test_valid_plz(self):
        """Test valid German postal code."""
        ort = Ort(postleitzahl="12345")
        assert ort.postleitzahl == "12345"
    
    def test_invalid_plz(self):
        """Test invalid postal code validation."""
        with pytest.raises(ValidationError):
            Ort(postleitzahl="1234")  # Too short
        
        with pytest.raises(ValidationError):
            Ort(postleitzahl="12345a")  # Contains letter


class TestTermine:
    """Test timing model."""
    
    def test_valid_times(self):
        """Test valid event times."""
        start = datetime(2024, 12, 1, 20, 0)
        end = datetime(2024, 12, 1, 23, 0)
        
        termine = Termine(beginn=start, ende=end)
        assert termine.beginn == start
        assert termine.ende == end
    
    def test_end_before_start(self):
        """Test validation fails when end is before start."""
        start = datetime(2024, 12, 1, 20, 0)
        end = datetime(2024, 12, 1, 18, 0)  # Before start
        
        with pytest.raises(ValidationError):
            Termine(beginn=start, ende=end)


class TestPreise:
    """Test pricing model."""
    
    def test_positive_prices(self):
        """Test positive price validation."""
        preise = Preise(preis=25.50, vorverkauf=22.00)
        assert preise.preis == 25.50
        assert preise.vorverkauf == 22.00
    
    def test_negative_price(self):
        """Test negative price validation fails."""
        with pytest.raises(ValidationError):
            Preise(preis=-10.0)
    
    def test_free_event(self):
        """Test free event handling."""
        preise = Preise(kostenlos=True)
        assert preise.kostenlos is True
        assert preise.waehrung == "EUR"


class TestEventKategorie:
    """Test event category enum."""
    
    def test_all_categories(self):
        """Test all available categories."""
        expected_categories = [
            "musik", "comedy", "essen", "party", "theater", 
            "sport", "workshop", "festival", "kultur", "andere"
        ]
        
        actual_categories = [cat.value for cat in EventKategorie]
        
        for expected in expected_categories:
            assert expected in actual_categories
    
    def test_category_assignment(self):
        """Test category assignment in event."""
        event = EventData(
            veranstaltungsname="Comedy Show",
            kategorie=EventKategorie.COMEDY
        )
        
        assert event.kategorie == EventKategorie.COMEDY
        assert event.kategorie.value == "comedy"


class TestKuenstler:
    """Test artist model."""
    
    def test_create_artist(self):
        """Test creating artist."""
        artist = Kuenstler(name="Test Band", info="Deutsche Rockband")
        
        assert artist.name == "Test Band"
        assert artist.info == "Deutsche Rockband"
    
    def test_artist_required_name(self):
        """Test artist requires name."""
        with pytest.raises(ValidationError):
            Kuenstler(info="Info without name")


class TestTicketInfo:
    """Test ticket information model."""
    
    def test_empty_ticket_info(self):
        """Test empty ticket info creation."""
        ticket_info = TicketInfo()
        
        assert ticket_info.verkaufsstellen == []
        assert ticket_info.online_links == []
        assert ticket_info.telefon is None
    
    def test_ticket_info_with_data(self):
        """Test ticket info with data."""
        ticket_info = TicketInfo(
            verkaufsstellen=["Eventim", "Ticketmaster"],
            online_links=["https://tickets.example.de"],
            telefon="+49 30 1234567"
        )
        
        assert len(ticket_info.verkaufsstellen) == 2
        assert len(ticket_info.online_links) == 1


class TestKontakt:
    """Test contact model."""
    
    def test_empty_contact(self):
        """Test empty contact creation."""
        kontakt = Kontakt()
        
        assert kontakt.veranstalter is None
        assert kontakt.telefon is None
        assert kontakt.email is None
        assert kontakt.website is None
    
    def test_contact_with_data(self):
        """Test contact with full data."""
        kontakt = Kontakt(
            veranstalter="Test Events GmbH",
            telefon="+49 30 1234567",
            email="info@test.de",
            website="https://test.de"
        )
        
        assert kontakt.veranstalter == "Test Events GmbH"
        assert kontakt.email == "info@test.de"


class TestMetadaten:
    """Test metadata model."""
    
    def test_empty_metadata(self):
        """Test empty metadata creation."""
        meta = Metadaten()
        
        assert meta.kuenstler == []
        assert meta.quellen == []
        assert meta.vertrauenswuerdigkeit == 0.0
    
    def test_confidence_score_bounds(self):
        """Test confidence score is bounded between 0 and 1."""
        # Valid scores
        meta1 = Metadaten(vertrauenswuerdigkeit=0.5)
        assert meta1.vertrauenswuerdigkeit == 0.5
        
        meta2 = Metadaten(vertrauenswuerdigkeit=1.0)
        assert meta2.vertrauenswuerdigkeit == 1.0
        
        meta3 = Metadaten(vertrauenswuerdigkeit=0.0)
        assert meta3.vertrauenswuerdigkeit == 0.0
        
        # Invalid scores
        with pytest.raises(ValidationError):
            Metadaten(vertrauenswuerdigkeit=1.5)
        
        with pytest.raises(ValidationError):
            Metadaten(vertrauenswuerdigkeit=-0.1)