# backend/main.py - Fixed version

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool
import time
import os
import shutil
from typing import Optional, List, Dict, Any
from backend.models.schemas import ExtractionResponse, MenuSchema
from backend.services.openai_service import OpenAIService
from backend.services.pdf_processor import PDFProcessor
from backend.services.performance.image_pipeline import ImagePipeline
from backend.services.performance.cache_manager import MenuCacheManager
from backend.services.performance.multilingual_handler import MultilingualMenuHandler
from backend.services.performance.async_queue import AsyncPriorityQueue, PrioritizedTask, Priority
from backend.config import config

# Initialize FastAPI app
app = FastAPI(
    title="Menu Extraction System",
    version="2.0.0",
    description="AI-powered menu extraction with performance optimizations"
)

# Enable CORS for Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
ai_service = OpenAIService()
pdf_processor = PDFProcessor()
image_pipeline = ImagePipeline()
cache_manager = MenuCacheManager()
multilingual_handler = MultilingualMenuHandler()
task_queue = AsyncPriorityQueue(max_concurrent=10, rate_limit_per_minute=100)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    print("🚀 Starting Menu Extraction System v2.0")
    print(f"📊 Cache size: {cache_manager.content_cache.max_size}")
    print(f"⚡ Concurrent tasks: {task_queue.max_concurrent}")
    print("✅ All services initialized")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Menu Extraction System API",
        "version": "2.0.0",
        "status": "running",
        "features": [
            "multilingual support",
            "caching",
            "async processing",
            "performance optimizations"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    cache_stats = cache_manager.content_cache.get_stats()
    return {
        "status": "healthy",
        "cache": cache_stats,
        "service": "menu-extraction-system"
    }

@app.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics"""
    return cache_manager.content_cache.get_stats()

@app.post("/extract-menu")
async def extract_menu(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    priority: str = "normal"
):
    """
    Extract structured menu data from uploaded image or PDF file
    """
    start_time = time.time()
    temp_file_path = None
    optimized_path = None

    # Parse priority
    priority_map = {
        "low": Priority.LOW,
        "normal": Priority.NORMAL,
        "high": Priority.HIGH,
        "critical": Priority.CRITICAL
    }
    task_priority = priority_map.get(priority.lower(), Priority.NORMAL)

    try:
        # Validate file type
        allowed_extensions = ['jpg', 'jpeg', 'png', 'pdf']
        file_extension = file.filename.split('.')[-1].lower()

        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
            )

        # Check file size
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)

        if file_size > config.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds {config.MAX_FILE_SIZE // 1024 // 1024}MB limit"
            )

        # Read file content for caching
        file_content = await file.read()
        file_hash = cache_manager.get_file_hash(file_content)

        # Check cache first
        cached_result = cache_manager.get_cached_menu(file_hash)
        if cached_result:
            processing_time = time.time() - start_time
            return ExtractionResponse(
                success=True,
                data=MenuSchema(**cached_result),
                processing_time=processing_time,
                cached=True
            )

        # Save uploaded file temporarily
        temp_file_path = f"/tmp/{file_hash}_{file.filename}"
        with open(temp_file_path, "wb") as buffer:
            buffer.write(file_content)

        # Process based on file type
        menu_data = None

        if file_extension == "pdf":
            # Handle PDF
            try:
                extracted_text = pdf_processor.extract_text_from_pdf(temp_file_path)

                if extracted_text and len(extracted_text.strip()) > 100:
                    menu_data = ai_service.extract_menu_from_text(extracted_text)
                else:
                    # Fallback to image extraction
                    images = pdf_processor.extract_images_from_pdf(temp_file_path)
                    if images:
                        # Optimize first page
                        optimized_first_page = image_pipeline.smart_resize(images[0], target_size_mb=0.5)
                        menu_data = await multilingual_handler.extract_multilingual_menu(optimized_first_page)
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail="Could not extract content from PDF"
                        )
            except ValueError as ve:
                raise HTTPException(status_code=400, detail=str(ve))

        else:  # Image file
            # Optimize image before processing
            try:
                # Auto-orient image
                oriented_path = image_pipeline.auto_orient(temp_file_path)

                # Smart resize
                optimized_path = image_pipeline.smart_resize(oriented_path, target_size_mb=0.5)

                # Extract with multilingual support
                menu_data = await multilingual_handler.extract_multilingual_menu(optimized_path)

            except Exception as img_err:
                raise HTTPException(status_code=400, detail=f"Image processing failed: {str(img_err)}")

        # Cache the result
        if menu_data:
            menu_dict = menu_data.dict() if hasattr(menu_data, 'dict') else menu_data
            cache_manager.cache_menu(file_hash, menu_dict, ttl_hours=24)

        processing_time = time.time() - start_time

        return ExtractionResponse(
            success=True,
            data=menu_data if isinstance(menu_data, MenuSchema) else MenuSchema(**menu_data),
            processing_time=processing_time,
            cached=False
        )

    except HTTPException:
        raise
    except Exception as e:
        processing_time = time.time() - start_time
        return ExtractionResponse(
            success=False,
            error=f"Processing failed: {str(e)}",
            processing_time=processing_time
        )

    finally:
        # Clean up temporary files
        for path in [temp_file_path, optimized_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except:
                    pass

@app.post("/extract-menu-batch")
async def extract_menu_batch(
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Batch extract menu data from multiple files
    """
    results = []
    for file in files:
        try:
            result = await extract_menu(file, background_tasks)
            results.append({
                "filename": file.filename,
                "success": result.success,
                "data": result.data.dict() if result.data else None,
                "error": result.error
            })
        except Exception as e:
            results.append({
                "filename": file.filename,
                "success": False,
                "error": str(e)
            })

    return {"results": results, "total": len(results)}

@app.get("/cache/clear")
async def clear_cache():
    """Clear the cache (admin endpoint)"""
    cache_manager.content_cache.cache.clear()
    cache_manager.content_cache.ttl_map.clear()
    return {"message": "Cache cleared successfully"}