import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from .agent.scheduling_agent import SchedulingAgent
from .rag.faq_rag import FAQRAG
from .api.calendly_integration import CalendlyMockAPI
from .tools.availability_tool import AvailabilityTool
from .tools.booking_tool import BookingTool
from .api import chat

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    # Startup
    logger.info("Starting up Medical Appointment Scheduling Agent...")

    # Initialize components
    logger.info("Initializing components...")

    # Calendly API
    calendly_api = CalendlyMockAPI(
        schedule_path=os.getenv("SCHEDULE_PATH", "./data/doctor_schedule.json")
    )

    # Tools
    availability_tool = AvailabilityTool(calendly_api)
    booking_tool = BookingTool(calendly_api)

    # FAQ RAG
    faq_rag = FAQRAG(
        data_path=os.getenv("CLINIC_DATA_PATH", "./data/clinic_info.json"),
        vector_store_path=os.getenv("VECTOR_DB_PATH", "./data/vectordb")
    )

    # Scheduling Agent
    llm_provider = os.getenv("LLM_PROVIDER", "openai")
    llm_model = os.getenv("LLM_MODEL", "gpt-4-turbo")

    if llm_provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
    elif llm_provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
    else:
        raise ValueError(f"Unsupported LLM provider: {llm_provider}")

    agent = SchedulingAgent(
        llm_provider=llm_provider,
        llm_model=llm_model,
        api_key=api_key,
        faq_rag=faq_rag,
        availability_tool=availability_tool,
        booking_tool=booking_tool
    )

    # Set agent in chat router
    chat.set_agent(agent)

    logger.info("Application startup complete!")

    yield

    # Shutdown
    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Medical Appointment Scheduling Agent",
    description="Intelligent conversational agent for medical appointment scheduling with RAG-based FAQ answering",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api", tags=["chat"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Medical Appointment Scheduling Agent API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/api/info")
async def info():
    """Get system information"""
    return {
        "clinic_name": os.getenv("CLINIC_NAME", "HealthCare Plus Clinic"),
        "clinic_phone": os.getenv("CLINIC_PHONE", "+1-555-123-4567"),
        "llm_provider": os.getenv("LLM_PROVIDER", "openai"),
        "llm_model": os.getenv("LLM_MODEL", "gpt-4-turbo"),
        "timezone": os.getenv("TIMEZONE", "America/New_York")
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("BACKEND_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
