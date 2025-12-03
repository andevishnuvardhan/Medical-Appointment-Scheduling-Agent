import json
import logging
from datetime import datetime, timedelta, date, time
from typing import List, Dict, Optional
from pathlib import Path
import uuid
import pytz

logger = logging.getLogger(__name__)


class CalendlyMockAPI:
    """Mock implementation of Calendly API for appointment scheduling"""

    def __init__(self, schedule_path: str = "./data/doctor_schedule.json"):
        """
        Initialize mock Calendly API

        Args:
            schedule_path: Path to doctor schedule JSON file
        """
        self.schedule_path = schedule_path
        self.schedule_data = self._load_schedule()
        self.bookings = self._load_existing_appointments()
        self.timezone = pytz.timezone(self.schedule_data['doctor_info']['timezone'])

        # Appointment type durations (in minutes)
        self.appointment_durations = {
            "consultation": 30,
            "followup": 15,
            "physical": 45,
            "specialist": 60
        }

    def _load_schedule(self) -> Dict:
        """Load doctor schedule from JSON file"""
        logger.info(f"Loading schedule from {self.schedule_path}")
        with open(self.schedule_path, 'r') as f:
            data = json.load(f)
        return data

    def _load_existing_appointments(self) -> List[Dict]:
        """Load existing appointments from schedule"""
        return self.schedule_data.get('existing_appointments', [])

    def _save_booking(self, booking: Dict):
        """Save a new booking to the schedule file"""
        self.bookings.append(booking)
        self.schedule_data['existing_appointments'] = self.bookings

        # Save to file
        with open(self.schedule_path, 'w') as f:
            json.dump(self.schedule_data, f, indent=2)
        logger.info(f"Saved booking: {booking['booking_id']}")

    def _parse_time(self, time_str: str) -> time:
        """Parse time string to time object"""
        return datetime.strptime(time_str, "%H:%M").time()

    def _is_working_day(self, check_date: date) -> bool:
        """Check if a given date is a working day"""
        day_name = check_date.strftime("%A").lower()
        working_hours = self.schedule_data['working_hours'].get(day_name)
        return working_hours is not None

    def _get_working_hours(self, check_date: date) -> Optional[Dict]:
        """Get working hours for a specific date"""
        day_name = check_date.strftime("%A").lower()
        return self.schedule_data['working_hours'].get(day_name)

    def _get_lunch_break(self) -> Dict:
        """Get lunch break times"""
        return self.schedule_data.get('lunch_break', {"start": "12:00", "end": "13:00"})

    def _time_to_minutes(self, t: time) -> int:
        """Convert time to minutes since midnight"""
        return t.hour * 60 + t.minute

    def _minutes_to_time(self, minutes: int) -> time:
        """Convert minutes since midnight to time"""
        hours = minutes // 60
        mins = minutes % 60
        return time(hour=hours, minute=mins)

    def _is_slot_available(
        self,
        check_date: date,
        start_time: time,
        duration: int
    ) -> bool:
        """
        Check if a time slot is available

        Args:
            check_date: Date to check
            start_time: Start time of slot
            duration: Duration in minutes

        Returns:
            True if slot is available, False otherwise
        """
        # Check if it's a working day
        if not self._is_working_day(check_date):
            return False

        # Get working hours
        working_hours = self._get_working_hours(check_date)
        if not working_hours:
            return False

        # Check if slot is within working hours
        work_start = self._parse_time(working_hours['start'])
        work_end = self._parse_time(working_hours['end'])

        slot_start_mins = self._time_to_minutes(start_time)
        slot_end_mins = slot_start_mins + duration

        work_start_mins = self._time_to_minutes(work_start)
        work_end_mins = self._time_to_minutes(work_end)

        if slot_start_mins < work_start_mins or slot_end_mins > work_end_mins:
            return False

        # Check if slot overlaps with lunch break
        lunch_break = self._get_lunch_break()
        lunch_start = self._parse_time(lunch_break['start'])
        lunch_end = self._parse_time(lunch_break['end'])

        lunch_start_mins = self._time_to_minutes(lunch_start)
        lunch_end_mins = self._time_to_minutes(lunch_end)

        # If slot overlaps with lunch, it's not available
        if not (slot_end_mins <= lunch_start_mins or slot_start_mins >= lunch_end_mins):
            return False

        # Check against existing appointments
        date_str = check_date.strftime("%Y-%m-%d")
        for booking in self.bookings:
            if booking['date'] == date_str and booking.get('status') == 'confirmed':
                booking_start = self._parse_time(booking['start_time'])
                booking_end = self._parse_time(booking['end_time'])

                booking_start_mins = self._time_to_minutes(booking_start)
                booking_end_mins = self._time_to_minutes(booking_end)

                # Check for overlap
                if not (slot_end_mins <= booking_start_mins or slot_start_mins >= booking_end_mins):
                    return False

        return True

    def get_availability(
        self,
        date_str: str,
        appointment_type: str = "consultation"
    ) -> Dict:
        """
        Get available time slots for a specific date

        Args:
            date_str: Date string in format "YYYY-MM-DD"
            appointment_type: Type of appointment

        Returns:
            Dictionary with date and available slots
        """
        logger.info(f"Getting availability for {date_str}, type: {appointment_type}")

        try:
            check_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            logger.error(f"Invalid date format: {date_str}")
            return {"date": date_str, "available_slots": []}

        # Check if date is in the past
        today = datetime.now(self.timezone).date()
        if check_date < today:
            logger.warning(f"Date {date_str} is in the past")
            return {"date": date_str, "available_slots": []}

        # Get appointment duration
        duration = self.appointment_durations.get(appointment_type, 30)

        # Get working hours
        working_hours = self._get_working_hours(check_date)
        if not working_hours:
            logger.info(f"{check_date.strftime('%A')} is not a working day")
            return {"date": date_str, "available_slots": []}

        # Generate potential slots
        work_start = self._parse_time(working_hours['start'])
        work_end = self._parse_time(working_hours['end'])

        slot_duration = self.schedule_data.get('slot_duration_minutes', 15)
        buffer_time = self.schedule_data.get('buffer_time_minutes', 5)

        available_slots = []

        current_mins = self._time_to_minutes(work_start)
        end_mins = self._time_to_minutes(work_end)

        while current_mins + duration <= end_mins:
            slot_start = self._minutes_to_time(current_mins)
            slot_end = self._minutes_to_time(current_mins + duration)

            is_available = self._is_slot_available(check_date, slot_start, duration)

            available_slots.append({
                "start_time": slot_start.strftime("%H:%M"),
                "end_time": slot_end.strftime("%H:%M"),
                "available": is_available
            })

            current_mins += slot_duration

        logger.info(f"Found {len([s for s in available_slots if s['available']])} available slots")

        return {
            "date": date_str,
            "available_slots": available_slots
        }

    def get_available_slots_only(
        self,
        date_str: str,
        appointment_type: str = "consultation",
        time_preference: Optional[str] = None
    ) -> List[Dict]:
        """
        Get only available time slots (filtering out booked ones)

        Args:
            date_str: Date string in format "YYYY-MM-DD"
            appointment_type: Type of appointment
            time_preference: Optional time preference ("morning", "afternoon", "evening")

        Returns:
            List of available time slots
        """
        availability = self.get_availability(date_str, appointment_type)
        available_slots = [slot for slot in availability['available_slots'] if slot['available']]

        # Filter by time preference if specified
        if time_preference and available_slots:
            filtered_slots = []
            for slot in available_slots:
                hour = int(slot['start_time'].split(':')[0])

                if time_preference == "morning" and 6 <= hour < 12:
                    filtered_slots.append(slot)
                elif time_preference == "afternoon" and 12 <= hour < 17:
                    filtered_slots.append(slot)
                elif time_preference == "evening" and 17 <= hour < 22:
                    filtered_slots.append(slot)

            return filtered_slots

        return available_slots

    def book_appointment(
        self,
        appointment_type: str,
        date_str: str,
        start_time: str,
        patient: Dict,
        reason: str
    ) -> Dict:
        """
        Book an appointment

        Args:
            appointment_type: Type of appointment
            date_str: Date string in format "YYYY-MM-DD"
            start_time: Start time in format "HH:MM"
            patient: Dictionary with patient information (name, email, phone)
            reason: Reason for visit

        Returns:
            Dictionary with booking confirmation
        """
        logger.info(f"Booking appointment for {patient['name']} on {date_str} at {start_time}")

        try:
            check_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            slot_start = self._parse_time(start_time)
        except ValueError as e:
            logger.error(f"Invalid date/time format: {e}")
            return {
                "booking_id": None,
                "status": "failed",
                "confirmation_code": None,
                "details": {"error": "Invalid date or time format"}
            }

        # Get duration
        duration = self.appointment_durations.get(appointment_type, 30)

        # Check if slot is available
        if not self._is_slot_available(check_date, slot_start, duration):
            logger.warning(f"Slot not available: {date_str} {start_time}")
            return {
                "booking_id": None,
                "status": "failed",
                "confirmation_code": None,
                "details": {"error": "Time slot is not available"}
            }

        # Calculate end time
        end_mins = self._time_to_minutes(slot_start) + duration
        slot_end = self._minutes_to_time(end_mins)

        # Generate booking ID and confirmation code
        booking_id = f"APPT-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
        confirmation_code = str(uuid.uuid4())[:8].upper()

        # Create booking
        booking = {
            "booking_id": booking_id,
            "date": date_str,
            "start_time": start_time,
            "end_time": slot_end.strftime("%H:%M"),
            "type": appointment_type,
            "patient_name": patient['name'],
            "patient_email": patient['email'],
            "patient_phone": patient['phone'],
            "reason": reason,
            "status": "confirmed",
            "confirmation_code": confirmation_code,
            "created_at": datetime.now(self.timezone).isoformat()
        }

        # Save booking
        self._save_booking(booking)

        logger.info(f"Booking confirmed: {booking_id}")

        return {
            "booking_id": booking_id,
            "status": "confirmed",
            "confirmation_code": confirmation_code,
            "details": {
                "date": date_str,
                "start_time": start_time,
                "end_time": slot_end.strftime("%H:%M"),
                "appointment_type": appointment_type,
                "duration": duration,
                "patient": patient,
                "reason": reason
            }
        }

    def get_booking(self, booking_id: str) -> Optional[Dict]:
        """Get booking details by ID"""
        for booking in self.bookings:
            if booking.get('booking_id') == booking_id:
                return booking
        return None

    def cancel_booking(self, booking_id: str) -> bool:
        """Cancel a booking"""
        for booking in self.bookings:
            if booking.get('booking_id') == booking_id:
                booking['status'] = 'cancelled'
                self._save_booking(booking)
                logger.info(f"Cancelled booking: {booking_id}")
                return True
        return False
