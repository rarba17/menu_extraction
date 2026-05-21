# 🍽️ AI-Powered Menu Extraction System

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green?logo=fastapi)
![Streamlit](https://img.shields.io/badge/Streamlit-1.29-red?logo=streamlit)
![OpenAI GPT-4o mini](https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991?logo=openai)
![Docker](https://img.shields.io/badge/Docker-Containerized-blue?logo=docker)
![Redis](https://img.shields.io/badge/Redis-7.2-red?logo=redis)
![License](https://img.shields.io/badge/License-MIT-yellow)

**Extract structured data from restaurant menus in any language, from any image or PDF — powered by Google Gemini AI.**

[Quick Start](#-quick-start) • [Architecture](#-architecture) • [API Reference](#-api-reference) • [Docker Setup](#-docker-setup) • [Configuration](#-configuration)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Project Structure](#-project-structure)
- [Tech Stack](#-tech-stack)
- [Quick Start](#-quick-start)
- [Docker Setup](#-docker-setup)
- [API Reference](#-api-reference)
- [Data Models](#-data-models)
- [Performance Features](#-performance-features)
- [Configuration](#-configuration)
- [Development Guide](#-development-guide)
- [Makefile Commands](#-makefile-commands)
- [Troubleshooting](#-troubleshooting)

---

## 🌟 Overview

The **AI-Powered Menu Extraction System** is a full-stack application that intelligently parses restaurant menus from images and PDFs into structured, machine-readable JSON data. It leverages Google Gemini's multimodal vision capabilities to understand menus in any language, automatically translating content to English while preserving the original text.

The system is designed for:
- **Restaurant aggregators** building menu databases
- **Food delivery platforms** onboarding new restaurants
- **Menu digitization services** at scale
- **Research and analytics** on food trends

---

## ✨ Features

| Feature | Description |
|---|---|
| 📸 **Image Extraction** | Extract menu data from JPG, PNG images using Gemini Vision |
| 📄 **PDF Support** | Handle both text-based and image-based PDFs |
| 🌍 **Multilingual** | Detect and translate menus from any language (Chinese, Arabic, Hindi, etc.) |
| ⚡ **Smart Caching** | SHA-256 content hashing with thread-safe LRU cache (TTL-aware) |
| 🔄 **Async Processing** | Priority queue with configurable concurrency and rate limiting |
| 🖼️ **Image Optimization** | Auto-orient, smart resize, and pipeline before AI processing |
| 📊 **Structured Output** | Rich JSON schema with items, prices, allergens, dietary tags |
| 🏥 **Health Monitoring** | `/health` and `/cache/stats` endpoints for observability |
| 🐳 **Fully Containerized** | Multi-stage Docker build with dev/prod configurations |
| 🔀 **Nginx Proxy** | Rate limiting, compression, WebSocket support for Streamlit |

---

## 🏛️ Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Browser                        │
└──────────────────────────┬──────────────────────────────────┘
                           │  HTTP / WebSocket
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Nginx (Port 80/443)                        │
│         Reverse Proxy | Rate Limiting | Compression          │
│   /api/* → Backend        /  → Frontend                     │
└──────────────┬──────────────────────┬───────────────────────┘
               │                      │
               ▼                      ▼
┌──────────────────────┐   ┌─────────────────────────┐
│   FastAPI Backend    │   │   Streamlit Frontend     │
│     (Port 8000)      │   │      (Port 8501)         │
│                      │   │                          │
│  ┌────────────────┐  │   │  ┌───────────────────┐  │
│  │ /extract-menu  │  │   │  │  File Uploader    │  │
│  │/extract-menu   │  │   │  │  Image Preview    │  │
│  │  -batch        │  │   │  │  Results Viewer   │  │
│  │ /health        │  │   │  │  JSON Explorer    │  │
│  │ /cache/stats   │  │   │  └───────────────────┘  │
│  └────────────────┘  │   └─────────────────────────┘
│                      │
│  ┌────────────────┐  │
│  │ OpenAIService  │  │──────────────► OpenAI API
│  │ PDFProcessor   │  │                (openai-gpt-4o-mini)
│  │ ImagePipeline  │  │
│  │ CacheManager   │  │
│  │MultilingualHdl │  │
│  │ AsyncQueue     │  │
│  └────────────────┘  │
│          │           │
│          ▼           │
│  ┌────────────────┐  │
│  │  Redis Cache   │◄─┘
│  │   (Port 6379)  │
│  │  LRU + TTL     │
│  └────────────────┘
└──────────────────────┘
```

### Request Processing Pipeline

```
File Upload (Image/PDF)
        │
        ▼
┌───────────────┐
│  File Validator│  ← Type check (jpg/png/pdf) + Size check (≤10MB)
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ Cache Lookup  │  ← SHA-256 hash of file content
└───────┬───────┘
        │ Cache Miss
        ▼
   ┌────┴────┐
   │  PDF?   │
   └────┬────┘
  Yes   │   No (Image)
   ▼    │      ▼
Text   │   ┌──────────────────┐
Extract│   │  Image Pipeline  │
       │   │  1. Auto-orient  │
       │   │  2. Smart resize │
       │   │     (≤0.5MB)     │
       │   └────────┬─────────┘
       │            │
       ▼            ▼
┌──────────────────────────────┐
│  MultilingualMenuHandler     │
│  1. Extract original text    │
│  2. Detect language (AI)     │
│  3. Extract structured data  │
│  4. Translate to English     │
└──────────────┬───────────────┘
               │
               ▼
        ┌──────────┐
        │  Cache   │  ← Store result (TTL: 24h)
        │  Store   │
        └──────────┘
               │
               ▼
      ExtractionResponse
   (MenuSchema + timing + cached flag)
```

---

## 📁 Project Structure

```
menu_extraction/
├── backend/
│   ├── main.py                          # FastAPI app, routes, CORS, startup
│   ├── config.py                        # Env-based configuration (Pydantic)
│   ├── models/
│   │   └── schemas.py                   # Pydantic data models
│   ├── services/
│   │   ├── gemini_service.py            # Gemini Vision API wrapper
│   │   ├── pdf_processor.py             # PDF → text/image extraction
│   │   └── performance/
│   │       ├── async_queue.py           # Priority async task queue
│   │       ├── cache_manager.py         # LRU + TTL cache with SHA-256 hashing
│   │       ├── connection_pool.py       # API connection pooling
│   │       ├── distributed_processor.py # Distributed task processing
│   │       ├── image_pipeline.py        # Image optimization pipeline
│   │       ├── load_balancer.py         # Request load balancing
│   │       ├── multilingual_handler.py  # Multilingual extraction & translation
│   │       └── streaming_handler.py     # Streaming response handler
│   ├── configs/
│   │   └── performance_configs.py       # Performance tuning constants
│   └── utils/                           # Shared utilities
│
├── frontend/
│   └── streamlit_app.py                 # Streamlit UI (upload, preview, results)
│
├── docker/
│   ├── entrypoint.sh                    # Unified entrypoint (preflight, signals)
│   └── nginx/
│       └── nginx.conf                   # Reverse proxy config
│
├── outputs/                             # Extracted/cropped images (persisted)
├── logs/                                # Application logs
│
├── Dockerfile                           # Multi-stage (builder → runtime → dev)
├── docker-compose.yml                   # Base service definitions
├── docker-compose.override.yml          # Development overrides (hot-reload)
├── docker-compose.prod.yml              # Production overrides (gunicorn, hardened)
├── Makefile                             # Developer command shortcuts
├── requirements.txt                     # Python dependencies
├── run.py                               # Local run script (without Docker)
├── .env.example                         # Environment variable template
└── .dockerignore                        # Build context exclusions
```

---

## 🛠️ Tech Stack

### Backend
| Component | Technology | Purpose |
|---|---|---|
| API Framework | FastAPI 0.104 | Async REST API with OpenAPI docs |
| AI Model | Google Gemini 2.5 Flash | Multimodal vision + text understanding |
| AI SDK | google-generativeai + LangChain | Gemini API client |
| PDF Processing | pypdf + pdf2image | Text extraction and PDF→image conversion |
| Image Processing | OpenCV + Pillow | Optimization, orientation, resizing |
| OCR Backup | EasyOCR | Fallback for low-quality scans |
| Caching | Redis 7.2 + In-memory LRU | Content-addressable result caching |
| Server (Dev) | Uvicorn | ASGI server with auto-reload |
| Server (Prod) | Gunicorn + Uvicorn workers | Multi-process production serving |
| Validation | Pydantic v2 | Schema validation and serialization |

### Frontend
| Component | Technology | Purpose |
|---|---|---|
| UI Framework | Streamlit 1.29 | Interactive web UI |
| HTTP Client | Requests | Backend API communication |
| Image Display | Pillow | Preview uploaded images |

### Infrastructure
| Component | Technology | Purpose |
|---|---|---|
| Containerization | Docker (multi-stage) | Reproducible builds |
| Orchestration | Docker Compose v2 | Multi-service coordination |
| Reverse Proxy | Nginx 1.25 | Load balancing, SSL, rate limiting |
| Caching Layer | Redis 7.2 (Alpine) | Persistent + in-memory caching |
| Base Image | Python 3.11-slim | Minimal production image |

---

## 🚀 Quick Start

### Prerequisites

- **Docker** ≥ 24.0 and **Docker Compose** v2
- A **Google Gemini API key** (free at [ai.google.dev](https://ai.google.dev/))

### 1. Clone & Setup

```bash
git clone <your-repo-url>
cd menu_extraction
make setup        # Creates .env from template, makes required directories
```

### 2. Add Your API Key

Edit `.env` and set your key:
```
GEMINI_API_KEY=your_actual_key_here
```

### 3. Build & Run

```bash
make build        # Build Docker images (~5-10 min first time)
make up           # Start all services
```

### 4. Open the App

| Service | URL |
|---|---|
| 🖥️ Streamlit Frontend | http://localhost:8501 |
| ⚡ FastAPI Backend | http://localhost:8000 |
| 📖 API Docs (Swagger) | http://localhost:8000/docs |
| 💚 Health Check | http://localhost:8000/health |

### Running Without Docker (Local Dev)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Terminal 1 - Backend
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 - Frontend
streamlit run frontend/streamlit_app.py --server.port 8501
```

---

## 🐳 Docker Setup

### Services

| Service | Image | Ports | Role |
|---|---|---|---|
| `backend` | `menu-extraction-backend:dev` | `8000` | FastAPI API server |
| `frontend` | `menu-extraction-frontend:dev` | `8501` | Streamlit UI |
| `redis` | `redis:7.2-alpine` | `6380` (host) | Result caching |
| `nginx` | `nginx:1.25-alpine` | `80`, `443` | Reverse proxy (optional) |

### Dockerfile Stages

```
Stage 1: builder
  └─ python:3.11-slim
  └─ Install build deps (gcc, libffi...)
  └─ Create /opt/venv
  └─ pip install -r requirements.txt + gunicorn

Stage 2: runtime
  └─ python:3.11-slim (fresh, no build tools)
  └─ Copy /opt/venv from builder
  └─ Install OS runtime libs (poppler-utils, libmagic1, tesseract-ocr, libgl1)
  └─ Create non-root user appuser (UID 1001)
  └─ HEALTHCHECK: curl /health every 30s

Stage 3: development (extends runtime)
  └─ Add pytest, black, isort, flake8, ipython
  └─ APP_ENV=development, LOG_LEVEL=debug
```

### Environments

**Development** (default with `make up`):
- Hot-reload for both backend and frontend — edit code, see changes instantly
- Source code mounted as volumes (`./backend:/app/backend`)
- Debug logging enabled
- Redis data not persisted (faster)

**Production** (with `make up-prod`):
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```
- Gunicorn with multiple Uvicorn workers (`WEB_CONCURRENCY=4`)
- Source code baked into image (no volume mounts)
- Redis with persistence (AOF + RDB snapshots)
- Nginx always-on for external traffic

### Docker Networks

```
192.168.100.0/24  ← app-network (backend ↔ frontend ↔ redis)
auto-assigned     ← frontend-network (nginx ↔ frontend)
```

---

## 📡 API Reference

### Base URL
```
http://localhost:8000
```

### Endpoints

#### `GET /health`
Returns service health and cache statistics.

```json
{
  "status": "healthy",
  "cache": {
    "size": 42,
    "max_size": 200,
    "hits": 387,
    "misses": 55,
    "hit_rate": "87.56%"
  },
  "service": "menu-extraction-system"
}
```

#### `POST /extract-menu`
Extract structured data from a single menu file.

**Request:** `multipart/form-data`
| Field | Type | Required | Description |
|---|---|---|---|
| `file` | File | ✅ | Image (jpg/png) or PDF |
| `priority` | string | ❌ | `low` \| `normal` \| `high` \| `critical` |

**Response:**
```json
{
  "success": true,
  "data": {
    "restaurant_name": "Bella Italia",
    "menu_language": "it",
    "menu_items": [
      {
        "item_name": "Spaghetti Carbonara",
        "translated_item_name": "Spaghetti Carbonara",
        "description": "Con guanciale, uova, pecorino romano",
        "translated_description": "With guanciale, eggs, pecorino romano",
        "category": "Main Course",
        "price": "14.50",
        "currency": "EUR",
        "calories": "680",
        "allergens": ["Eggs", "Dairy", "Gluten"],
        "dietary_tags": [],
        "image_path": null
      }
    ]
  },
  "processing_time": 3.42,
  "cached": false
}
```

#### `POST /extract-menu-batch`
Extract from multiple files in one request.

**Request:** `multipart/form-data` with multiple `files`

**Response:**
```json
{
  "results": [
    {"filename": "menu1.pdf", "success": true, "data": {...}},
    {"filename": "menu2.jpg", "success": false, "error": "..."}
  ],
  "total": 2
}
```

#### `GET /cache/stats`
Returns LRU cache hit/miss statistics.

#### `GET /cache/clear`
Clears all in-memory cache entries.

---

## 📊 Data Models

### `MenuItem`
```python
class MenuItem(BaseModel):
    item_name: str                         # Original dish name
    translated_item_name: Optional[str]    # English translation
    description: Optional[str]             # Original description
    translated_description: Optional[str]  # English translation
    category: Optional[str]                # Appetizer / Main / Dessert / Drink
    price: Optional[str]                   # Price as string (e.g., "14.50")
    currency: Optional[str]                # ISO code: USD, EUR, INR, etc.
    calories: Optional[str]                # Caloric info if listed
    allergens: List[str]                   # ["Nuts", "Dairy", "Gluten"]
    dietary_tags: List[str]                # ["Vegan", "Gluten-Free", "Jain"]
    image_path: Optional[str]              # Path to cropped dish image
```

### `MenuSchema`
```python
class MenuSchema(BaseModel):
    restaurant_name: Optional[str]         # Restaurant name if visible
    menu_language: Optional[str]           # ISO 639-1 language code
    menu_items: List[MenuItem]             # All extracted items
```

### `ExtractionResponse`
```python
class ExtractionResponse(BaseModel):
    success: bool
    data: Optional[MenuSchema]
    error: Optional[str]
    processing_time: Optional[float]       # Seconds
    cached: bool                           # True if result came from cache
```

---

## ⚡ Performance Features

### 1. Content-Addressable Caching
Every uploaded file is hashed with **SHA-256** before processing. If the same file (or identical content) was processed before, the cached result is returned instantly — avoiding a redundant Gemini API call.

```
File Content → SHA-256 Hash → Cache Lookup → Hit: return instantly
                                           └─ Miss: process + store
```

### 2. Thread-Safe LRU Cache
In-memory **Least Recently Used (LRU)** cache with:
- **200 slots** for content cache (24-hour TTL)
- **100 slots** for semantic cache (7-day TTL)
- Thread-safe via `threading.RLock()`
- Automatic eviction of expired entries

### 3. Async Priority Queue
Tasks are processed via a priority queue supporting 4 levels:
- `CRITICAL` → `HIGH` → `NORMAL` → `LOW`
- Configurable max concurrency (`max_concurrent=10`)
- Rate limiting (`rate_limit_per_minute=100`)

### 4. Image Optimization Pipeline
Before sending to Gemini:
1. **Auto-orient**: EXIF-based rotation correction
2. **Smart resize**: Target ≤0.5MB to reduce API latency
3. Avoids sending unnecessarily large images

### 5. Multilingual 3-Step Pipeline
```
Step 1: Extract raw text in original language (no translation yet)
Step 2: Detect language using Gemini AI (ISO 639-1 code + confidence)
Step 3: Re-extract with language context → structured JSON + translations
```
Gemini natively reads Chinese, Arabic, Hindi, Devanagari, Japanese, etc. without OCR.

### 6. Production: Gunicorn + Uvicorn Workers
```
gunicorn backend.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers <2*CPU+1>         # Auto-calculated
  --timeout 120               # For long AI inference
  --graceful-timeout 30       # Clean shutdown
```

---

## ⚙️ Configuration

All configuration is via environment variables in `.env`.

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | *(required)* | Google Gemini API key |
| `APP_ENV` | `development` | `development` or `production` |
| `LOG_LEVEL` | `info` | `debug` \| `info` \| `warning` \| `error` |
| `BACKEND_PORT` | `8000` | FastAPI listen port |
| `FRONTEND_PORT` | `8501` | Streamlit listen port |
| `BACKEND_URL` | `http://backend:8000` | Frontend → Backend URL (Docker hostname) |
| `MAX_FILE_SIZE` | `10485760` | Max upload size in bytes (10MB) |
| `WEB_CONCURRENCY` | `2` | Gunicorn worker count |
| `MAX_WORKERS` | `4` | Worker count ceiling |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL |
| `REDIS_MAX_MEMORY` | `256mb` | Redis memory limit |
| `REDIS_PASSWORD` | *(empty)* | Redis auth (set in production!) |

Copy `.env.example` → `.env` to get started:
```bash
cp .env.example .env
```

---

## 👨‍💻 Development Guide

### Hot Reload
Both services support hot reload in development:

- **Backend**: Change any file in `backend/` → Uvicorn automatically reloads
- **Frontend**: Change `frontend/streamlit_app.py` → Streamlit reloads on save

### Running Tests
```bash
make test                   # Run pytest in backend container
make test-watch             # Watch mode
```

### Code Quality
```bash
make lint                   # Check: black + isort + flake8
make format                 # Auto-fix: black + isort
```

### Adding a New API Endpoint
1. Add the route to `backend/main.py`
2. Add Pydantic models to `backend/models/schemas.py` if needed
3. Add service logic to `backend/services/`
4. The dev server reloads automatically

### Inspecting Redis
```bash
make shell-redis            # Opens redis-cli
> KEYS *                    # List all cached keys
> GET <key>                 # View cached data
> TTL <key>                 # Check time-to-live
```

### Viewing Backend Logs
```bash
make logs-backend           # Follow backend logs
make logs-frontend          # Follow frontend logs
make logs                   # Follow all service logs
```

---

## 📋 Makefile Commands

```bash
# Setup
make setup              # First-time setup (copy .env, create dirs)
make help               # Show all available commands

# Build
make build              # Build development images
make build-prod         # Build production images (no cache)
make build-no-cache     # Force rebuild dev images

# Run
make up                 # Start development stack
make up-prod            # Start production stack
make up-with-nginx      # Start with Nginx reverse proxy
make down               # Stop all services
make restart            # Restart all services
make restart-backend    # Restart backend only
make restart-frontend   # Restart frontend only

# Logs
make logs               # Follow all logs
make logs-backend       # Backend logs only
make logs-frontend      # Frontend logs only

# Shell Access
make shell-backend      # Bash inside backend container
make shell-frontend     # Bash inside frontend container
make shell-redis        # Redis CLI

# Testing & Quality
make test               # Run pytest
make lint               # Run linters
make format             # Auto-format code

# Monitoring
make health             # Check all service health endpoints
make ps                 # Show container status
make stats              # Live CPU/memory usage

# Cache Management
make cache-clear        # Clear app cache via API
make redis-flush        # Flush all Redis data (with confirmation)

# Cleanup
make clean              # Remove containers + volumes
make clean-images       # Remove project Docker images
make clean-all          # Full cleanup + system prune

# Production
make deploy             # build-prod + up-prod
```

---

## 🔒 Security

- **Non-root container user**: All containers run as `appuser` (UID 1001)
- **No secrets in images**: API keys injected via env at runtime only
- **Redis not publicly exposed**: Internal Docker network only in production
- **Nginx security headers**: X-Frame-Options, X-XSS-Protection, X-Content-Type-Options
- **Rate limiting**: 10 req/s general, 2 req/s for file upload endpoints
- **File type validation**: Only `jpg`, `jpeg`, `png`, `pdf` accepted
- **File size limit**: 10MB maximum per upload

> ⚠️ **Important**: Never commit your `.env` file. It is already in `.gitignore`.

---

## 🔧 Troubleshooting

### "Cannot connect to backend API"
The frontend `BACKEND_URL` env var must be `http://backend:8000` (Docker service name), not `localhost:8000`. Verify in `.env`:
```
BACKEND_URL=http://backend:8000
```

### "Pool overlaps with other one on this address space"
Another Docker network is using the same subnet. Update `docker-compose.yml`:
```yaml
networks:
  app-network:
    ipam:
      config:
        - subnet: 192.168.200.0/24   # Change to a free subnet
```

### "Port already in use"
Check what's using the port: `ss -tlnp | grep 8000`
Change the port in `.env`: `BACKEND_PORT=8001`

### Backend health check failing
Check backend logs: `make logs-backend`
Common causes:
- `GEMINI_API_KEY` not set in `.env`
- `./outputs` directory not writable → run `chmod 777 outputs`

### Build fails: package not found
Base image is Debian Trixie. Some package names changed:
- `libgl1-mesa-glx` → `libgl1`
- `python3-magic` → `python3-magic` (install via pip: `python-magic`)

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgements

- [Google Gemini](https://ai.google.dev/) — Multimodal AI powering the extraction
- [FastAPI](https://fastapi.tiangolo.com/) — Modern Python API framework
- [Streamlit](https://streamlit.io/) — Rapid ML app development
- [pdf2image](https://github.com/Belval/pdf2image) — PDF to image conversion
- [EasyOCR](https://github.com/JaidedAI/EasyOCR) — OCR fallback engine

---

<div align="center">
Built with ❤️ using FastAPI, Streamlit, and Google Gemini AI
</div>
