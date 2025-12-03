# Medical Appointment Scheduling Agent

An intelligent conversational agent that helps patients schedule medical appointments through Calendly integration, with RAG-based FAQ answering and natural conversation flow.

## Features

- **Intelligent Conversation Flow**: Natural, empathetic conversations that guide patients through appointment scheduling
- **Calendly Integration**: Mock implementation of Calendly API for fetching availability and booking appointments
- **RAG-based FAQ System**: Answers questions about clinic information, policies, insurance, and more using retrieval-augmented generation
- **Context Switching**: Seamlessly switches between scheduling and FAQ answering while maintaining conversation context
- **Multiple Appointment Types**: Supports General Consultation (30min), Follow-up (15min), Physical Exam (45min), and Specialist Consultation (60min)
- **Smart Scheduling Logic**: Understands time preferences, date flexibility, and suggests optimal slots
- **Edge Case Handling**: Gracefully handles no available slots, ambiguous requests, API failures, and more

## Architecture

The system consists of the following components:

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Interface                           │
│                     (Chat API/Frontend)                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             v
┌─────────────────────────────────────────────────────────────────┐
│                     Scheduling Agent                             │
│                  (LLM: OpenAI/Anthropic)                         │
│                                                                  │
│  • Natural conversation management                               │
│  • Context switching (FAQ ↔ Scheduling)                         │
│  • Tool calling orchestration                                    │
└─────┬──────────────┬──────────────┬─────────────────────────────┘
      │              │              │
      v              v              v
┌──────────┐  ┌───────────┐  ┌────────────────┐
│   FAQ    │  │Calendly   │  │   Booking      │
│   RAG    │  │Mock API   │  │    Tool        │
│          │  │           │  │                │
│ ChromaDB │  │Available  │  │  Validation    │
│ Vector   │  │Slots      │  │  & Booking     │
│ Store    │  │           │  │                │
└──────────┘  └───────────┘  └────────────────┘
```

### Component Details:

1. **Scheduling Agent**: Main conversational agent powered by LLM (OpenAI GPT-4 or Anthropic Claude)
   - Manages conversation state and flow
   - Calls appropriate tools based on user intent
   - Seamlessly switches between scheduling and FAQ contexts

2. **FAQ RAG System**: Retrieval-Augmented Generation for clinic information
   - Vector database (ChromaDB) stores clinic information, policies, and FAQs
   - Sentence transformers for semantic search
   - Provides accurate, contextual answers without hallucination

3. **Calendly Mock API**: Mock implementation of Calendly scheduling
   - Manages doctor schedules and working hours
   - Checks slot availability with conflict detection
   - Books appointments with confirmation codes

4. **Tools**: Specialized functions for the agent
   - `AvailabilityTool`: Check availability, suggest slots based on preferences
   - `BookingTool`: Create bookings, validate information, manage appointments

## Tech Stack

- **Backend**: FastAPI (Python 3.10+)
- **LLM**: OpenAI GPT-4 Turbo or Anthropic Claude (configurable)
- **Vector Database**: ChromaDB for FAQ storage and retrieval
- **Embeddings**: Sentence Transformers (all-MiniLM-L6-v2)
- **Calendar API**: Mock Calendly implementation
- **Data Processing**: Python-dateutil, Pytz for timezone handling

## Setup Instructions

### Prerequisites

- Python 3.10 or higher
- OpenAI API key OR Anthropic API key
- Git (for cloning the repository)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd appointment-scheduling-agent
```

2. **Create and activate virtual environment**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Edit `.env` file:

```env
# For OpenAI (default)
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo
OPENAI_API_KEY=your_openai_api_key_here

# OR for Anthropic Claude
# LLM_PROVIDER=anthropic
# LLM_MODEL=claude-3-5-sonnet-20241022
# ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Clinic Configuration
CLINIC_NAME=HealthCare Plus Clinic
CLINIC_PHONE=+1-555-123-4567
TIMEZONE=America/New_York

# Application
BACKEND_PORT=8000
```

5. **Run the application**
```bash
# From project root
python -m uvicorn backend.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

6. **Access the API documentation**

Open your browser and navigate to:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Testing

Run the test suite:

```bash
pytest tests/test_agent.py -v
```

## Usage

### Chat API

Send a POST request to `/api/chat`:

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I need to schedule an appointment",
    "conversation_id": null
  }'
```

