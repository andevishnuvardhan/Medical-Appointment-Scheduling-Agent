from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
from ..api.calendly_integration import CalendlyMockAPI

logger = logging.getLogger(__name__)


class AvailabilityTool:
    """Tool for checking appointment availability"""

    def __init__(self, calendly_api: CalendlyMockAPI):
        self.calendly_api = calendly_api

    def check_availability(
        self,
        date_str: str,
        appointment_type: str = "consultation",
        time_preference: Optional[str] = None
    ) -> Dict:
        """
        Check availability for a specific date

        Args:
            date_str: Date string in format "YYYY-MM-DD"
            appointment_type: Type of appointment
            time_preference: Optional time preference ("morning", "afternoon", "evening")

        Returns:
            Dictionary with availability information
        """
        logger.info(f"Checking availability for {date_str}")

        available_slots = self.calendly_api.get_available_slots_only(
            date_str=date_str,
            appointment_type=appointment_type,
            time_preference=time_preference
        )

        return {
            "date": date_str,
            "appointment_type": appointment_type,
            "time_preference": time_preference,
            "available_slots": available_slots,
            "slots_count": len(available_slots)
        }

    def find_next_available_dates(
        self,
        appointment_type: str = "consultation",
        days_to_check: int = 14,
        max_dates: int = 5,
        time_preference: Optional[str] = None
    ) -> List[Dict]:
        """
        Find next available dates with open slots

        Args:
            appointment_type: Type of appointment
            days_to_check: Number of days to look ahead
            max_dates: Maximum number of dates to return
            time_preference: Optional time preference

        Returns:
            List of dates with available slots
        """
        logger.info(f"Finding next available dates for {appointment_type}")

        today = datetime.now().date()
        available_dates = []

        for i in range(1, days_to_check + 1):
            check_date = today + timedelta(days=i)
            date_str = check_date.strftime("%Y-%m-%d")

            result = self.check_availability(
                date_str=date_str,
                appointment_type=appointment_type,
                time_preference=time_preference
            )

            if result['slots_count'] > 0:
                available_dates.append({
                    "date": date_str,
                    "day_name": check_date.strftime("%A"),
                    "available_slots": result['available_slots'][:5],  # Limit to first 5 slots
                    "total_slots": result['slots_count']
                })

                if len(available_dates) >= max_dates:
                    break

        return available_dates

    def suggest_slots(
        self,
        preferred_date: Optional[str] = None,
        appointment_type: str = "consultation",
        time_preference: Optional[str] = None,
        num_suggestions: int = 5
    ) -> List[Dict]:
        """
        Suggest available time slots based on preferences

        Args:
            preferred_date: Preferred date (if None, finds next available dates)
            appointment_type: Type of appointment
            time_preference: Time of day preference
            num_suggestions: Number of suggestions to return

        Returns:
            List of suggested time slots
        """
        suggestions = []

        if preferred_date:
            # Check specific date
            result = self.check_availability(
                date_str=preferred_date,
                appointment_type=appointment_type,
                time_preference=time_preference
            )

            if result['slots_count'] > 0:
                for slot in result['available_slots'][:num_suggestions]:
                    suggestions.append({
                        "date": preferred_date,
                        "start_time": slot['start_time'],
                        "end_time": slot['end_time'],
                        "day_name": datetime.strptime(preferred_date, "%Y-%m-%d").strftime("%A")
                    })
        else:
            # Find next available dates
            available_dates = self.find_next_available_dates(
                appointment_type=appointment_type,
                days_to_check=14,
                max_dates=5,
                time_preference=time_preference
            )

            # Collect suggestions from available dates
            for date_info in available_dates:
                for slot in date_info['available_slots']:
                    if len(suggestions) >= num_suggestions:
                        break

                    suggestions.append({
                        "date": date_info['date'],
                        "start_time": slot['start_time'],
                        "end_time": slot['end_time'],
                        "day_name": date_info['day_name']
                    })

                if len(suggestions) >= num_suggestions:
                    break

        return suggestions
