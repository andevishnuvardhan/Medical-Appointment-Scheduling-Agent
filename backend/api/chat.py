from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from ..models.schemas import ChatRequest, ChatResponse
from ..agent.scheduling_agent import SchedulingAgent

logger = logging.getLogger(__name__)

router = APIRouter()

# Global agent instance (will be set by main.py)
agent: Optional[SchedulingAgent] = None


def set_agent(scheduling_agent: SchedulingAgent):
    """Set the global agent instance"""
    global agent
    agent = scheduling_agent


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint for conversational interaction

    Args:
        request: Chat request with message and optional conversation_id

    Returns:
        Chat response with agent's message
    """
    if agent is None:
        raise HTTPException(status_code=500, detail="Agent not initialized")

    try:
        logger.info(f"Received chat message: {request.message[:50]}...")

        result = agent.chat(
            message=request.message,
            conversation_id=request.conversation_id
        )

        return ChatResponse(
            message=result["message"],
            conversation_id=result["conversation_id"],
            metadata=result.get("metadata")
        )

    except Exception as e:
        logger.error(f"Error processing chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "agent_initialized": agent is not None}
