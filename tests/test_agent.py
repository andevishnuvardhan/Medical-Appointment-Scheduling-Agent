import pytest
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.agent.scheduling_agent import SchedulingAgent
from backend.rag.faq_rag import FAQRAG
from backend.api.calendly_integration import CalendlyMockAPI
from backend.tools.availability_tool import AvailabilityTool
from backend.tools.booking_tool import BookingTool


@pytest.fixture
def calendly_api():
    """Fixture for Calendly API"""
    return CalendlyMockAPI(schedule_path="./data/doctor_schedule.json")


@pytest.fixture
def availability_tool(calendly_api):
    """Fixture for availability tool"""
    return AvailabilityTool(calendly_api)


@pytest.fixture
def booking_tool(calendly_api):
    """Fixture for booking tool"""
    return BookingTool(calendly_api)


@pytest.fixture
def faq_rag():
    """Fixture for FAQ RAG"""
    return FAQRAG(
        data_path="./data/clinic_info.json",
        vector_store_path="./data/vectordb"
    )


def test_calendly_availability(calendly_api):
    """Test checking availability"""
    result = calendly_api.get_availability(
        date_str="2024-12-10",
        appointment_type="consultation"
    )

    assert result["date"] == "2024-12-10"
    assert "available_slots" in result
    assert isinstance(result["available_slots"], list)


def test_availability_tool(availability_tool):
    """Test availability tool"""
    suggestions = availability_tool.suggest_slots(
        appointment_type="consultation",
        time_preference="morning",
        num_suggestions=3
    )

    assert isinstance(suggestions, list)
    print(f"\nFound {len(suggestions)} suggested slots")
    for slot in suggestions:
        print(f"  - {slot['date']} ({slot['day_name']}) at {slot['start_time']}")


def test_faq_rag(faq_rag):
    """Test FAQ RAG system"""
    # Test querying
    results = faq_rag.query("What insurance do you accept?", n_results=2)

    assert len(results) > 0
    print(f"\nFAQ Query Results:")
    for result in results:
        print(f"  - {result['content'][:100]}...")

    # Test context generation
    context = faq_rag.get_context_for_question("What are your hours?")
    assert len(context) > 0
    print(f"\nContext for 'What are your hours?':\n{context[:200]}...")


def test_booking_validation(booking_tool):
    """Test booking information validation"""
    # Test incomplete info
    validation = booking_tool.validate_booking_info(
        patient_name="John Doe",
        patient_email=None,
        patient_phone=None,
        reason="Checkup"
    )

    assert not validation["is_valid"]
    assert "email" in validation["missing_fields"]
    assert "phone" in validation["missing_fields"]

    # Test complete info
    validation = booking_tool.validate_booking_info(
        patient_name="John Doe",
        patient_email="john@example.com",
        patient_phone="+1-555-0100",
        reason="Checkup"
    )

    assert validation["is_valid"]
    assert len(validation["missing_fields"]) == 0


def test_mock_booking(booking_tool):
    """Test creating a mock booking"""
    result = booking_tool.create_booking(
        appointment_type="consultation",
        date="2024-12-15",
        start_time="10:00",
        patient_name="Test Patient",
        patient_email="test@example.com",
        patient_phone="+1-555-0199",
        reason="Test appointment"
    )

    if result["status"] == "confirmed":
        print(f"\nBooking created successfully!")
        print(f"  Booking ID: {result['booking_id']}")
        print(f"  Confirmation Code: {result['confirmation_code']}")
        assert result["booking_id"] is not None
        assert result["confirmation_code"] is not None
    else:
        print(f"\nBooking failed: {result['details'].get('error')}")


# Example conversation test
def test_example_conversation():
    """Test an example conversation flow"""
    print("\n" + "="*50)
    print("EXAMPLE CONVERSATION FLOW")
    print("="*50)

    conversation_steps = [
        "I need to see the doctor",
        "I've been having headaches",
        "Afternoon would be good, sometime this week",
        "Wednesday at 3:30 PM works for me",
        "John Doe",
        "john.doe@email.com",
        "+1-555-0123"
    ]

    print("\nConversation simulation:")
    for i, message in enumerate(conversation_steps, 1):
        print(f"\n{i}. Patient: {message}")
        print(f"   Agent: [Would respond based on conversation state]")

    print("\n" + "="*50)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
