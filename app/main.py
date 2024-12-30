from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.router import router
import logging
import sys
import os

# Get the absolute path to the log file
log_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app.log')

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

# Create formatters and handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# File handler
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)

# Add handlers to root logger
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

# Create a logger for this module
logger = logging.getLogger(__name__)
logger.info(f"Application starting, logging to {log_file}")

app = FastAPI(
    title="Book Reader API",
    description="API for processing and accessing book content",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Modify this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    """Initialize the database on startup."""
    from .api.router import db
    await db.init_db()
    logger.info("Database initialized")

@app.get("/")
async def root():
    return {
        "message": "Book Reader API",
        "version": "1.0.0",
        "docs_url": "/docs"
    }