Response:
```json
{
  "message": "I'd be happy to help you schedule an appointment! What brings you in today?",
  "conversation_id": "abc123...",
  "metadata": {
    "phase": "understanding_needs",
    "message_count": 2
  }
}
```

Continue the conversation by including the `conversation_id`:

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I have been having headaches",
    "conversation_id": "abc123..."
  }'
```

## System Design

### Agent Conversation Flow

The agent follows a structured conversation flow with intelligent phase management:

1. **Greeting**: Welcome the patient
2. **Understanding Needs**: Determine reason for visit and appointment type
3. **Slot Recommendation**: Suggest available slots based on preferences
4. **Collecting Information**: Gather patient details (name, email, phone, reason)
5. **Confirmation**: Verify all details before booking
6. **Completed**: Provide confirmation and follow-up information

The agent can seamlessly switch to **FAQ mode** at any point when the patient asks questions about the clinic.

### Calendly Integration Approach

**Mock Implementation** (current):
- Loads doctor schedule from `data/doctor_schedule.json`
- Simulates availability checking with:
  - Working hours validation
  - Lunch break handling
  - Existing appointment conflict detection
  - Appointment type duration matching
- Persists bookings to JSON file
- Generates booking IDs and confirmation codes

**Real Calendly API** (optional):
To use real Calendly API, implement these endpoints in `calendly_integration.py`:
- `GET /event_types` - Get appointment types
- `GET /event_types/{uuid}/available_times` - Get availability
- `POST /scheduled_events` - Create booking

### RAG Pipeline for FAQs

The RAG system uses a three-stage process:

1. **Data Ingestion**:
   - Loads clinic information from `data/clinic_info.json`
   - Chunks information into semantic units (location, insurance, policies, FAQs, etc.)
   - Generates embeddings using Sentence Transformers

2. **Vector Storage**:
   - Stores embeddings in ChromaDB with metadata
   - Persists to disk for fast startup

3. **Retrieval**:
   - User question is embedded using the same model
   - Semantic search finds top-k relevant documents
   - Context is provided to LLM for accurate answer generation

### Tool Calling Strategy

The agent uses function calling to interact with tools:

1. **LLM decides which tool to call** based on conversation context
2. **Tool executes** and returns structured data
3. **LLM synthesizes result** into natural language response
4. **Context is maintained** throughout the conversation

Available tools:
- `check_availability(date, appointment_type, time_preference)` - Check specific date
- `suggest_slots(appointment_type, preferred_date, time_preference, num_suggestions)` - Get suggestions
- `book_appointment(...)` - Create booking (requires explicit confirmation)
- `answer_faq(question)` - Search knowledge base

## Scheduling Logic

### How Available Slots are Determined

1. **Working Hours Check**: Verify date falls on working day with defined hours
2. **Business Hours**: Slots must be within clinic operating hours
3. **Lunch Break**: Exclude lunch break period (12:00-13:00 PM by default)
4. **Existing Appointments**: Check for conflicts with booked appointments
5. **Buffer Time**: Account for buffer time between appointments (5 min default)
6. **Duration Matching**: Ensure slot duration matches appointment type

### Appointment Type Handling

Different appointment types have different durations:
- **General Consultation**: 30 minutes
- **Follow-up**: 15 minutes
- **Physical Exam**: 45 minutes
- **Specialist Consultation**: 60 minutes

The system automatically:
- Finds contiguous available time matching the required duration
- Prevents double-booking
- Suggests appropriate appointment types based on patient's reason for visit

### Conflict Prevention

- Checks all existing appointments for time overlap
- Validates slot is not in the past
- Ensures slot doesn't overlap with lunch or non-working hours
- Atomic booking operation prevents race conditions

## Example Conversations

### Successful Booking

```
User: I need to see the doctor
Agent: I'd be happy to help you schedule an appointment! What's the main reason for your visit today?

User: I've been having headaches
Agent: I understand. For persistent headaches, I'd recommend a general consultation (30 minutes) where the doctor can assess your symptoms. When would you like to come in? Do you have a preference for morning or afternoon appointments?

User: Afternoon if possible, sometime this week
Agent: Let me check our afternoon availability this week. I have these options:
- Tomorrow (Dec 4) at 2:00 PM
- Wednesday (Dec 5) at 3:30 PM
- Thursday (Dec 6) at 1:00 PM
- Friday (Dec 7) at 2:30 PM

