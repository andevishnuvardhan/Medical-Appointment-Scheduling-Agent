# Architecture Diagram and System Design

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          USER INTERFACE                                   │
│                   (HTTP/REST API - Port 8000)                            │
│                                                                          │
│  POST /api/chat                    GET /api/health                       │
│  POST /api/info                                                          │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
                                 │ HTTP Request
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         FASTAPI APPLICATION                               │
│                        (main.py, chat.py)                                │
│                                                                          │
│  • CORS middleware                                                       │
│  • Request validation (Pydantic)                                         │
│  • Error handling                                                        │
│  • Conversation state management                                         │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
                                 │ Process Message
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                      SCHEDULING AGENT                                     │
│                   (scheduling_agent.py)                                  │
│                                                                          │
│  LLM: OpenAI GPT-4 Turbo / Anthropic Claude                             │
│                                                                          │
│  Capabilities:                                                           │
│  • Natural conversation management                                       │
│  • Context switching (FAQ ↔ Scheduling)                                 │
│  • Tool calling orchestration                                            │
│  • Conversation state tracking                                           │
│  • Multi-turn dialogue handling                                          │
│                                                                          │
│  System Prompt:                                                          │
│  • Role: Medical appointment scheduling assistant                        │
│  • Guidelines: Empathetic, clear, professional                          │
│  • Phases: greeting → understanding → suggesting →                       │
│            collecting → confirming → completing                          │
└─────┬────────────────┬─────────────────┬──────────────────┬─────────────┘
      │                │                 │                  │
      │ Tool Calls     │                 │                  │
      │                │                 │                  │
      ▼                ▼                 ▼                  ▼
┌──────────┐    ┌─────────────┐   ┌────────────┐    ┌──────────────┐
│          │    │             │   │            │    │              │
│ FAQ RAG  │    │ Availability│   │  Booking   │    │  Calendly    │
│ System   │    │    Tool     │   │    Tool    │    │  Mock API    │
│          │    │             │   │            │    │              │
└────┬─────┘    └──────┬──────┘   └─────┬──────┘    └──────┬───────┘
     │                 │                 │                  │
     │                 └─────────────────┴──────────────────┘
     │                                   │
     │                                   │
     ▼                                   ▼
┌──────────────────────┐      ┌────────────────────────────┐
│   VECTOR DATABASE    │      │    SCHEDULE DATABASE       │
│     (ChromaDB)       │      │  (doctor_schedule.json)    │
│                      │      │                            │
│  Collections:        │      │  • Working hours           │
│  • clinic_faq        │      │  • Existing appointments   │
│                      │      │  • Lunch breaks            │
│  Storage:            │      │  • Buffer times            │
│  • Clinic info       │      │                            │
│  • Insurance/billing │      │  Format:                   │
│  • Policies          │      │  • JSON persistence        │
│  • FAQs              │      │  • Atomic updates          │
│  • Visit prep        │      │                            │
│                      │      │                            │
│  Embeddings:         │      │                            │
│  • Sentence BERT     │      │                            │
│  • 384 dimensions    │      │                            │
└──────────────────────┘      └────────────────────────────┘
```

## Component Details

### 1. FastAPI Application Layer

**Responsibilities:**
- HTTP request/response handling
- Input validation using Pydantic schemas
- CORS configuration for frontend integration
- Conversation ID management
- Error handling and logging

**Key Files:**
- `backend/main.py`: Application initialization, lifespan management
- `backend/api/chat.py`: Chat endpoint implementation
- `backend/models/schemas.py`: Pydantic models for validation

**Endpoints:**
- `POST /api/chat`: Main conversational interface
- `GET /api/health`: Health check
- `GET /api/info`: System information

### 2. Scheduling Agent (Core Intelligence)

**Responsibilities:**
- Manages multi-turn conversation state
- Decides when to call tools vs respond directly
- Maintains context across conversation phases
- Handles seamless switching between scheduling and FAQ modes
- Generates empathetic, natural responses

**LLM Integration:**
- Supports OpenAI (GPT-4 Turbo) and Anthropic (Claude)
- Function calling for tool orchestration
- Temperature: 0.7 for natural but consistent responses
- System prompt defines role, guidelines, and behavior

**Conversation Phases:**
1. **Greeting**: Welcome patient
2. **Understanding Needs**: Determine appointment type
3. **Slot Recommendation**: Suggest available times
4. **Collecting Info**: Gather patient details
5. **Confirmation**: Verify before booking
6. **Completed**: Provide confirmation

**Tool Calling Flow:**
```
User Message
     │
     ▼
