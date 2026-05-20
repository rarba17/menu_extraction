# backend/services/performance/streaming_handler.py
from fastapi.responses import StreamingResponse
import json
import asyncio
from typing import AsyncGenerator

class StreamingMenuHandler:
    """Stream menu extraction results as they're processed"""

    async def stream_extraction(self, image_path: str) -> AsyncGenerator[str, None]:
        """Stream results chunk by chunk"""

        # Yield start of extraction
        yield json.dumps({"status": "started", "progress": 0}) + "\n"

        # Process with streaming
        async for chunk in self._process_image_streaming(image_path):
            yield json.dumps({"status": "processing", "chunk": chunk}) + "\n"

        # Yield completion
        yield json.dumps({"status": "completed", "progress": 100}) + "\n"

    async def _process_image_streaming(self, image_path: str):
        """Process image in streaming mode"""
        # This would integrate with Gemini's streaming API
        # Simplified example
        yield {"item_name": "Margherita Pizza", "price": "$12.99"}
        await asyncio.sleep(0.1)
        yield {"item_name": "Caesar Salad", "price": "$8.99"}

# In FastAPI endpoint
@app.get("/extract-menu-stream")
async def extract_menu_stream(file: UploadFile):
    handler = StreamingMenuHandler()
    return StreamingResponse(
        handler.stream_extraction(file),
        media_type="application/x-ndjson"
    )