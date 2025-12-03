from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Literal
from datetime import datetime, date, time


class PatientInfo(BaseModel):
    name: str
    email: EmailStr
    phone: str
    reason: Optional[str] = None


class TimeSlot(BaseModel):
    start_time: str
    end_time: str
    available: bool


class AvailabilityResponse(BaseModel):
    date: str
    available_slots: List[TimeSlot]


class BookingRequest(BaseModel):
    appointment_type: Literal["consultation", "followup", "physical", "specialist"]
    date: str
    start_time: str
    patient: PatientInfo
    reason: str


class BookingResponse(BaseModel):
    booking_id: str
    status: Literal["confirmed", "pending", "failed"]
    confirmation_code: str
    details: dict


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: Optional[datetime] = Field(default_factory=datetime.now)


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    message: str
    conversation_id: str
    metadata: Optional[dict] = None


class ConversationState(BaseModel):
    conversation_id: str
    phase: Literal["greeting", "understanding_needs", "slot_recommendation", "collecting_info", "confirmation", "faq", "completed"]
    appointment_type: Optional[str] = None
    preferred_date: Optional[str] = None
    preferred_time_of_day: Optional[Literal["morning", "afternoon", "evening", "any"]] = None
    selected_slot: Optional[dict] = None
    patient_info: Optional[PatientInfo] = None
    suggested_slots: List[dict] = []
    messages: List[ChatMessage] = []
