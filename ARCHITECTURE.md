# Architectural Analysis: AI-Powered Menu Extraction System

## 1. Executive Summary

The **AI-Powered Menu Extraction System** is a full-stack web application that takes restaurant menu images or PDF files as input and returns structured JSON data containing dish names, descriptions, prices, allergens, dietary tags, and more. It uses Google Gemini's multimodal vision AI to read text directly from images — including menus in non-Latin scripts like Chinese, Arabic, or Hindi — and automatically translates the extracted content to English.

The core problem it solves is the manual, error-prone, and time-consuming process of digitizing restaurant menus. Instead of a human typing out every dish from a photographed menu, the system automates this in 5–15 seconds, producing machine-readable data that restaurant aggregators, food delivery platforms, and analytics teams can immediately consume.

The value delivered is threefold: (1) **speed** — extraction takes seconds instead of minutes, (2) **multilingual capability** — no human translator is needed, and (3) **structured output** — the JSON schema is ready for database insertion without further parsing.

---

## 2. Technology Stack

### Languages & Runtimes

| Technology | Version | Purpose |
|---|---|---|
| **Python** | 3.11 | Primary language for both backend and frontend |
| **Bash** | — | Docker entrypoint script, Makefile commands |

### Frameworks & Libraries

| Technology | Version | Purpose | Why Chosen |
|---|---|---|---|
| **FastAPI** | 0.104.1 | Backend REST API framework | Native async support, automatic OpenAPI/Swagger docs, Pydantic integration, high performance |
| **Streamlit** | 1.35.0 | Frontend UI framework | Rapid prototyping for data/ML apps, no JavaScript needed, built-in file upload and JSON display widgets |
| **Google Gemini (google-generativeai)** | 0.3.2 | AI vision + text model | Multimodal (accepts images + text), strong OCR-like text reading in any language, structured JSON output capability |
| **LangChain** | 0.1.0 | AI orchestration layer | Listed as a dependency for potential chaining of AI prompts (though not heavily used in current code) |
| **Pydantic** | 2.5.0 | Data validation and serialization | Native FastAPI integration, clean schema definitions, automatic type coercion |
| **Uvicorn** | 0.24.0 | ASGI server (development) | Fast, async-native, supports hot-reload |
| **Gunicorn** | 21.2.0 | WSGI/ASGI server (production) | Multi-process worker management, graceful shutdown, production-hardened |
| **pypdf** | 3.17.4 | PDF text extraction | Pure Python, no external dependencies, reliable for text-based PDFs |
| **pdf2image** | 1.16.3 | PDF-to-image conversion | Wraps `poppler-utils` for rendering PDF pages as images for vision AI |
| **OpenCV (opencv-python)** | 4.8.1.78 | Image processing pipeline | Resize, rotation, contrast enhancement (CLAHE) |
| **Pillow** | 10.1.0 | Image manipulation | EXIF orientation handling, image preview in frontend |
| **python-magic** | 0.4.27 | MIME type detection | Libmagic binding for accurate file type validation beyond extension checking |
| **EasyOCR** | 1.7.1 | OCR fallback engine | Listed as optional backup if Gemini vision fails on low-quality scans |
| **Redis** | 7.2 (Alpine) | Caching layer | In-memory key-value store with LRU eviction and TTL support |
| **Requests** | 2.31.0 | HTTP client (frontend) | Simple synchronous HTTP calls from Streamlit to FastAPI |
| **python-dotenv** | 1.0.0 | Environment variable loading | Loads `.env` files into `os.environ` |

### Build Tools & Infrastructure

| Technology | Purpose |
|---|---|
| **Docker** (multi-stage builds) | Reproducible, containerized deployments with builder → runtime → dev stages |
| **Docker Compose** v2 | Multi-service orchestration (backend, frontend, Redis, Nginx) |
| **Nginx** 1.25 | Reverse proxy, rate limiting, gzip compression, WebSocket support |
| **Make** | Developer command shortcuts (build, run, test, deploy) |
| **Render** (render.yaml) | PaaS deployment blueprint for cloud hosting |

---

## 3. High-Level Architecture

### Architectural Style: Layered Monolith with Service-Oriented Internal Structure

A **layered architecture** (also called n-tier architecture) organizes code into horizontal layers where each layer has a specific responsibility and typically depends only on the layer directly below it. The standard flow is: Presentation Layer → Business Logic Layer → Data/Persistence Layer.

This project follows a **layered monolith** pattern: it is a single deployable unit (monolith) but internally organizes its code into distinct layers:

1. **API/Route Layer** (`backend/main.py`) — handles HTTP requests, validation, and response formatting.
2. **Service Layer** (`backend/services/`) — contains business logic for AI extraction, PDF processing, image optimization, caching, and multilingual handling.
3. **Model/Schema Layer** (`backend/models/schemas.py`) — defines data structures using Pydantic.
4. **Infrastructure Layer** (Redis, Docker, Nginx) — handles caching, containerization, and reverse proxying.

Additionally, the system uses a **client-server** pattern with a separate frontend (Streamlit) communicating with the backend (FastAPI) over HTTP.

