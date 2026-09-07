# ThermalTrace

**AI-Based Detection and Classification of Industrial Fires and Persistent Thermal Sources**
Built for Smart India Hackathon 2026 — SIH26162

ThermalTrace is a geospatial intelligence platform that classifies satellite thermal detections across India. It combines NASA FIRMS satellite data, OpenStreetMap infrastructure, and an XGBoost classifier to answer a question raw hotspot data can't: *what kind of source is this?*

A satellite thermal anomaly only tells you something is hot. ThermalTrace analyzes historical persistence, thermal intensity, and nearby infrastructure to classify each source as an **industrial thermal source, mining source, agricultural fire, or unclassified**.

---

## Problem Statement

**SIH26162** — Satellite-based thermal detection systems flag hotspots but provide no context on their cause: industrial activity, mining, agricultural burning, seasonal fire, or something needing further investigation. ThermalTrace addresses this by fusing satellite observations with spatial infrastructure context through machine learning.

---

## Pipeline Overview

```
NASA FIRMS Satellite Observations
              │
              ▼
       Data Normalization
              │
              ▼
      Spatial Source Grouping
              │
              ▼
    Temporal Persistence Analysis
              │
              ▼
      OpenStreetMap Context
              │
              ▼
       Feature Engineering
              │
              ▼
      XGBoost Classification
              │
              ▼
        FastAPI Backend
              │
              ▼
   React + TypeScript Geospatial UI
```

---

## Machine Learning

### Dataset

- **5,706,071** raw VIIRS satellite observations across India (~2022–2026)
- Grouped into **~4.7 million spatial source groups** using ~100m spatial cells, since the same physical source can be observed multiple times at slightly different coordinates
- For each group: observation count, first/last seen dates, active duration, active months, monsoon activity, mean FRP, FRP variability, and temporal persistence

### Weak Supervision

There's no large independently verified dataset labeling millions of thermal observations, so ThermalTrace uses a weak-labeling strategy grounded in observable evidence:

```
Persistent Source
       │
       ├── Near Industrial OSM  →  Industrial Thermal Source
       ├── Near Quarry OSM      →  Mining Thermal Source
       └── Insufficient Evidence → Unclassified

Non-persistent, no nearby industrial infrastructure → Agricultural Fire
```

These are **weak labels**, not verified ground truth — an important distinction when interpreting model performance.

### Features

The final production model uses 8 features:

| Feature | Captures |
|---|---|
| `obs_count` | Persistence |
| `log_mean_frp` | Thermal intensity |
| `log_std_frp` | Thermal variability |
| `frp_cv` | Thermal behavior |
| `months_active` | Temporal spread |
| `nearest_osm_distance_km` | Spatial context |
| `active_duration_days` | Persistence over time |
| `first_seen_month` | Seasonality |

Raw latitude/longitude were deliberately excluded to prevent the model from memorizing geographic locations instead of learning generalizable patterns.

### Model Selection & Results

Benchmarked: Dummy baseline → Logistic Regression → Random Forest → **XGBoost** (with sample/class weighting)

| Metric | Result |
|---|---|
| Test Accuracy | **95.93%** |
| Balanced Accuracy | **89.20%** |
| Macro ROC-AUC | **0.9932** |
| Weighted ROC-AUC | **0.9976** |

Strongest performance on the agricultural-fire and unclassified categories. The main remaining challenge is separating industrial from mining sources, since both can show similar persistent thermal behavior.

**Important:** these metrics evaluate performance against the project's weak-label framework, not independently verified real-world ground truth.

---

## Features

- **🛰️ NASA FIRMS Integration** — VIIRS Suomi-NPP, NOAA-20, NOAA-21; hourly synchronization
- **🏭 Facility Intelligence** — ~80K OSM infrastructure features (industrial areas, quarries, chimneys, power plants, works), filterable on the map
- **🔥 Thermal Hotspot Intelligence** — per-hotspot FRP, confidence, land-cover context, ML classification, and model version
- **🌍 Interactive Geospatial Visualization** — MapLibre-based map for exploring hotspots, facilities, and their spatial relationships

---

## Architecture

```
                       ┌─────────────────────┐
                       │     NASA FIRMS      │
                       │  VIIRS Observations │
                       └──────────┬──────────┘
                                  ▼
                       ┌─────────────────────┐
                       │  FIRMS Ingestion    │
                       │   Normalization     │
                       └──────────┬──────────┘
                                  ▼
                       ┌─────────────────────┐
                       │ PostgreSQL/PostGIS  │
                       │     Hotspots        │
                       └──────────┬──────────┘
                                  ▼
                       ┌─────────────────────┐
                       │  Source Grouping    │
                       │  & Feature Builder  │
                       └──────────┬──────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
          ┌─────────────────┐        ┌─────────────────┐
          │  OSM Features    │        │ Temporal / FRP  │
          │  Infrastructure  │        │    Features     │
          └────────┬────────┘        └────────┬────────┘
                    └─────────────┬────────────┘
                                  ▼
                         ┌─────────────────┐
                         │     XGBoost     │
                         │ Classification  │
                         └────────┬────────┘
                                  ▼
                         ┌─────────────────┐
                         │   FastAPI API   │
                         └────────┬────────┘
                                  ▼
                         ┌─────────────────┐
                         │ React + TS UI   │
                         │   MapLibre GIS  │
                         └─────────────────┘
```

