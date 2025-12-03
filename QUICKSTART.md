# Quick Start Guide

Get the Medical Appointment Scheduling Agent running in 5 minutes!

## Prerequisites

- Python 3.10+
- OpenAI API key (or Anthropic API key)

## Installation Steps

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file:

```bash
# Copy example
cp .env.example .env
```

Edit `.env` and add your API key:

```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo
OPENAI_API_KEY=sk-your-api-key-here
```

### 3. Run the Server

```bash
python -m uvicorn backend.main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Starting up Medical Appointment Scheduling Agent...
INFO:     Application startup complete!
```

### 4. Test the API

Open another terminal and test:

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, I need to schedule an appointment"}'
```

## Example Conversation via API

### 1. Start Conversation

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "I need to see a doctor for headaches"}'
```

Response:
```json
{
  "message": "I understand you've been experiencing headaches. I'd recommend a general consultation (30 minutes) where the doctor can assess your symptoms. When would you like to come in? Do you have a preference for morning or afternoon appointments?",
  "conversation_id": "abc123-...",
  "metadata": {...}
}
```

### 2. Continue Conversation

Use the `conversation_id` from the previous response:

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Afternoon would be best",
    "conversation_id": "abc123-..."
  }'
```

### 3. Select Time Slot

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Wednesday at 3:30 PM works for me",
    "conversation_id": "abc123-..."
  }'
```

### 4. Provide Information

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "My name is John Doe, email john@example.com, phone 555-0123",
    "conversation_id": "abc123-..."
  }'
```

### 5. Confirm Booking

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Yes, please book it",
    "conversation_id": "abc123-..."
  }'
```

## Testing FAQ System

Ask about clinic information:

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "What insurance do you accept?"}'
```

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "What are your hours?"}'
```

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "What should I bring to my appointment?"}'
```

## View API Documentation

Open your browser:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Run Tests

```bash
pytest tests/test_agent.py -v -s
```

## Common Issues

### Issue: "Agent not initialized"

**Solution:** Ensure your API key is correctly set in `.env`

### Issue: "Module not found"

**Solution:** Run from project root directory and ensure all dependencies are installed

### Issue: "ChromaDB error"

**Solution:** Delete `data/vectordb` folder and restart - it will rebuild automatically

### Issue: Vector database taking too long to initialize

**Solution:** First run initializes the vector DB. Subsequent runs are much faster.

## Next Steps

1. **Customize Clinic Data**: Edit `data/clinic_info.json` with your clinic's information
2. **Modify Schedule**: Update `data/doctor_schedule.json` with actual working hours
3. **Change LLM Provider**: Switch to Anthropic Claude by updating `.env`:
   ```env
   LLM_PROVIDER=anthropic
   LLM_MODEL=claude-3-5-sonnet-20241022
   ANTHROPIC_API_KEY=your-key-here
   ```
4. **Integrate Real Calendly**: Implement real Calendly API in `calendly_integration.py`

## Production Deployment

For production deployment, consider:

1. **Security**: Add authentication, HTTPS, rate limiting
2. **Database**: Replace JSON with PostgreSQL
3. **Caching**: Add Redis for conversation state
4. **Monitoring**: Add logging, metrics, alerts
5. **Scaling**: Deploy behind load balancer with multiple instances

## Support

For issues or questions, refer to:
- Full README: `README.md`
- Architecture docs: `ARCHITECTURE.md`
- Test examples: `tests/test_agent.py`

Happy scheduling! 🏥
