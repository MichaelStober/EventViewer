# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

EventViewer is a privacy-first, AI-powered mobile and web application for local event discovery through QR code scanning. The app transforms physical event placards into a personalized digital event management system.

**Core Architecture**: Multi-platform application with mobile (React Native), web (Next.js PWA), and admin portal components, backed by Node.js API services.

## Key Technologies (Planned)

- **Mobile**: React Native 0.72+ with Redux Toolkit, react-native-camera, Google Maps
- **Web**: Next.js 13+ with Tailwind CSS, WebRTC camera API
- **Backend**: Node.js + Express + TypeScript, PostgreSQL with PostGIS, Redis cache
- **AI/ML**: TensorFlow Lite for on-device event categorization
- **Infrastructure**: Docker, Kubernetes, cloud deployment

## Project Status

**Current State**: Early development phase with specifications and HTML mockup complete. The project contains:
- Comprehensive functional and technical specifications (`specs/micha-event-view-spec.md`)
- Visual mockup demonstrating UI/UX concepts (`mockup/micha-event-view-mockup.html`)
- No production code implementation yet

## Core Features (Planned)

1. **QR Code Scanner**: Real-time event QR code detection and parsing
2. **Smart Categorization**: AI-powered event classification (Music, Theater, Food, Sports, Family, Nightlife, Workshops, Festivals)
3. **Event Management**: Calendar integration, filtering, search, and offline storage
4. **Maps Integration**: Location-based event discovery with Google Maps
5. **Privacy-First**: Local ML processing, minimal data collection
6. **Offline Mode**: SQLite local storage with background sync

## Data Schema

Events follow this structure:
```json
{
  "eventId": "uuid",
  "title": "required string",
  "category": "enum[8 categories]",
  "startDateTime": "ISO8601",
  "location": {
    "name": "string",
    "address": "required",
    "coordinates": {"lat": "number", "lng": "number"}
  },
  "pricing": {"isFree": "boolean", "amount": "number", "currency": "ISO4217"}
}
```

## Development Notes

- The project prioritizes user privacy with local-first data processing
- Performance targets: < 2s QR scan response, < 150MB RAM usage, 99.9% uptime
- Multi-language support planned (initially English, German)
- Accessibility compliance required for screen readers
- Offline-first approach with intelligent sync when connected

## Implementation Phases

1. **MVP**: Basic QR scanning, event storage, simple calendar/map views
2. **Enhanced**: AI categorization, advanced filtering, offline mode, calendar integration  
3. **Intelligence**: Personalized recommendations, smart notifications, analytics
4. **Scale**: Multi-language, accessibility features, performance optimization

When implementing features, refer to the detailed specifications in `specs/micha-event-view-spec.md` for functional requirements and the mockup for UI guidance.