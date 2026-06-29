"""Attendance request/response schemas."""

from datetime import date, datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class CheckInRequest(BaseModel):
    """Check-in request body.

    Attributes:
        user_id: User UUID for manual check-in (optional if face recognition used).
        method: Recognition method (FACE or MANUAL).
    """

    user_id: Optional[str] = None
    method: str = Field(default="FACE")


class CheckOutRequest(BaseModel):
    """Check-out request body.

    Attributes:
        user_id: User UUID checking out.
    """

    user_id: str


class AttendanceResponse(BaseModel):
    """Attendance record response.

    Attributes:
        id: Attendance UUID.
        user_id: User UUID.
        user_name: User display name.
        date: Attendance date.
        check_in: Check-in timestamp.
        check_out: Check-out timestamp.
        status: Attendance status.
        recognized_by: Recognition method.
        notes: Optional notes.
    """

    id: str
    user_id: str
    user_name: Optional[str] = None
    date: date
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    status: str
    late_minutes: Optional[int] = None
    recognized_by: str
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class PaginatedAttendanceResponse(BaseModel):
    """Paginated list of attendance records.

    Attributes:
        items: List of attendance records.
        total: Total record count.
        page: Current page.
        limit: Items per page.
    """

    items: List[AttendanceResponse]
    total: int
    page: int
    limit: int


class AttendanceUpdateRequest(BaseModel):
    """Attendance correction request (admin only).

    Attributes:
        check_in: Updated check-in time.
        check_out: Updated check-out time.
        status: Updated status.
        notes: Updated notes.
    """

    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class DailyReportResponse(BaseModel):
    """Daily attendance report.

    Attributes:
        date: Report date.
        total_users: Total registered users.
        present: Number of present users.
        absent: Number of absent users.
        late: Number of late users.
        present_list: List of present user names.
        late_list: List of late user names.
        absent_list: List of absent user names.
    """

    date: date
    total_users: int
    present: int
    absent: int
    late: int
    present_list: List[str]
    late_list: List[str]
    absent_list: List[str]


class MonthlyReportResponse(BaseModel):
    """Monthly attendance report.

    Attributes:
        year: Report year.
        month: Report month.
        total_users: Total registered users.
        total_days: Total working days.
        average_daily_rate: Average attendance rate.
        daily_stats: List of daily report summaries.
    """

    year: int
    month: int
    total_users: int
    total_days: int
    average_daily_rate: float
    daily_stats: List[Dict]
