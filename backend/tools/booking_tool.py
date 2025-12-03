from typing import Dict, Optional
import logging
from ..api.calendly_integration import CalendlyMockAPI

logger = logging.getLogger(__name__)


class BookingTool:
    """Tool for booking and managing appointments"""

    def __init__(self, calendly_api: CalendlyMockAPI):
        self.calendly_api = calendly_api

    def create_booking(
        self,
        appointment_type: str,
        date: str,
        start_time: str,
        patient_name: str,
        patient_email: str,
        patient_phone: str,
        reason: str
    ) -> Dict:
        """
        Create a new appointment booking

        Args:
            appointment_type: Type of appointment
            date: Date in format "YYYY-MM-DD"
            start_time: Start time in format "HH:MM"
            patient_name: Patient's full name
            patient_email: Patient's email
            patient_phone: Patient's phone number
            reason: Reason for visit

        Returns:
            Dictionary with booking confirmation or error
        """
        logger.info(f"Creating booking for {patient_name} on {date} at {start_time}")

        patient_info = {
            "name": patient_name,
            "email": patient_email,
            "phone": patient_phone
        }

        try:
            result = self.calendly_api.book_appointment(
                appointment_type=appointment_type,
                date_str=date,
                start_time=start_time,
                patient=patient_info,
                reason=reason
            )

            if result['status'] == 'confirmed':
                logger.info(f"Booking successful: {result['booking_id']}")
            else:
                logger.warning(f"Booking failed: {result.get('details', {}).get('error', 'Unknown error')}")

            return result

        except Exception as e:
            logger.error(f"Error creating booking: {str(e)}")
            return {
                "booking_id": None,
                "status": "failed",
                "confirmation_code": None,
                "details": {"error": str(e)}
            }

    def get_booking_details(self, booking_id: str) -> Optional[Dict]:
        """
        Get details of an existing booking

        Args:
            booking_id: Booking ID

        Returns:
            Booking details or None if not found
        """
        return self.calendly_api.get_booking(booking_id)

    def cancel_booking(self, booking_id: str) -> bool:
        """
        Cancel an existing booking

        Args:
            booking_id: Booking ID

        Returns:
            True if cancellation successful, False otherwise
        """
        logger.info(f"Cancelling booking: {booking_id}")
        return self.calendly_api.cancel_booking(booking_id)

    def validate_booking_info(
        self,
        patient_name: Optional[str],
        patient_email: Optional[str],
        patient_phone: Optional[str],
        reason: Optional[str]
    ) -> Dict:
        """
        Validate booking information completeness

        Args:
            patient_name: Patient's name
            patient_email: Patient's email
            patient_phone: Patient's phone
            reason: Reason for visit

        Returns:
            Dictionary with validation results and missing fields
        """
        missing_fields = []

        if not patient_name:
            missing_fields.append("name")
        if not patient_email:
            missing_fields.append("email")
        if not patient_phone:
            missing_fields.append("phone")
        if not reason:
            missing_fields.append("reason for visit")

        is_valid = len(missing_fields) == 0

        return {
            "is_valid": is_valid,
            "missing_fields": missing_fields
        }
