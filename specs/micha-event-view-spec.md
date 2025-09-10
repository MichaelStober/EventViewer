# Micha's Event-View: Functional & Technical Specification

## 1. Executive Summary

**Product Vision**: A privacy-first, AI-powered mobile and web application that revolutionizes local event discovery through machine vision QR scanning, enabling seamless transition from physical event placards to personalized digital event management.

**Target Users**: 
- Tourists and travelers seeking local experiences
- Local residents discovering nearby cultural events
- Event organizers wanting engagement analytics

**Core Value Proposition**: Scan. Discover. Experience. - Transform any street-side event placard into your personalized event calendar.

---

## 2. Functional Specifications

### 2.1 Core User Journeys

#### Journey 1: Tourist Event Discovery
```
Tourist walks through city → Sees event placard → Opens app → Scans QR code → 
Event auto-categorized & saved → Views on map/calendar → Adds to personal calendar → 
Gets navigation with travel time → Receives smart reminders
```

#### Journey 2: Local Event Planning
```
Local resident scanning multiple events → AI learns preferences → 
Receives personalized recommendations → Filters by interests/schedule → 
Shares curated list with friends → Plans weekend itinerary
```

#### Journey 3: Event Organizer Analytics
```
Organizer creates event → Generates QR placard → Tracks scan locations → 
Analyzes engagement patterns → Optimizes placard placement → 
Measures event reach and popularity
```

### 2.2 Feature Requirements

#### 2.2.1 Machine Vision QR Scanner
**Functional Requirements:**
- Real-time QR code detection using device camera
- Support for QR codes 2-10cm in various lighting conditions
- Haptic feedback and audio confirmation on successful scan
- Error handling for damaged/unreadable codes
- Batch scanning capability (multiple codes in sequence)

**Performance Requirements:**
- Scan recognition time: < 2 seconds average
- Success rate: > 95% in normal lighting
- Battery usage: < 5% per hour of active scanning
- Works offline without internet connectivity

#### 2.2.2 Smart Event Parser & Categorizer
**Functional Requirements:**
- Extract structured data from QR code JSON/XML payloads
- Auto-categorize events using local ML model
- Support 8 primary categories: Music, Theater, Food, Sports, Family, Nightlife, Workshops, Festivals
- Validate and normalize event data (dates, locations, pricing)
- Handle multiple languages in event descriptions

**Data Schema:**
```json
{
  "eventId": "uuid",
  "title": "required string",
  "description": "optional text",
  "category": "enum[8 categories]",
  "startDateTime": "ISO8601 required",
  "endDateTime": "ISO8601 optional", 
  "location": {
    "name": "string",
    "address": "required string",
    "coordinates": {"lat": "number", "lng": "number"},
    "venue": "optional string"
  },
  "pricing": {
    "isFree": "boolean",
    "amount": "optional number",
    "currency": "ISO4217",
    "ticketUrl": "optional URL"
  },
  "organizer": {
    "name": "string",
    "contact": "optional string",
    "website": "optional URL"
  },
  "metadata": {
    "ageRestriction": "optional string",
    "accessibility": "optional array",
    "languages": "optional array"
  }
}
```

#### 2.2.3 Interactive Event Calendar
**Functional Requirements:**
- Multi-view calendar: Month, Week, Day, List views
- Color-coded events by category with customizable themes
- Advanced filtering: Category, Date Range, Price, Distance, Time
- Global search across all event data
- Event conflict detection and scheduling suggestions
- Bulk operations: Select multiple events for actions

**UI/UX Requirements:**
- Swipe gestures for navigation between calendar views
- Pull-to-refresh for real-time updates
- Smooth animations with 60fps performance
- Accessible design supporting screen readers
- Responsive layout for phones, tablets, and web

#### 2.2.4 Google Maps Integration
**Functional Requirements:**
- Real-time Google Maps with custom event markers
- Distance-based filtering: 1km, 5km, 10km, Custom radius
- Cluster markers for high-density event areas
- Turn-by-turn navigation integration
- Traffic-aware route planning
- Offline map tiles for saved events

**Map Features:**
- Current location tracking with permission management
- Event density heatmaps for popular areas
- Multiple map styles: Standard, Satellite, Terrain
- Custom marker icons per event category
- Info windows with event preview and quick actions

#### 2.2.5 AI-Powered Recommendations
**Functional Requirements:**
- Machine learning recommendation engine using collaborative filtering
- Context-aware suggestions based on:
  - Time of day and day of week
  - Current weather conditions
  - Historical user preferences
  - Location patterns and travel distance
  - Calendar availability

**Privacy Requirements (optional):**
- 
- Optional anonymous analytics with explicit opt-in
- No personal data transmitted without user consent
- Recommendation explanations available to users

#### 2.2.6 Offline Mode & Data Management
**Functional Requirements:**
- SQLite local database for all scanned events
- Intelligent preloading of event details and images
- Background sync when connectivity restored
- Offline search and filtering capabilities
- Data compression and storage optimization