Agent analyzes intent
     │
     ├─→ FAQ question? → call answer_faq()
     │
     ├─→ Need slots? → call suggest_slots()
     │
     ├─→ Check specific date? → call check_availability()
     │
     └─→ Ready to book? → call book_appointment()
     │
     ▼
Tool executes and returns result
     │
     ▼
Agent synthesizes natural language response
     │
     ▼
Response sent to user
```

### 3. FAQ RAG System

**Responsibilities:**
- Semantic search over clinic information
- Accurate answer generation without hallucination
- Context provision to LLM

**Components:**

**a) Vector Store (ChromaDB)**
- Persistent storage at `./data/vectordb`
- Collection: `clinic_faq`
- Automatic embedding generation

**b) Embedding Model**
- Model: `all-MiniLM-L6-v2` (Sentence Transformers)
- Dimension: 384
- Fast inference, good quality for FAQ retrieval

**c) Document Chunks**
Stored with metadata:
- Clinic details (location, hours, parking)
- Insurance information
- Billing policies
- Visit preparation
- Appointment types
- FAQs (question-answer pairs)

**RAG Pipeline:**
```
User Question
     │
     ▼
Embed question (Sentence BERT)
     │
     ▼
Semantic search in ChromaDB (cosine similarity)
     │
     ▼
Retrieve top-k documents (k=3 default)
     │
     ▼
Format as context string
     │
     ▼
Provide to LLM for answer generation
     │
     ▼
Natural language answer
```

### 4. Calendly Mock API

**Responsibilities:**
- Simulate Calendly scheduling functionality
- Manage doctor schedules and availability
- Handle booking, cancellation, rescheduling
- Persist appointments to JSON

**Key Features:**

**Availability Checking:**
1. Load working hours for day of week
2. Generate time slots (15-min intervals)
3. Check against:
   - Working hours boundaries
   - Lunch break (12:00-13:00 PM)
   - Existing appointments
   - Required appointment duration
4. Return available/unavailable status for each slot

**Booking Logic:**
1. Validate date and time format
2. Check slot availability
3. Verify no conflicts
4. Generate booking ID and confirmation code
5. Store appointment
6. Return confirmation

**Conflict Prevention:**
- Checks all existing appointments for overlaps
- Validates slot doesn't overlap with lunch
- Ensures slot is within working hours
- Prevents double-booking

### 5. Tools Layer

**a) Availability Tool**
```python
check_availability(date, appointment_type, time_preference)
  ├─→ Queries Calendly API for specific date
  ├─→ Filters by time preference (morning/afternoon/evening)
  └─→ Returns available slots with metadata

suggest_slots(appointment_type, preferred_date, time_preference, num)
  ├─→ If no preferred_date: searches next 14 days
  ├─→ Finds dates with availability
  ├─→ Returns top N suggestions
  └─→ Includes day name, slot details

find_next_available_dates(appointment_type, days_to_check, max_dates)
  ├─→ Iterates through future dates
  ├─→ Identifies dates with open slots
  └─→ Returns first max_dates with availability
```

**b) Booking Tool**
```python
create_booking(appointment_type, date, time, patient_info, reason)
  ├─→ Validates all required information
  ├─→ Checks slot availability
  ├─→ Creates booking via Calendly API
  └─→ Returns confirmation or error

validate_booking_info(name, email, phone, reason)
  ├─→ Checks completeness of information
  └─→ Returns validation result and missing fields

cancel_booking(booking_id)
  ├─→ Looks up booking
  ├─→ Updates status to 'cancelled'
  └─→ Persists change
```

## Data Flow

### Successful Booking Flow

```
1. User: "I need an appointment"
   │
   ▼
2. Agent: Greets, asks reason for visit
   │
   ▼
3. User: "I have headaches"
   │
   ▼
4. Agent: Determines appointment type → General Consultation
   │    Asks for time preference
   │
   ▼