### Tech Stack

**Frontend** (built by Yash Pandey): React, TypeScript, Vite, MapLibre, Zustand, TanStack Query, Axios, OpenFreeMap

**Backend**: Python, FastAPI, Uvicorn, SQLAlchemy, asyncpg, GeoAlchemy2 — handles FIRMS ingestion, normalization, hotspot/facility APIs, ML inference, and spatial queries

**Database & Geospatial**: PostgreSQL + PostGIS (Supabase) — powers nearest-infrastructure spatial queries

**Cache**: Redis (Upstash) — caching and distributed locking for sync workflows, not the source of truth

### Deployment

```
Vercel (React Frontend)
        │
        ▼
Render (FastAPI Backend)
        │
   ┌────┼────┐
   ▼    ▼    ▼
Supabase  Redis  NASA FIRMS
```

---

## Project Statistics

| Component | Scale |
|---|---|
| Historical VIIRS observations | 5.7M+ |
| Spatial source groups | 4.7M+ |
| Supervised training source groups | 41K+ |
| OSM infrastructure features | 80K+ |
| Production facility features | 79K+ |
| Final model features | 8 |
| Test accuracy | 95.93% |
| Macro ROC-AUC | 0.9932 |
| Balanced accuracy | 89.20% |
| FIRMS sync interval | ~1 hour |

---

## Design Principles

1. **A thermal anomaly isn't automatically a "fire."** Every observation is treated as a satellite sensor reading, not an assumed physical event.
2. **Persistence matters.** Repeated detections at the same location over months carry more signal than isolated pings.
3. **Spatial context matters.** Nearby industrial or mining infrastructure adds evidence about the likely source.
4. **Weak labels aren't ground truth.** They're useful for a scalable prototype, not a substitute for manual verification.
5. **Geographic memorization is minimized.** Lat/long were excluded from the final feature set for this reason.

---

## Current Limitations

- **Weak supervision** — training labels are rule-derived, not independently verified
- **Industrial vs. mining** — both can show similar persistent, high-intensity thermal signatures
- **OSM completeness** — infrastructure tagging quality varies by region
- **Satellite resolution** — inherent spatial/temporal limits of VIIRS data
- **Source attribution** — a classification is an evidence-based inference, not proof

## Future Improvements

Independently verified training data, human-in-the-loop label validation, improved industrial/mining separation, additional satellite sources, higher-resolution imagery, land-cover integration, confidence calibration, explainable ML (SHAP), and multi-sensor fusion.

---

## Getting Started

### Backend

```bash
cd backend
python -m venv .venv
# activate the environment
pip install -r requirements.txt
```

Configure environment variables:

```
DATABASE_URL=...
DATABASE_URL_SESSION=...
REDIS_URL=...
FIRMS_MAP_KEY=...
FRONTEND_ORIGIN=...
ENVIRONMENT=development
```

Run:

```bash
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
```

Configure:

```
VITE_API_URL=...
VITE_SUPABASE_URL=...
VITE_SUPABASE_ANON_KEY=...
VITE_MAP_PROVIDER=openfreemap
```

Run:

```bash
npm run dev      # development
npm run build    # production
```

**Never commit secrets** — FIRMS API keys, Supabase credentials, database passwords, Redis credentials, or environment files.

---

## Responsible Interpretation

ThermalTrace is a decision-support system, not an automated authority on the cause of a thermal event. A classification should be read alongside satellite evidence, temporal behavior, spatial context, and model confidence — the goal is to help prioritize areas for investigation, not to make a final call on its own.

---

## Team

- **Yash Pandey** — Frontend (React, TypeScript, MapLibre, UI/UX)
- **Vedagya** — Backend architecture, ML pipeline, data engineering, model integration

## Acknowledgements

Built for **Smart India Hackathon 2026** — Problem Statement **SIH26162**: AI-Based Detection and Classification of Industrial Fires and Persistent Thermal Sources Using NASA FIRMS, OSM & Satellite Data.

Technologies: NASA FIRMS, VIIRS, OpenStreetMap, PostGIS, OpenFreeMap, XGBoost, FastAPI, React, TypeScript

---

*Satellite Data → Geospatial Context → Machine Learning → Actionable Intelligence*