Which works best for you?

User: Wednesday at 3:30
Agent: Excellent! Wednesday, December 5th at 3:30 PM for a 30-minute consultation. Before I confirm, I'll need a few details:
- Your full name?

User: John Doe
Agent: Thank you, John. And your best phone number to reach you?

User: 555-0123
Agent: Great. And finally, your email address for confirmation?

User: john@email.com
Agent: Perfect! Let me confirm the details:

Appointment Details:
- Type: General Consultation (30 minutes)
- Date: Wednesday, December 5, 2024
- Time: 3:30 PM - 4:00 PM

Patient Information:
- Name: John Doe
- Phone: 555-0123
- Email: john@email.com
- Reason: Headaches

Is everything correct? Can I go ahead and book this for you?

User: Yes, that's correct
Agent: All set! Your appointment is confirmed for Wednesday, December 5th at 3:30 PM.

Confirmation Code: ABC12345
Booking ID: APPT-20241205-XYZ789

You'll receive a confirmation email at john@email.com. Please arrive 10 minutes early to allow time for check-in. Remember, we require 24-hour notice for cancellations.

Is there anything else you'd like to know about your visit?
```

### FAQ During Booking

```
User: I want to book an appointment
Agent: I'd be happy to help! What brings you in today?

User: Actually, first - what insurance do you accept?
Agent: Great question! We accept most major insurance providers including Blue Cross Blue Shield, Aetna, Cigna, UnitedHealthcare, and Medicare. We also accept self-pay patients. Do you have insurance with one of these providers?

User: Yes, I have Blue Cross. Okay, I'd like to schedule a checkup
Agent: Perfect, we accept Blue Cross Blue Shield. Now for your checkup - would this be your first visit with us, or are you an existing patient?

[Continues with scheduling...]
```

### No Available Slots

```
User: Can I see the doctor today?
Agent: I understand you'd like to be seen today. Unfortunately, we don't have any available appointments for today. However, I have several options for tomorrow:
- 9:00 AM
- 11:30 AM
- 2:00 PM

Would any of these work? If you need urgent care, I can also provide information about our walk-in clinic hours.
```

## Edge Cases Covered

1. **No Available Slots**: Offer alternative dates, suggest calling office
2. **Ambiguous Time References**: Clarify "tomorrow morning" → specific time
3. **Invalid Input**: Past dates, non-existent dates, outside business hours
4. **User Changes Mind**: Graceful mid-booking restart
5. **API Failures**: Graceful degradation with helpful error messages
6. **Incomplete Information**: Prompt for missing details
7. **Context Switching**: FAQ questions during scheduling flow

## Evaluation Focus Areas

The system is optimized for:

1. **Conversational Quality** (30%): Natural, empathetic dialogue with appropriate questions
2. **RAG Quality** (30%): Accurate FAQ retrieval without hallucination
3. **Scheduling Intelligence** (25%): Smart slot recommendations and preference understanding
4. **Edge Case Handling** (15%): Robust handling of various failure scenarios

## Project Structure

```
appointment-scheduling-agent/
├── README.md
├── .env.example
├── requirements.txt
├── backend/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── scheduling_agent.py # Main conversational agent
│   │   └── prompts.py          # System prompts and templates
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── faq_rag.py          # RAG system implementation
│   │   ├── embeddings.py       # Embedding model
│   │   └── vector_store.py     # ChromaDB wrapper
│   ├── api/
│   │   ├── __init__.py
│   │   ├── chat.py             # Chat endpoint
│   │   └── calendly_integration.py  # Mock Calendly API
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── availability_tool.py     # Availability checking
│   │   └── booking_tool.py          # Booking management
│   └── models/
│       ├── __init__.py
│       └── schemas.py          # Pydantic models
├── data/
│   ├── clinic_info.json        # Clinic information and FAQs
│   └── doctor_schedule.json    # Doctor schedule and appointments
└── tests/
    └── test_agent.py           # Test suite
```

## Contributing

Contributions are welcome! Please ensure:
- Code follows PEP 8 style guidelines
- All tests pass
- New features include tests
- Documentation is updated

## License

[Your License Here]

## Acknowledgments

Built for the Lyzr Assessment as an intelligent medical appointment scheduling solution.

## Contact

For questions or support, contact: [Your Contact Information]