### ASCII Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                        Client Browser                             │
│                    (User uploads menu file)                        │
└──────────────────────────┬───────────────────────────────────────┘
                           │  HTTP POST /extract-menu
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Nginx Reverse Proxy (optional)                  │
│              Port 80/443 | Rate Limiting | Gzip                   │
│   /api/* → Backend    / → Frontend    /_stcore/stream → WS       │
└──────────┬──────────────────────────┬────────────────────────────┘
           │                          │
           ▼                          ▼
┌──────────────────────┐   ┌────────────────────────────┐
│   FastAPI Backend    │   │   Streamlit Frontend        │
│   (Port 8000)        │   │   (Port 8501)               │
│                      │   │                              │
│  ┌────────────────┐  │   │  ┌──────────────────────┐  │
│  │ Route Handlers │  │   │  │ File Uploader         │  │
│  │ /extract-menu  │  │   │  │ Image Preview         │  │
│  │ /extract-menu  │  │   │  │ Structured Data Tabs  │  │
│  │   -batch       │  │   │  │ Raw JSON Viewer       │  │
│  │ /health        │  │   │  └──────────────────────┘  │
│  │ /cache/stats   │  │   │                              │
│  │ /cache/clear   │  │   │  Talks to backend via       │
│  └───────┬────────┘  │   │  requests.post()            │
│          │           │   └────────────────────────────┘
│          ▼           │
│  ┌───────────────────┴──────────────────────────┐
│  │              Service Layer                    │
│  │                                               │
│  │  GeminiService ──────► Google Gemini API      │
│  │  PDFProcessor                                 │
│  │  ImagePipeline (resize, orient, enhance)      │
│  │  MultilingualMenuHandler (detect + translate) │
│  │  MenuCacheManager (LRU + TTL)                 │
│  │  AsyncPriorityQueue (task scheduling)         │
│  │  GeminiConnectionPool (connection mgmt)       │
│  │  DistributedProcessor (Redis-based workers)   │
│  │  LoadBalancer (system resource monitoring)    │
│  │  StreamingHandler (SSE responses)             │
│  └───────────────────┬──────────────────────────┘
│                      │
│                      ▼
│  ┌──────────────────────────┐
│  │  In-Memory LRU Cache     │
│  │  (thread-safe, TTL-aware)│
│  │  + Redis (optional)      │
│  │  Port 6379               │
│  └──────────────────────────┘
└──────────────────────────────┘
```

---

## 4. Directory & Module Structure

```
menu_extraction/
├── backend/                    # FastAPI application (API + business logic)
│   ├── main.py                 # FastAPI app instance, route definitions, CORS, startup hooks
│   ├── config.py               # Environment-based configuration (simple Config class)
│   ├── models/
│   │   └── schemas.py          # Pydantic data models (MenuItem, MenuSchema, ExtractionResponse)
│   ├── services/
│   │   ├── gemini_service.py   # Google Gemini API wrapper (text + image extraction)
│   │   ├── pdf_processor.py    # PDF text extraction and PDF-to-image conversion
│   │   └── performance/        # Performance optimization modules
│   │       ├── async_queue.py          # Priority-based async task queue
│   │       ├── cache_manager.py        # Thread-safe LRU cache with TTL
│   │       ├── connection_pool.py      # HTTP connection pooling for Gemini API
│   │       ├── distributed_processor.py# Redis-based distributed task processing
│   │       ├── image_pipeline.py       # Image optimization (resize, orient, contrast)
│   │       ├── load_balancer.py        # System resource monitoring + auto-scaling stub
│   │       ├── multilingual_handler.py # Language detection + translation pipeline
│   │       └── streaming_handler.py    # Server-sent events streaming (stub)
│   ├── configs/
│   │   └── performance_configs.py      # Pre-set configuration profiles (dev/prod/enterprise)
│   └── utils/
│       └── file_util.py        # MIME type validation using python-magic
│
├── frontend/
│   └── streamlit_app.py        # Streamlit UI (file upload, preview, results display)
│
├── docker/
│   ├── entrypoint.sh           # Unified container entrypoint (service startup, health checks, signals)
│   └── nginx/
│       ├── nginx.conf          # Nginx reverse proxy configuration
│       └── certs/              # SSL certificate directory (empty by default)
│
├── outputs/                    # Persisted cropped/extracted images from menu processing
├── logs/                       # Application log files (access.log, error.log)
│
├── Dockerfile                  # Multi-stage Dockerfile (builder → runtime → development)
├── Dockerfile.frontend         # Lightweight Streamlit-only Docker image (~200MB)
├── docker-compose.yml          # Base Docker Compose configuration (4 services)
├── docker-compose.override.yml # Development overrides (hot-reload, volume mounts)
├── docker-compose.prod.yml     # Production overrides (gunicorn, hardened Redis, replicas)
├── Makefile                    # Developer command shortcuts (30+ targets)
├── requirements.txt            # Full Python dependencies (backend + frontend combined)
├── requirements-frontend.txt   # Minimal frontend-only dependencies
├── run.py                      # Local development launcher (starts backend + frontend)
├── render.yaml                 # Render.com PaaS deployment blueprint
├── .env.example                # Environment variable template
├── .env                        # Actual environment variables (gitignored)
├── .gitignore                  # Git ignore rules
├── .dockerignore               # Docker build context exclusions
└── README.md                   # Project documentation
```

### Module Relationships and Data Flow

```
frontend/streamlit_app.py
    │
    │  HTTP POST (requests library)
    ▼
backend/main.py  (FastAPI routes)
    │
    ├──► backend/models/schemas.py  (Pydantic validation)
    │
    ├──► backend/services/gemini_service.py  (AI extraction)
    │       │
    │       └──► Google Gemini API (external)
    │
    ├──► backend/services/pdf_processor.py  (PDF handling)
    │       │
    │       ├──► pypdf (text extraction)
    │       └──► pdf2image (page rendering)
    │
    ├──► backend/services/performance/image_pipeline.py  (image optimization)
    │       │
    │       ├──► OpenCV (resize, contrast)
    │       └──► Pillow (EXIF orientation)
    │
    ├──► backend/services/performance/multilingual_handler.py  (language + translation)
    │       │
    │       └──► Google Gemini API (language detection, translation)
    │
    ├──► backend/services/performance/cache_manager.py  (caching)
    │       │
    │       └──► In-memory OrderedDict + optional Redis
    │
    └──► backend/config.py  (configuration)
            │
            └──► .env file / environment variables
```

---

## 5. Core Data Flow

Here is the end-to-end lifecycle of a typical user request — uploading a menu image and receiving structured JSON data:

1. **User uploads a file** in the Streamlit frontend (`frontend/streamlit_app.py:47`). The file uploader widget accepts JPG, JPEG, PNG, or PDF files.

2. **Frontend sends HTTP POST** to the backend API (`frontend/streamlit_app.py:70`). The file is wrapped in a `multipart/form-data` request and sent to `{BACKEND_URL}/extract-menu`.

3. **Nginx reverse proxy** (if used) receives the request, applies rate limiting (2 req/s for upload endpoints), gzip compression, and forwards it to the FastAPI backend on port 8000 (`docker/nginx/nginx.conf:166`).

4. **FastAPI route handler** (`backend/main.py:82`) receives the request and:
   - a. Validates the file extension is one of `jpg`, `jpeg`, `png`, `pdf` (`main.py:106-113`).
   - b. Checks the file size does not exceed `MAX_FILE_SIZE` (10MB) (`main.py:116-124`).
   - c. Reads the file content and computes a SHA-256 hash (`main.py:127-128`).

5. **Cache lookup** (`main.py:131`). The `MenuCacheManager` checks if this exact file content has been processed before using the SHA-256 hash as the cache key. If found, the cached `MenuSchema` is returned immediately with `cached: true` — skipping all AI processing.

6. **File is saved temporarily** to `/tmp/{hash}_{filename}` (`main.py:142-144`).

7. **File-type branching** (`main.py:149-184`):
   - **If PDF**: `PDFProcessor.extract_text_from_pdf()` attempts text extraction using `pypdf`. If sufficient text (>100 chars) is found, `GeminiService.extract_menu_from_text()` processes it. If the PDF is image-based (no extractable text), `PDFProcessor.extract_images_from_pdf()` converts pages to images via `pdf2image`, and the first page is passed through the image pipeline.
   - **If Image**: `ImagePipeline.auto_orient()` corrects EXIF rotation, then `ImagePipeline.smart_resize()` reduces the image to ≤0.5MB while maintaining ≥800px on the longest dimension.

8. **Multilingual extraction** (`main.py:162,181`). The optimized image is passed to `MultilingualMenuHandler.extract_multilingual_menu()`, which:
   - a. Sends the image to Gemini with a prompt to extract all text in the original language.
   - b. Detects the menu's language using a separate Gemini call (`detect_language()`).
   - c. Sends a second structured extraction prompt with language context, requesting both original text and English translations.
   - d. Returns a dictionary matching the `MenuSchema` structure.

9. **Result caching** (`main.py:187-189`). The extracted `MenuSchema` is serialized to a dictionary and stored in the LRU cache with a 24-hour TTL, keyed by the SHA-256 hash.

10. **Response construction** (`main.py:193-198`). An `ExtractionResponse` Pydantic model is built with `success: true`, the `MenuSchema` data, processing time in seconds, and `cached: false`.

11. **Temporary file cleanup** (`main.py:211-217`). The `finally` block removes any temporary files created during processing.

12. **Frontend receives and displays** the response (`frontend/streamlit_app.py:72-132`). Three tabs are rendered: Structured Data (formatted view), Raw JSON (complete output), and Extracted Images (cropped dish images from the `outputs/` directory).

---

## 6. Key Design Patterns & Principles

### 6.1 Service Layer Pattern

**What it is:** The Service Layer pattern separates business logic from the presentation/API layer. Services encapsulate domain operations and can be reused across different entry points (API routes, CLI, batch jobs).

**Where it appears:** Every file under `backend/services/` is a service. `GeminiService` (`backend/services/gemini_service.py:10`) encapsulates all Gemini API interactions. `PDFProcessor` (`backend/services/pdf_processor.py:8`) encapsulates PDF handling. `ImagePipeline` (`backend/services/performance/image_pipeline.py:11`) encapsulates image optimization. The route handlers in `main.py` delegate to these services rather than implementing logic inline.

### 6.2 Singleton Pattern (Module-Level)

**What it is:** The Singleton pattern ensures a class has only one instance and provides a global point of access to it. In Python, module-level instances achieve this naturally because modules are imported only once.

**Where it appears:** In `backend/main.py:37-42`, all services are instantiated at module level:
```python
gemini_service = GeminiService()
pdf_processor = PDFProcessor()
image_pipeline = ImagePipeline()
cache_manager = MenuCacheManager()
multilingual_handler = MultilingualMenuHandler()
task_queue = AsyncPriorityQueue(...)
```
These singletons are shared across all HTTP requests within the same process, avoiding redundant initialization (e.g., re-configuring the Gemini API client on every request).

### 6.3 Strategy Pattern

**What it is:** The Strategy pattern defines a family of algorithms, encapsulates each one, and makes them interchangeable. The client selects which strategy to use at runtime.

**Where it appears:** In `backend/main.py:149-184`, the file processing logic branches based on file type. For PDFs, one strategy is used (text extraction first, then image fallback). For images, a different strategy is used (auto-orient → resize → multilingual extraction). The `MultilingualMenuHandler` also provides multiple strategies: `extract_multilingual_menu()` for general menus and `handle_script_menus()` for non-Latin scripts.

### 6.4 Builder Pattern (Configuration Profiles)

**What it is:** The Builder pattern constructs complex objects step by step. A variant is providing pre-configured presets for different environments.

**Where it appears:** `backend/configs/performance_configs.py` defines three configuration profiles — `DEV_CONFIG`, `PROD_CONFIG`, and `ENTERPRISE_CONFIG` — each with different values for connection pool sizes, cache sizes, concurrency limits, and model selection. This allows the system to scale from a single developer machine to an enterprise deployment by simply selecting a different profile.

### 6.5 Decorator Pattern (Middleware)

**What it is:** The Decorator pattern adds responsibilities to objects dynamically without modifying their structure. In web frameworks, middleware acts as a decorator around request/response handling.

**Where it appears:** `backend/main.py:28-34` adds CORS middleware to the FastAPI app:
```python
app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)
```
This wraps every route handler with CORS header injection. Nginx also acts as a decorator layer, adding rate limiting, gzip compression, and security headers before requests reach the backend.

### 6.6 Priority Queue Pattern

**What it is:** A priority queue processes items based on their priority level rather than FIFO (first-in, first-out) order. Higher-priority items are processed first.

**Where it appears:** `backend/services/performance/async_queue.py:32` implements `AsyncPriorityQueue` using Python's `heapq` module. Tasks are wrapped in `PrioritizedTask` objects with four priority levels: `CRITICAL` (0), `HIGH` (1), `NORMAL` (2), `LOW` (3). The queue supports configurable concurrency limits and rate limiting. Note: this queue is instantiated in `main.py:42` but not actively used in the current route handlers — it is prepared for future async batch processing.

### 6.7 LRU Cache Pattern (Least Recently Used)

**What it is:** An LRU cache evicts the least recently accessed items when it reaches capacity, ensuring that frequently used data stays in memory.

**Where it appears:** `backend/services/performance/cache_manager.py:12` implements `LRUCache` using `collections.OrderedDict`. When an item is accessed via `get()`, it is moved to the end of the ordered dict (most recently used). When capacity is exceeded, the oldest item (first in the dict) is evicted. TTL (time-to-live) support adds expiration on top of LRU eviction.

### 6.8 Dependency Injection (Manual)

**What it is:** Dependency Injection (DI) is a pattern where objects receive their dependencies from external sources rather than creating them internally. This improves testability and flexibility.

**Where it appears:** While there is no formal DI framework, the codebase uses manual DI. Services are instantiated in `main.py` and used directly by route handlers. The `MultilingualMenuHandler` receives its model configuration from `backend/config.py:9` via the shared `config` singleton. The `DistributedProcessor` (`backend/services/performance/distributed_processor.py:13`) accepts `redis_url` as a constructor parameter.

### 6.9 Failover Pattern

**What it is:** The failover pattern provides a backup mechanism when the primary system fails, ensuring continued operation.

**Where it appears:** In `backend/main.py:156-167`, when a PDF has no extractable text (image-based PDF), the system falls back from text extraction to image extraction: `PDFProcessor.extract_images_from_pdf()` converts pages to images, which are then processed through the vision pipeline. Additionally, `docker/entrypoint.sh:69-70` shows that if Redis is unavailable, the application falls back to in-memory LRU caching.

---

## 7. Database / Persistence Layer

### Overview

This application does **not** use a traditional relational database (PostgreSQL, MySQL) or document database (MongoDB). Instead, it uses a **cache-first, stateless** architecture with two persistence mechanisms:

### 7.1 In-Memory LRU Cache

| Property | Value |
|---|---|
| Implementation | `LRUCache` class in `backend/services/performance/cache_manager.py:12` |
| Data structure | `collections.OrderedDict` |
| Capacity | 200 entries (content cache), 100 entries (semantic cache) |
| TTL | 24 hours (content), 168 hours / 7 days (semantic) |
| Thread safety | `threading.RLock()` |
| Key format | SHA-256 hex digest of file content |
| Value format | Python dictionary matching `MenuSchema` structure |

The cache stores the complete extraction result keyed by the SHA-256 hash of the uploaded file's content. This means if the same file is uploaded again (even with a different filename), the cached result is returned instantly.

### 7.2 Redis (Optional External Cache)

| Property | Value |
|---|---|
| Version | Redis 7.2 Alpine |
| Port | 6379 (internal), 6380 (host, dev only) |
| Eviction policy | `allkeys-lru` |
| Max memory | 256MB (dev), 512MB (prod) |
| Persistence | AOF (append-only file) + RDB snapshots |
| Password | Empty in dev, required in prod |

Redis is configured as an optional external cache layer. The `DistributedProcessor` (`backend/services/performance/distributed_processor.py`) uses `redis.asyncio` for distributed task queuing across multiple workers, storing serialized tasks via `pickle`. However, the current route handlers in `main.py` do not actively use Redis — they rely solely on the in-memory LRU cache. Redis is present in the architecture for future scaling.

### 7.3 File System Persistence

| Directory | Purpose |
|---|---|
| `/app/outputs/` (mapped to `./outputs/`) | Stores cropped dish images extracted from menus |
| `/app/logs/` (mapped to `./logs/`) | Application logs (access.log, error.log) |
| `/tmp/` | Temporary file storage during processing (cleaned up after each request) |

### Data Flow Diagram (Persistence)

```
User Uploads File
    │
    ▼
SHA-256 Hash Computed
    │
    ├──► Cache Lookup (LRUCache.get(hash))
    │       │
    │       ├── HIT: Return cached MenuSchema dict
    │       │
    │       └── MISS: Continue processing
    │               │
    │               ▼
    │         AI Processing (Gemini API)
    │               │
    │               ▼
    │         Cache Store (LRUCache.set(hash, data, ttl=24h))
    │               │
    │               ▼
    │         Return ExtractionResponse
    │
    └──► (Future) Redis Distributed Queue
            │
            ├──► LPUSH task to "menu:tasks"
            └──► GET results from "menu:results"
```

### ORM / ODM

No ORM or ODM is used. The application is stateless with respect to business data — it does not persist menu extractions to a database. Each request is processed independently, and results are either returned immediately or cached temporarily.

---

## 8. API & Interface Layer

### REST Endpoints

| Method | Path | Description | Request Body | Response |
|---|---|---|---|---|
| `GET` | `/` | Root endpoint — returns API info and feature list | None | JSON with version, status, features |
| `GET` | `/health` | Health check — returns service status and cache statistics | None | JSON with status, cache stats, service name |
| `GET` | `/cache/stats` | Cache statistics — hit/miss counts and rates | None | JSON with size, max_size, hits, misses, hit_rate |
| `POST` | `/extract-menu` | Single menu extraction | `multipart/form-data`: `file` (required), `priority` (optional) | `ExtractionResponse` JSON |
| `POST` | `/extract-menu-batch` | Batch extraction from multiple files | `multipart/form-data`: `files` (multiple, required) | JSON with `results` array and `total` count |
| `GET` | `/cache/clear` | Clear all in-memory cache entries | None | JSON confirmation message |

### Request Validation

- **File type validation**: Extension-based check in `main.py:106-113`. Only `jpg`, `jpeg`, `png`, `pdf` are accepted.
- **File size validation**: Size check in `main.py:116-124` against `config.MAX_FILE_SIZE` (10MB).
- **Pydantic schema validation**: All response models (`MenuItem`, `MenuSchema`, `ExtractionResponse`) are Pydantic v2 models that automatically validate and serialize data.
- **Nginx-level validation**: `client_max_body_size 15M` in `docker/nginx/nginx.conf:85` provides an additional size gate at the proxy layer.

### Error Handling Conventions

1. **HTTPException for client errors**: `main.py:110,121,164,169,184` raises `HTTPException` with status code 400 for invalid file types, oversized files, and processing failures. FastAPI automatically converts these to JSON error responses.

2. **Graceful error responses for server errors**: `main.py:202-208` catches all unhandled exceptions and returns an `ExtractionResponse` with `success: false` and an error message, rather than returning a raw 500 stack trace.

3. **Service-level error propagation**: `gemini_service.py:71-72` and `pdf_processor.py:44-48` print error messages and re-raise exceptions, allowing the route handler to decide how to respond.

### Authentication & Authorization

**There is no authentication or authorization mechanism in the current codebase.** All endpoints are publicly accessible. The CORS middleware allows all origins (`allow_origins=["*"]`). For production use, authentication (API keys, OAuth, JWT) should be added.

### WebSocket Support

Nginx is configured to proxy WebSocket connections for Streamlit's real-time communication (`docker/nginx/nginx.conf:199-206`). The `/_stcore/stream` endpoint upgrades HTTP to WebSocket with a 24-hour read timeout.

---

## 9. Configuration & Environment Management

### Configuration Sources (Hierarchy)

1. **`.env` file** — Primary source. Copied from `.env.example` and populated with actual values. Loaded by `python-dotenv` in `backend/config.py:5`.

2. **Environment variables** — Override `.env` values. Set in Docker Compose files, Render dashboard, or the host OS.

3. **Docker Compose files** — Define service-level environment variables. The base `docker-compose.yml` sets defaults, while `docker-compose.override.yml` (dev) and `docker-compose.prod.yml` (prod) override them.

4. **`performance_configs.py`** — Pre-set configuration profiles for different deployment scales (dev, prod, enterprise).

5. **Dockerfile ENV directives** — Hardcoded defaults baked into the image (e.g., `APP_ENV=production`, `LOG_LEVEL=info`).

### Key Environment Variables

| Variable | Default | Description | Sensitivity |
|---|---|---|---|
| `GEMINI_API_KEY` | *(required)* | Google Gemini API key | **SECRET** — never commit |
| `APP_ENV` | `production` | `development` or `production` | Low |
| `LOG_LEVEL` | `info` | `debug`, `info`, `warning`, `error` | Low |
| `BACKEND_URL` | `http://backend:8000` | Frontend-to-backend URL (Docker hostname) | Low |
| `MAX_FILE_SIZE` | `10485760` | Max upload size in bytes (10MB) | Low |
| `WEB_CONCURRENCY` | `2` | Gunicorn worker count | Low |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection string | Medium |
| `REDIS_PASSWORD` | *(empty)* | Redis authentication | **SECRET** in production |
| `REDIS_MAX_MEMORY` | `256mb` | Redis memory limit | Low |
| `BACKEND_REPLICAS` | `1` | Number of backend container replicas | Low |

### Secrets Management

- **`.env` is gitignored** (`.gitignore:14`). The `.env.example` template contains placeholder values.
- **No secrets in Docker images**: API keys are injected at runtime via environment variables, not baked into the image.
- **Render.com**: The `render.yaml` marks `GEMINI_API_KEY` with `sync: false`, meaning it must be set manually in the Render dashboard as a secret.
- **Redis password**: Empty in development, required in production via `REDIS_PASSWORD` env var (`docker-compose.prod.yml:96`).

### Configuration Code Location

```python
# backend/config.py — Simple config class
class Config:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    MODEL_NAME = "gemini-2.5-flash"
    OUTPUT_DIR = "outputs"
    MAX_FILE_SIZE = 10 * 1024 * 1024
```

Note: The `config.py` is minimal and does not use Pydantic Settings (which would provide validation and type coercion). The `performance_configs.py` provides richer profiles but is not actively imported by the application code.

---

## 10. Testing Strategy

### Current State: **No Tests Present**

The codebase has **zero test files**. The `tests/` directory referenced in the Makefile (`make test` runs `pytest tests/ -v`) does not exist. The Dockerfile installs `pytest`, `pytest-asyncio`, and `httpx` as development dependencies, indicating that testing was planned but not yet implemented.

### Intended Testing Framework

| Framework | Purpose |
|---|---|
| `pytest` | Unit and integration test runner |
| `pytest-asyncio` | Async test support for FastAPI endpoints |
| `httpx` | Async HTTP client for testing FastAPI routes |

### Recommended Test Structure (Not Yet Implemented)

```
tests/
├── conftest.py              # Shared fixtures (test client, mock Gemini)
├── test_routes.py           # API endpoint tests
├── test_schemas.py          # Pydantic model validation tests
├── test_gemini_service.py   # Gemini API wrapper tests (mocked)
├── test_pdf_processor.py    # PDF extraction tests
├── test_image_pipeline.py   # Image optimization tests
├── test_cache_manager.py    # LRU cache tests
└── test_multilingual.py     # Language detection/translation tests
```

### Mocking Strategy (Recommended)

- **Gemini API**: Mock `genai.GenerativeModel.generate_content()` to return predefined JSON responses, avoiding real API calls and costs during tests.
- **File uploads**: Use `httpx`'s `TestClient` with `files` parameter to simulate multipart uploads.
- **Redis**: Use `fakeredis` for in-memory Redis mocking.
- **File system**: Use `tmp_path` pytest fixture for isolated temporary directories.

### Code Quality Tools

| Tool | Purpose | Makefile Target |
|---|---|---|
| `black` | Auto-formatting | `make format` / `make lint` |
| `isort` | Import sorting | `make format` / `make lint` |
| `flake8` | Linting (style + errors) | `make lint` |

---

## 11. Build, CI/CD & Deployment

### Build Pipeline

The project uses **Docker multi-stage builds** defined in `Dockerfile`:

```
Stage 1: builder (python:3.11-slim)
  ├── Install build deps (gcc, g++, libffi-dev, libssl-dev, pkg-config)
  ├── Create /opt/venv virtual environment
  ├── pip install -r requirements.txt (with BuildKit cache mount)
  └── pip install gunicorn + uvicorn[standard]

Stage 2: runtime (python:3.11-slim)
  ├── Install runtime OS deps (poppler-utils, libmagic1, tesseract-ocr, libgl1)
  ├── Copy /opt/venv from builder stage
  ├── Create non-root user (appuser, UID 1001)
  ├── Copy application code (backend/, frontend/, docker/entrypoint.sh)
  ├── Set HEALTHCHECK (curl /health every 30s)
  └── ENTRYPOINT: ./entrypoint.sh

Stage 3: development (extends runtime)
  ├── Install dev tools (vim, git, httpie)
  ├── Install dev Python packages (pytest, black, isort, flake8, ipython)
  └── Override ENV: APP_ENV=development, LOG_LEVEL=debug
```

### Docker Compose Environments

| Environment | Command | Key Differences |
|---|---|---|
| **Development** | `make up` | Hot-reload, volume mounts, debug logging, single worker, Redis on port 6380 |
| **Production** | `make up-prod` | Gunicorn + uvicorn workers, baked-in code, warning-level logs, Redis with password, Nginx always-on |
| **With Nginx** | `make up-with-nginx` | Development + Nginx reverse proxy on port 80 |

### Container Orchestration

| Component | Technology | Details |
|---|---|---|
| Containerization | Docker multi-stage | Builder → Runtime → Dev stages |
| Orchestration | Docker Compose v2 | 4 services: backend, frontend, redis, nginx |
| Networks | 2 Docker networks | `app-network` (192.168.100.0/24) for internal, `frontend-network` for external |
| Volumes | 3 named volumes | `outputs-data`, `redis-data`, `logs-data` |
| Health checks | Docker HEALTHCHECK | Backend: `/health`, Frontend: `/_stcore/health`, Redis: `redis-cli ping`, Nginx: `/nginx-health` |
| Resource limits | Docker deploy.resources | CPU and memory limits per service (e.g., backend: 1 CPU, 1G RAM in base) |

### Deployment Targets

1. **Local Docker** — `make up` for development, `make deploy` for production.

2. **Render.com** — Defined in `render.yaml` as a Blueprint with two web services (backend + frontend). The backend uses the full Dockerfile, the frontend uses the lightweight `Dockerfile.frontend` (~200MB vs ~3GB). Deployed to the Oregon region on the free tier.

3. **PaaS/Cloud-agnostic** — The Docker images can be deployed to any container platform (AWS ECS, Google Cloud Run, Azure Container Apps, Kubernetes).

### CI/CD Pipeline

**No CI/CD pipeline is defined.** There are no GitHub Actions workflows, GitLab CI configs, or other CI/CD files in the repository. The Makefile provides manual deployment commands (`make deploy`, `make build-prod`, `make up-prod`) but no automated pipeline.

### Entrypoint Script

`docker/entrypoint.sh` is a comprehensive startup script that:
1. Traps SIGTERM/SIGINT/SIGQUIT for graceful shutdown (30-second timeout, then SIGKILL).
2. Waits for Redis to be available (with configurable retries and optional fatal behavior).
3. Runs pre-flight checks (output directory writable, logs directory exists).
4. Dispatches to the correct service based on the CMD argument (`backend`, `backend-dev`, `backend-prod`, `frontend`, `frontend-dev`, `frontend-prod`, `shell`, `test`).

---

## 12. Dependency Map

### Internal Module Dependency Graph

```
backend/main.py
├── backend/config.py
├── backend/models/schemas.py
├── backend/services/gemini_service.py
│   ├── backend/config.py
│   └── backend/models/schemas.py
├── backend/services/pdf_processor.py
│   └── (external: pypdf, pdf2image, Pillow)
├── backend/services/performance/image_pipeline.py
│   └── (external: OpenCV, Pillow, numpy)
├── backend/services/performance/cache_manager.py
│   └── (stdlib: collections, hashlib, threading)
├── backend/services/performance/multilingual_handler.py
│   ├── backend/config.py
│   └── (external: google-generativeai, Pillow)
├── backend/services/performance/async_queue.py
│   └── (stdlib: asyncio, heapq, enum)
├── backend/services/performance/connection_pool.py
│   ├── backend/config.py (imported but missing in file)
│   └── (external: aiohttp)
├── backend/services/performance/distributed_processor.py
│   └── (external: redis.asyncio, pickle)
├── backend/services/performance/load_balancer.py
│   └── (external: psutil)
├── backend/services/performance/streaming_handler.py
│   └── (stdlib: json, asyncio)
└── backend/utils/file_util.py
    └── (external: magic)

frontend/streamlit_app.py
├── (external: streamlit, requests, Pillow)
└── ──HTTP──► backend/main.py (via BACKEND_URL)
```

### Notable External Dependencies

| Dependency | Used By | Why It Matters |
|---|---|---|
| **Google Gemini API** | `gemini_service.py`, `multilingual_handler.py` | Core AI engine — without it, the system cannot extract menu data. All extraction logic depends on this external service. |
| **Redis** | `distributed_processor.py`, Docker Compose | Optional caching and distributed task queue. Currently not actively used by route handlers but present for future scaling. |
| **OpenCV** | `image_pipeline.py` | Image resizing, rotation, and contrast enhancement. Required for the image optimization pipeline. |
| **poppler-utils** | `pdf_processor.py` (via pdf2image) | OS-level dependency for converting PDF pages to images. Without it, image-based PDFs cannot be processed. |
| **python-magic** | `utils/file_util.py` | MIME type detection for robust file validation. Not currently used in route handlers (extension-based validation is used instead). |
| **Gunicorn** | `entrypoint.sh` (production) | Production ASGI server with multi-process workers. Required for production deployments. |
| **aiohttp** | `connection_pool.py` | Async HTTP client for batched Gemini API requests. The connection pool module is not actively used in current route handlers. |
| **psutil** | `load_balancer.py` | System resource monitoring for auto-scaling decisions. The load balancer is a stub and not actively used. |

### Unused / Dead Code Modules

Several modules in `backend/services/performance/` are defined but **not imported or used** by the active route handlers in `main.py`:

- `connection_pool.py` — `GeminiConnectionPool` class is never instantiated.
- `distributed_processor.py` — `DistributedProcessor` class is never instantiated.
- `load_balancer.py` — `LoadBalancer` class is never instantiated.
- `streaming_handler.py` — `StreamingMenuHandler` is defined but the route `/extract-menu-stream` is commented out and uses `app` which is not defined in that file.
- `async_queue.py` — `AsyncPriorityQueue` is instantiated in `main.py:42` but never used in route handlers.
- `utils/file_util.py` — `validate_file_type()` is never called; route handlers use extension-based validation instead.
- `configs/performance_configs.py` — Configuration profiles are never imported by the application.

These appear to be **planned features** that were scaffolded but not yet integrated into the active code path.

---

## 13. Potential Weaknesses & Tech Debt

### 13.1 No Authentication or Authorization

**Severity: High**

All API endpoints are publicly accessible with no authentication. Any client can call `/extract-menu` and consume Gemini API quota, potentially leading to significant costs. The CORS policy allows all origins (`*`), which is a security risk in production.

**Recommendation:** Add API key authentication (e.g., via FastAPI's `Depends` with a header check), implement rate limiting per API key, and restrict CORS to known origins.

### 13.2 Dead Code and Unused Modules

**Severity: Medium**

Approximately 40% of the code in `backend/services/performance/` is not actively used. The `connection_pool.py`, `distributed_processor.py`, `load_balancer.py`, `streaming_handler.py`, and `async_queue.py` modules are defined but never called by route handlers. This creates confusion for new developers who may try to understand or modify code that has no effect.

**Recommendation:** Either integrate these modules into the active code path or remove them. If they are planned for future use, document their intended purpose and add TODO comments.

### 13.3 No Test Coverage

**Severity: High**

There are zero test files in the repository. The Makefile references `make test` which runs `pytest tests/`, but the `tests/` directory does not exist. This means:
- No regression protection when modifying code.
- No way to verify that the AI extraction pipeline works correctly.
- No CI/CD safety net.

**Recommendation:** Implement unit tests for all service classes, integration tests for API endpoints (using `httpx.TestClient`), and mock the Gemini API to avoid real API costs during testing.

### 13.4 Config Class Lacks Validation

**Severity: Medium**

`backend/config.py` uses a simple class with `os.getenv()` calls. There is no validation that required values (like `GEMINI_API_KEY`) are set, no type coercion, and no default fallbacks for most values. If `GEMINI_API_KEY` is missing, the application will fail at runtime with a cryptic error from the Gemini SDK.

**Recommendation:** Use Pydantic Settings (`pydantic.BaseSettings`) for configuration, which provides validation, type coercion, and clear error messages for missing required values.

### 13.5 Temporary File Race Conditions

**Severity: Medium**

In `main.py:142-144`, temporary files are saved to `/tmp/{hash}_{filename}`. In a multi-worker production environment (Gunicorn with multiple uvicorn workers), concurrent requests with the same file hash could overwrite each other's temporary files. The cleanup in the `finally` block could also delete a file that another worker is still using.

**Recommendation:** Use Python's `tempfile.NamedTemporaryFile()` or `tempfile.mkdtemp()` for unique temporary file paths per request.

### 13.6 Gemini API Error Handling Is Fragile

**Severity: Medium**

In `gemini_service.py:67-68`, the JSON response from Gemini is cleaned by splitting on markdown code fences. If Gemini returns malformed JSON (missing brackets, unescaped quotes, or extra text), `json.loads()` will raise an exception that propagates as a 500 error. There is no retry logic, no JSON validation against the schema, and no fallback parsing.

**Recommendation:** Add JSON validation against the Pydantic schema with graceful error handling. Implement retry logic with exponential backoff for API failures. Consider using Gemini's built-in structured output feature (response schema) if available.

### 13.7 Cache Is In-Memory Only (No Redis Integration in Active Path)

**Severity: Medium**

Despite Redis being configured in Docker Compose and the `DistributedProcessor` being defined, the active route handlers in `main.py` only use the in-memory `LRUCache`. This means:
- Cache is lost on container restart.
- Cache is not shared across multiple backend replicas.
- The Redis dependency in Docker Compose is unnecessary for the current code.

**Recommendation:** Either integrate Redis into the active cache path (use Redis as primary cache with in-memory as fallback) or remove Redis from the Docker Compose configuration to simplify the architecture.

### 13.8 Batch Endpoint Calls Single Extraction Sequentially

**Severity: Low**

The `/extract-menu-batch` endpoint in `main.py:219-244` processes files sequentially by calling `extract_menu()` in a loop. For N files, this takes N × (AI processing time). The `AsyncPriorityQueue` that was designed for concurrent processing is not used here.

**Recommendation:** Use `asyncio.gather()` to process batch files concurrently, or enqueue them to the `AsyncPriorityQueue` for prioritized parallel processing.

### 13.9 Hardcoded Paths

**Severity: Low**

`main.py:142` uses a hardcoded `/tmp/` path for temporary files. This works on Linux but may fail on Windows or in restricted container environments.

**Recommendation:** Use `tempfile.gettempdir()` or a configurable temporary directory path.

### 13.10 No API Versioning

**Severity: Low**

The API has no versioning (e.g., `/api/v1/extract-menu`). If the response schema changes in the future, existing clients will break.

**Recommendation:** Add URL-based versioning (`/api/v1/...`) or header-based versioning for future schema evolution.

---

## 14. Glossary

| Term | Definition |
|---|---|
| **ASGI** | Asynchronous Server Gateway Interface — a Python standard for async web servers, used by FastAPI and Uvicorn. |
| **LRU Cache** | Least Recently Used cache — evicts the least recently accessed items when full. |
| **TTL** | Time-To-Live — the duration after which a cached item expires and is removed. |
| **SHA-256** | Secure Hash Algorithm producing a 256-bit (64 hex character) fingerprint of data. Used here to uniquely identify file content. |
| **Pydantic** | A Python library for data validation using Python type annotations. Used for request/response schemas. |
| **Gemini** | Google's multimodal AI model that can understand both text and images. Used here for menu text extraction and translation. |
| **Multimodal** | An AI model that can process multiple types of input (text, images, audio). Gemini is multimodal because it accepts both text prompts and images. |
| **EXIF** | Exchangeable Image File Format — metadata embedded in image files, including orientation, camera settings, and timestamps. |
| **CLAHE** | Contrast Limited Adaptive Histogram Equalization — an image processing technique that improves local contrast, making text more readable. |
| **CORS** | Cross-Origin Resource Sharing — a browser security mechanism that controls which domains can make requests to an API. |
| **Reverse Proxy** | A server that sits in front of backend servers, forwarding client requests. Nginx acts as a reverse proxy here. |
| **WebSocket** | A protocol for full-duplex (two-way) communication over a single TCP connection. Used by Streamlit for real-time UI updates. |
| **Gunicorn** | A production-grade WSGI/ASGI HTTP server for Python, used here to run multiple FastAPI worker processes. |
| **Uvicorn** | An ASGI server implementation using uvloop and httptools. Fast and async-native. |
| **Docker Multi-Stage Build** | A Dockerfile technique that uses multiple `FROM` statements to create a smaller final image by copying only needed artifacts from earlier stages. |
| **Docker Compose Override** | A secondary YAML file that merges with the base `docker-compose.yml`, allowing environment-specific configuration (dev vs prod). |
| **MIME Type** | Multipurpose Internet Mail Extensions — a standard identifier for file types (e.g., `image/jpeg`, `application/pdf`). |
| **AOF** | Append-Only File — a Redis persistence mechanism that logs every write operation. |
| **RDB** | Redis Database — a point-in-time snapshot persistence mechanism for Redis. |
| **ISO 639-1** | A two-letter code standard for language identification (e.g., `en` for English, `zh` for Chinese, `ar` for Arabic). |
| **PaaS** | Platform as a Service — a cloud computing model where the provider manages the infrastructure (e.g., Render.com, Heroku). |
| **SSE** | Server-Sent Events — a technology for pushing real-time updates from server to client over HTTP. |
| **NDJSON** | Newline-Delimited JSON — a format where each line is a valid JSON object, used for streaming data. |
| **EXIF Orientation Tag** | A metadata field (0x0112) in JPEG images that indicates how the image should be rotated for correct display. |
| **BuildKit** | Docker's next-generation build system that supports features like cache mounts and parallel stage building. |
| **Blueprint (Render)** | Render.com's infrastructure-as-code format that defines multiple services and their relationships in a single YAML file. |
| **Poppler** | A PDF rendering library used by `pdf2image` to convert PDF pages to image files. |
| **Heap Queue (heapq)** | Python's priority queue implementation using a binary heap, providing O(log n) insertion and extraction. |
| **RLock** | Reentrant Lock — a threading primitive that allows the same thread to acquire the lock multiple times without deadlocking. |