5. User: "Afternoon this week"
   │
   ▼
6. Agent: Calls suggest_slots(
   │          appointment_type="consultation",
   │          time_preference="afternoon"
   │        )
   │
   ▼
7. Availability Tool: Searches next 14 days for afternoon slots
   │
   ▼
8. Calendly API: Returns available slots
   │
   ▼
9. Agent: Presents 3-5 options to user
   │
   ▼
10. User: Selects "Wednesday 3:30 PM"
    │
    ▼
11. Agent: Collects patient information
    │    (name, email, phone)
    │
    ▼
12. User: Provides information
    │
    ▼
13. Agent: Confirms all details
    │
    ▼
14. User: Confirms
    │
    ▼
15. Agent: Calls book_appointment(...)
    │
    ▼
16. Booking Tool: Validates and creates booking
    │
    ▼
17. Calendly API: Persists appointment, generates confirmation
    │
    ▼
18. Agent: Provides confirmation code and details
```

### FAQ During Scheduling Flow

```
1. User: "I want to schedule"
   │
   ▼
2. Agent: Asks reason for visit
   │
   ▼
3. User: "What insurance do you accept?"
   │
   ▼
4. Agent: Detects FAQ question
   │    Calls answer_faq("What insurance do you accept?")
   │
   ▼
5. FAQ RAG: Embeds question → searches vector DB
   │
   ▼
6. ChromaDB: Returns relevant documents about insurance
   │
   ▼
7. Agent: Generates answer using context
   │
   ▼
8. Agent: Answers question, then returns to scheduling
   │    "Great question! We accept... Now, back to scheduling..."
```

## Context Switching Mechanism

The agent maintains conversation context and seamlessly switches between modes:

**States:**
- `scheduling_mode`: Active booking flow
- `faq_mode`: Answering questions
- `mixed_mode`: Both in same conversation

**Switching Logic:**
```python
if user_message contains question:
    previous_context = save_scheduling_state()
    answer_faq(question)
    restore_context(previous_context)
    prompt_to_continue_scheduling()
else:
    continue_scheduling_flow()
```

**Context Preservation:**
- Conversation history maintained
- Partial booking information stored
- Phase tracking across turns
- Tool call results cached

## Error Handling Paths

### API Failure
```
Calendly API unavailable
     │
     ▼
Booking Tool catches exception
     │
     ▼
Returns error status
     │
     ▼
Agent detects failure
     │
     ▼
Apologizes, offers alternatives
     │
     ▼
"I'm having trouble accessing our scheduling system.
 Would you like to call our office at [phone]?"
```

### No Available Slots
```
User requests specific date
     │
     ▼
check_availability() returns 0 slots
     │
     ▼
Agent acknowledges situation
     │
     ▼
Suggests alternative dates
     │
     ▼
Offers to call office for urgent needs
```

### Invalid Input
```
User provides past date
     │
     ▼
Calendly API validates
     │
     ▼
Returns validation error
     │
     ▼
Agent politely explains
     │
     ▼
"I notice that date has passed.
 Would you like to schedule for tomorrow or later?"
```

## Scalability Considerations

**Current Design:**
- In-memory conversation storage
- JSON file persistence
- Single-instance deployment

**Production Enhancements:**
- Redis for conversation state
- PostgreSQL for appointment storage
- Horizontal scaling with load balancer
- Message queue for async processing
- Caching layer for frequent queries

## Security Considerations

**Current:**
- CORS enabled for all origins (development)
- No authentication/authorization
- API keys in environment variables

**Production Requirements:**
- CORS restricted to known origins
- JWT authentication
- Rate limiting
- Input sanitization
- HIPAA compliance for patient data
- Encrypted data at rest
- Audit logging

## Performance Metrics

**Expected Performance:**
- Chat response time: < 2 seconds (LLM dependent)
- FAQ retrieval: < 100ms
- Availability check: < 50ms
- Booking creation: < 100ms

**Optimization Opportunities:**
- Cache frequent FAQ queries
- Preload embeddings at startup
- Batch availability checks
- Async tool execution

---

This architecture provides a robust, scalable foundation for intelligent medical appointment scheduling with natural conversation and accurate information retrieval.
