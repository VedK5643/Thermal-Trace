# ThermalEye — Project Context

## 1. Project Overview
ThermalTrace is a specialized geospatial thermal intelligence platform engineered to monitor, visualize, and classify thermal anomalies (industrial fires, gas flares, agricultural burns, wildfires, and unknown heat sources) across critical regional assets and industrial corridors.

The platform combines high-resolution geographic basemaps with thermal anomaly observations, facility proximity metrics, historical tracking, and interactive operational dashboards.

**Current Status**: 
- **Frontend**: Frozen and integrated with real FastAPI backend via `axios` and `TanStack Query`.
- **Backend**: **IMPLEMENTED & AUDITED (Phase 4 / 4B)**. FastAPI running on port 8000, connected to Supabase PostgreSQL + PostGIS (port 6543 / 5432).
- **Thermal Data**: DEMO/MOCK data seeded into Supabase PostGIS database for initial demonstration.

---

## 2. Current Project Status
- **Phases Completed**: 
  - Phase 0 (Setup)
  - Phase 1 (UI Shell)
  - Phase 1B (Audit)
  - Phase 2 (MapLibre + Thunderforest)
  - Phase 3 (Intelligence Layer & Filtering)
  - Phase 3B (Visual Alignment)
  - Phase 3C (Full Frontend Audit & Optimization)
  - Phase 3D (Context Documentation)
  - **Phase 4 (Backend Foundation + Supabase/PostGIS Integration)**
  - **Phase 4B (Backend Foundation Audit & Frontend Integration Audit)**
- **Frontend Status**: **FROZEN & INTEGRATED**. Visual layout, map layers, user interactions, routing, client state management, and type definitions are locked and connected to FastAPI endpoints.
- **Backend Status**: **COMPLETED & OPERATIONAL**. FastAPI server with clean Router-Schema-Service-Repository architecture, PostGIS geospatial queries, Pydantic camelCase serialization, and Supabase integration.
- **Next Phase**: **Phase 5 (Satellite / NASA FIRMS Ingestion)**.

---

## 3. Product Goal
The ultimate goal of ThermalEye is to provide near-real-time satellite-driven thermal monitoring and predictive intelligence for industrial assets, environmental safety teams, and emergency responders.

The system will ingest thermal observation telemetry (e.g., NASA FIRMS MODIS/VIIRS), process and classify heat sources via machine learning (XGBoost/SHAP), compute severity/confidence scores, evaluate proximity to industrial facilities (refineries, power plants, LNG terminals), and dispatch actionable alerts through a mission-control web interface.

---

## 4. Core Concept
ThermalEye operates on three distinct conceptual layers:

1. **GEOGRAPHIC BASEMAP (Thunderforest)**: Provides cartographic context (cities, roads, coastlines, terrain, transportation networks). Thunderforest provides background geographic rendering; it does *not* detect fires or provide thermal data.
2. **THERMAL OBSERVATIONS (Supabase PostGIS / Future Satellite FIRMS Pipeline)**: Stores and ingests raw thermal coordinates `POINT(longitude latitude)`, brightness measurements (Kelvin), detection confidence, and acquisition timestamps.
3. **THERMALWATCH INTELLIGENCE LAYER**: Merges cartographic basemaps with thermal telemetry, classifies heat signatures, computes risk metrics, correlates anomalies with nearby industrial facilities, and renders a multi-layer interactive intelligence map.

```
+-------------------------------------------------------------+
|                 Satellite / FIRMS Telemetry                 |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|              ML Classification & Risk Engine                |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|           ThermalEye Geospatial Intelligence Layer        |
|             (Heatmap / Point Markers / Facilities)          |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|            MapLibre GL Interactive Renderer                 |
|       (Floating Overlays: Legend, Controls, Panels)         |
+-------------------------------------------------------------+
                              ^
                              |
+-------------------------------------------------------------+
|               Thunderforest Geographic Basemap              |
+-------------------------------------------------------------+
```

---

## 5. Technology Stack

### Frontend
| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Core Framework | React | `18.3.1` | Component UI structure |
| Build Tool | Vite | `5.4.11` | Dev server & production bundler |
| Type System | TypeScript | `5.7.2` | Compile-time strict type checking |
| Styling | Tailwind CSS | `3.4.16` | Utility-first CSS styling |
| Map Renderer | MapLibre GL | `4.7.1` | WebGL map rendering engine |
| React Map Wrapper | react-map-gl/maplibre | `7.1.9` | Declarative React components for MapLibre |
| Basemap Tiles | Thunderforest API | Raster | Cartographic map tiles (Cycle Map, Atlas, etc.) |
| Server/Query State | TanStack React Query | `5.62.0` | Data fetching, caching, and query state |
| Client State | Zustand | `^5.0.15` | Global UI client state management |
| Router | React Router DOM | `6.28.0` | Single Page Application routing |
| Icons | Lucide React | `0.469.0` | UI icon library |
| HTTP Client | Axios | `^1.7.9` | Asynchronous API requests to FastAPI backend |

### Backend (Phase 4/4B)
| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Web Framework | FastAPI | `0.115.6` | Asynchronous REST API framework |
| Server | Uvicorn | `0.34.0` | ASGI web server |
| ORM | SQLAlchemy (asyncio) | `2.0.36` | Asynchronous database ORM |
| Database Driver | asyncpg | `0.30.0` | High-performance PostgreSQL async driver |
| GIS Extension | GeoAlchemy2 | `0.15.2` | Spatial PostGIS types & functions for SQLAlchemy |
| Data Validation | Pydantic | `2.13.4` | Data schemas & camelCase serialization |
| Configuration | Pydantic Settings | `2.7.0` | Environment settings management |
| Database Cloud | Supabase PostgreSQL | PostGIS 3.x | Cloud database & spatial storage |
| Migration Tool | Alembic | `1.14.1` | Database migration framework |
| Test Suite | pytest | `8.3.4` | Asynchronous API unit & integration testing |