**Storage Architecture:**
- Events: Full details cached locally
- Images: Progressive JPEG with compression
- Maps: Offline tiles for event locations
- User preferences: Encrypted local storage
- Maximum storage: 500MB with user-configurable limits

#### 2.2.7 Calendar Integration & Sharing
**Functional Requirements:**
- One-tap integration with Google Calendar, Apple Calendar, Outlook
- iCal export for universal calendar compatibility
- Social sharing via WhatsApp, Signal, Email, SMS
- Deep linking for shared events
- Custom event collections and curation

**Sharing Options:**
- Individual event sharing with rich previews
- Curated event lists (e.g., "Weekend Arts Events")
- Location-based collections (e.g., "Events near Central Park")
- QR code generation for reverse sharing

#### 2.2.8 Smart Notifications & Reminders
**Functional Requirements:**
- Context-aware reminder notifications
- Travel time calculations with live traffic data
- Weather-based event suggestions
- Battery-optimized notification scheduling
- Rich notifications with action buttons

**Notification Types:**
- Event reminders: 30min, 1hr, 1 day configurable
- Travel alerts: "Leave now to arrive on time"
- Weather alerts: "Rain expected for outdoor event"
- Discovery alerts: "New event nearby matches your interests"

---

## 3. Technical Specifications

### 3.1 Architecture Overview

#### Systemarchitektur
```
┌─────────────────────┐    ┌─────────────────────┐
│   Mobile App (Kotlin│    │   Web App           │
│   Android/iOS)      │    │   (Webtechnologien) │
└─────────┬───────────┘    └─────────┬───────────┘
     │                          │
     └──────────────────────────┘
      │
    ┌───────────────────────────────┐
    │         Backend API           │
    │   (Python, FastAPI, Uvicorn)  │
    └─────────────┬─────────────────┘
        │
      ┌──────▼───────┐
      │ PostgreSQL   │
      │ SQLAlchemy   │
      └──────────────┘
```

### 3.2 Technology Stack


#### Frontend Technologien
**Mobile Application:**
- **Sprache/Framework**: Kotlin (Android, zukünftig auch iOS)
- **Plattformen**: Native Android, iOS (geplant)
- **Features**: Kamera-Integration, Karten, lokale Speicherung, Push-Notifications

**Web Application:**
- **Framework**: Moderne Webtechnologien (z.B. React, Vue, Angular möglich)
- **UI**: Responsive Design, Kartenintegration, QR-Scan via Kamera-API

#### Backend Technologien
- **Sprache**: Python
- **Framework**: FastAPI
- **ORM**: SQLAlchemy
- **Datenbank**: PostgreSQL
- **Server**: Uvicorn


#### Infrastruktur
- **Containerisierung**: Docker mit Multi-Stage Builds
- **Orchestrierung**: Kubernetes für produktive Deployments
- **CI/CD**: GitHub Actions mit automatisierten Tests
- **Monitoring**: DataDog oder New Relic für Performance-Monitoring
- **Error Tracking**: Sentry für Fehlerprotokollierung und Debugging

### 3.3 Machine Learning & AI
#### Server side Machine Vivsion 
```python
# Event Categorization Model Architecture
Input: Picture (title + description)
    ↓
Output: Category + Confidence Score + Event Data
```

#### On-Device ML Pipeline (Optional)
```python
# Event Categorization Model Architecture
Input: Event text (title + description)
    ↓
Text Preprocessing (tokenization, normalization)
    ↓
Feature Extraction (TF-IDF + Word Embeddings)
    ↓
Classification Model (Lightweight Neural Network)
    ↓
Output: Category + Confidence Score
```

**Model Specifications:**
- **Framework**: TensorFlow Lite for mobile deployment
- **Model Size**: < 10MB for fast loading
- **Inference Time**: < 100ms on average mobile device
- **Accuracy Target**: > 85% for primary categories
- **Languages**: Initially English, German (expandable)

#### Recommendation System
**Hybrid Approach:**
1. **Content-Based**: Event features similarity
2. **Collaborative Filtering**: User behavior patterns
3. **Context-Aware**: Time, location, weather factors

**Privacy-Preserving Techniques:**
- Federated learning for model updates
- Differential privacy for analytics
- Local data processing with optional cloud sync

### 3.4 Database Schema

#### Core Tables
```sql
-- Events table
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    qr_code_id VARCHAR(255) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    category event_category_enum NOT NULL,
    start_datetime TIMESTAMPTZ NOT NULL,
    end_datetime TIMESTAMPTZ,
    location JSONB NOT NULL, -- {name, address, coordinates}
    pricing JSONB, -- {isFree, amount, currency, ticketUrl}
    organizer JSONB, -- {name, contact, website}
    metadata JSONB, -- {ageRestriction, accessibility, languages}
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Event scans tracking
CREATE TABLE event_scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID REFERENCES events(id),
    scan_location POINT, -- PostGIS point type
    scanned_at TIMESTAMPTZ DEFAULT now(),
    user_session_id VARCHAR(255), -- Anonymous session tracking
    device_info JSONB -- {platform, version, userAgent}
);

-- User preferences (opt-in only)
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_session_id VARCHAR(255) UNIQUE,
    preferred_categories TEXT[],
    location_preferences JSONB,
    notification_settings JSONB,
    privacy_settings JSONB,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

### 3.5 API Endpoints

#### Core API Specifications
```typescript
// Event Discovery API
GET /api/v1/events
POST /api/v1/events/scan
GET /api/v1/events/:id
GET /api/v1/events/nearby

