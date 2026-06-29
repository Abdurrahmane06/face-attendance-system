"""Attendance router: check-in, check-out, history, reports, CSV export.

IMPORTANT — route order: /report/* routes are declared BEFORE /{attendance_id}
so FastAPI does not match the literal string "report" as an attendance UUID.
"""

import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, require_admin
from app.models.user import User
from app.schemas.attendance import (
    AttendanceResponse,
    AttendanceUpdateRequest,
    CheckInRequest,
    CheckOutRequest,
    DailyReportResponse,
    MonthlyReportResponse,
    PaginatedAttendanceResponse,
)
from app.services import attendance_service

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Check-in / Check-out  (POST — no path collision risk)
# ---------------------------------------------------------------------------

@router.post("/check-in", response_model=AttendanceResponse, status_code=201,
             summary="Record today's check-in")
async def check_in(
    request: CheckInRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttendanceResponse:
    """Create today's attendance record.

    Status is 'late' if the check-in time exceeds the user's work schedule deadline.
    Returns 409 if the user already checked in today.
    Omit user_id to check in the currently authenticated user.
    """
    target_id = request.user_id or current_user.id
    return await attendance_service.check_in(db, target_id, request.method)


@router.post("/check-out", response_model=AttendanceResponse,
             summary="Record today's check-out")
async def check_out(
    request: CheckOutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttendanceResponse:
    """Update today's attendance record with a check-out timestamp."""
    return await attendance_service.check_out(db, request.user_id)


# ---------------------------------------------------------------------------
# Reports  — declared BEFORE /{attendance_id} to avoid route shadowing
# ---------------------------------------------------------------------------

@router.get("/report/daily", response_model=DailyReportResponse,
            summary="Daily attendance summary")
async def daily_report(
    report_date: date = Query(default_factory=date.today),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DailyReportResponse:
    """Return present / late / absent counts and name lists for a given date."""
    return await attendance_service.daily_report(db, report_date)


@router.get("/report/monthly", response_model=MonthlyReportResponse,
            summary="Monthly attendance summary")
async def monthly_report(
    year: int = Query(default_factory=lambda: date.today().year),
    month: int = Query(default_factory=lambda: date.today().month, ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MonthlyReportResponse:
    """Return per-day attendance stats for the given year/month."""
    return await attendance_service.monthly_report(db, year, month)


@router.get("/report/export", summary="Export attendance as CSV")
async def export_report(
    month: int = Query(default_factory=lambda: date.today().month, ge=1, le=12),
    year: int = Query(default_factory=lambda: date.today().year),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Download attendance data for a month as a UTF-8 CSV file (Excel-compatible)."""
    csv_data = await attendance_service.export_csv(db, month, year)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=presence_{year}_{month:02d}.csv"
        },
    )


# ---------------------------------------------------------------------------
# List / detail / update  — /{attendance_id} routes come LAST
# ---------------------------------------------------------------------------

@router.get("", response_model=PaginatedAttendanceResponse,
            summary="List attendance records")
async def list_attendance(
    user_id: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    status: Optional[str] = Query(None, description="present | late | absent"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedAttendanceResponse:
    """Paginated list of attendance records with optional filters."""
    return await attendance_service.list_attendance(
        db, user_id, date_from, date_to, status, page, limit
    )


@router.get("/{attendance_id}", response_model=AttendanceResponse,
            summary="Get attendance record by ID")
async def get_attendance(
    attendance_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttendanceResponse:
    """Fetch a single attendance record by UUID."""
    return await attendance_service.get_attendance(db, attendance_id)


@router.put("/{attendance_id}", response_model=AttendanceResponse,
            summary="Correct an attendance record (admin only)")
async def update_attendance(
    attendance_id: str,
    request: AttendanceUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> AttendanceResponse:
    """Admin endpoint to correct check-in/out times, status, or notes."""
    return await attendance_service.update_attendance(db, attendance_id, request)