---

## 6. Architecture & Data Flow

```
+-------------------------------------------------------------+
|                      React Frontend                         |
|                 (TanStack Query / Axios)                    |
+-------------------------------------------------------------+
                              ^
                              | REST API / JSON (camelCase serialized)
                              v
+-------------------------------------------------------------+
|                       FastAPI Server                        |
|           (/api/v1 - Routers / Services / Repos)            |
+-------------------------------------------------------------+
                              ^
                              | SQLAlchemy Async Session
                              v
+-------------------------------------------------------------+
|               Supabase PostgreSQL + PostGIS                 |
|            (Hotspots, Facilities, Alerts Tables)            |
+-------------------------------------------------------------+
```

### Clean Control Flow Scoping:
```
Route (FastAPI Endpoint)
 ↓
Pydantic Schema (Validation & Serialization)
 ↓
Service (Business Logic & Derived Incidents Join)
 ↓
Repository (Database Queries & PostGIS ST_DWithin)
 ↓
Database (Supabase PostgreSQL / PostGIS)
```

---

## 7. Database & PostGIS Schema

### Entities:
1. **`hotspots`**:
   - `id`: `String` (PK)
   - `latitude`: `Float`
   - `longitude`: `Float`
   - `type`: `String` (`industrial_fire`, `gas_flare`, `agricultural`, `wildfire`, `unknown`)
   - `brightness`: `Float` (Kelvin)
   - `confidence`: `Float` (0–100%)
   - `severity`: `String` (`low`, `medium`, `high`, `critical`)
   - `timestamp`: `DateTime(tz=True)`
   - `facility_id`: `String` (FK -> `facilities.id`, nullable)
   - `status`: `String` (`active`, `resolved`, `monitoring`)
   - `city`, `district`, `state`, `country` (India-wide structural support)
   - `geometry`: `Geometry("POINT", srid=4326)` — Spatial order: `POINT(longitude latitude)`
   - **Indexes**: `type`, `severity`, `state`, `timestamp`, `facility_id`, GIST on `geometry`.

2. **`facilities`**:
   - `id`: `String` (PK)
   - `name`: `String`
   - `type`: `String` (`refinery`, `power_plant`, `steel_plant`, `cement_plant`, `lng_terminal`)
   - `latitude`: `Float`
   - `longitude`: `Float`
   - `city`, `district`, `state`, `country`
   - `geometry`: `Geometry("POINT", srid=4326)` — Spatial order: `POINT(longitude latitude)`
   - **Indexes**: `type`, `state`, `city`, GIST on `geometry`.

3. **`alerts`**:
   - `id`: `String` (PK)
   - `hotspot_id`: `String` (FK -> `hotspots.id`, nullable)
   - `facility_id`: `String` (FK -> `facilities.id`, nullable)
   - `severity`: `String` (`info`, `warning`, `critical`)
   - `title`: `String`
   - `message`: `String`
   - `timestamp`: `DateTime(tz=True)`
   - `acknowledged`: `Boolean`
   - **Indexes**: `severity`, `timestamp`, `hotspot_id`, `facility_id`.

4. **`incidents`**:
   - **Derived server-side** via outer join between `hotspots` and `facilities`. No separate database table needed.

---

## 8. API Contract & Endpoints (`/api/v1`)

| Endpoint | Method | Params | Description |
|---|---|---|---|
| `/api/v1/health` | GET | None | System & DB health status |
| `/api/v1/hotspots` | GET | `page`, `page_size`, `type`, `min_confidence`, `severity`, `state`, `city`, `start_date`, `end_date`, `near_lat`, `near_lng`, `radius_km` | List hotspots with optional PostGIS spatial radius filter |
| `/api/v1/hotspots/{id}` | GET | `hotspot_id` | Get single hotspot |
| `/api/v1/facilities` | GET | `page`, `page_size`, `type`, `state`, `city` | List facilities |
| `/api/v1/facilities/{id}` | GET | `facility_id` | Get single facility |
| `/api/v1/alerts` | GET | `page`, `page_size`, `severity`, `acknowledged` | List alerts |
| `/api/v1/alerts/{id}` | GET | `alert_id` | Get single alert |
| `/api/v1/incidents` | GET | `page`, `page_size`, `type`, `severity`, `min_confidence`, `state`, `start_date`, `end_date` | List derived incidents |
| `/api/v1/incidents/{id}` | GET | `incident_id` | Get single derived incident |

---

## 9. Current Validation Status
- **Backend pytest Suite**: `pytest tests/ -v` → **PASS** (15 test cases passing including PostGIS ST_DWithin spatial radius search).
- **TypeScript**: `npx tsc --noEmit` → **PASS** (0 errors).
- **Frontend Build**: `npm run build` → **PASS** (✓ 1739 modules transformed).
- **Runtime Stack**: Both FastAPI (`uvicorn`) and Vite (`npm run dev`) operational and integrated.

---

## 10. Rules for Future AI Coding Agents
1. **Read `context.md`** thoroughly before making modifications to the codebase.
2. **Maintain architectural boundary**: Route -> Schema -> Service -> Repository -> Database.
3. **DO NOT redesign the frozen frontend UI**.
4. **Preserve MapLibre GL + Thunderforest basemap architecture**.
5. **Preserve TanStack Query and Zustand boundaries**.
6. **Maintain strict TypeScript discipline** (`npx tsc --noEmit`).
7. **Never expose secrets or DB credentials**. Always use environment variables (`.env`).
8. **Keep database India-wide capable** (do not hardcode Gujarat-specific constraints into schema).