// Analytics API (Admin)
GET /api/v1/analytics/scans
GET /api/v1/analytics/heatmap
GET /api/v1/analytics/popular-events

// Recommendations API
GET /api/v1/recommendations
POST /api/v1/recommendations/feedback
```

### 3.6 Security & Privacy

#### Security Measures
- **API Security**: Rate limiting, CORS, helmet.js
- **Data Encryption**: ECC-256 for sensitive data at rest
- **Transport Security**: TLS 1.3 for all communications
- **Input Validation**: Comprehensive sanitization and validation
- **Authentication**: OAuth 2.0 with PKCE for admin users

#### Privacy Implementation
- **Data Minimization**: Collect only necessary data
- **Anonymization**: Remove PII from analytics data
- **Consent Management**: Granular privacy controls
- **Data Portability**: Export functionality for user data
- **Right to Deletion**: Complete data removal capabilities

### 3.7 Performance Requirements

#### Mobile Application
- **App Launch Time**: < 2 seconds cold start
- **QR Scan Response**: < 2 seconds average
- **Map Loading**: < 3 seconds for 100 events
- **Memory Usage**: < 150MB RAM usage
- **Battery Impact**: < 5% per hour active use

#### Web Application
- **Page Load Time**: < 3 seconds (3G connection)
- **First Contentful Paint**: < 1.5 seconds
- **Interactive Time**: < 4 seconds
- **Lighthouse Score**: > 90 for all metrics

#### Backend Services
- **API Response Time**: < 200ms for 95th percentile
- **Database Query Time**: < 100ms for complex queries
- **Concurrent Users**: Support 10,000 simultaneous users
- **Uptime**: 99.9% availability SLA

### 3.8 Scalability & Deployment

#### Infrastructure Scaling
- **Horizontal Scaling**: Auto-scaling Kubernetes pods
- **Database Scaling**: Read replicas and connection pooling
- **CDN**: Global content delivery for static assets
- **Load Balancing**: Geographic load distribution

#### Deployment Strategy
- **Environment Strategy**: Development → Staging → Production
- **Blue-Green Deployment**: Zero-downtime updates
- **Feature Flags**: Gradual feature rollout
- **Monitoring**: Real-time performance and error tracking

---
## 4.1 Core Functionalities
- Analyze Pictures and detect events on the picture. The Eventinformation is on a Poster
- The Result of the analysis should be a json dictionary which contains:
  - Eventname, EVENT_LOCATION, EVENT_TIME, price (optional), describtion (optional)
- Find the GPS coordinates of a given location 
- Categorize the Event
- Filter Locations of events based on a given center postiontion and a radius (in km).
## 4. Implementation Roadmap
### Phase 1.1: Core Functionalities
- The Projects relies hevily on AI tools. The basic functionalities should be implemented as standlone function.
- 
### Phase 1: Core MVP (Months 1-3)
- Setup a basic project for testing base functionalities.
- Basic MV functionality to analyze Posters or Pictures with information about one event
- Intermediat MV functionality which can detect multiple shown events on a poster
- advanced MV functionality which can detect links or QR codes on the Poster and search on the website behind it for information about the advertised event
- Basic QR scanning functionality
- Event storage and display
- Simple calendar view
- Basic map integration

### Phase 2: Enhanced Features (Months 4-6)
- AI categorization
- Advanced filtering
- Offline functionality
- Calendar integration

### Phase 3: Intelligence Layer (Months 7-9)
- Personalized recommendations
- Smart notifications
- Analytics dashboard
- Admin portal

### Phase 4: Scale & Polish (Months 10-12)
- Multi-language support
- Accessibility features
- Performance optimization
- Advanced analytics

---

## 5. Success Metrics

### User Engagement
- **Scan Success Rate**: > 95%
- **Daily Active Users**: Track growth trajectory
- **Session Duration**: Average 5+ minutes per session
- **Event Save Rate**: > 60% of scanned events saved

### Technical Performance
- **App Store Rating**: > 4.5 stars
- **Crash Rate**: < 0.1%
- **API Uptime**: 99.9%
- **Page Load Speed**: < 3 seconds

### Business Impact
- **Event Discovery**: Increase local event attendance
- **User Retention**: 70% monthly active user retention
- **Organizer Adoption**: 1000+ events in system
- **Geographic Coverage**: 10+ cities in first year