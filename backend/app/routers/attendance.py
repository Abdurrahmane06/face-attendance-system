"""Attendance router: check-in, check-out, history, reports.

Check-in/out require authentication. Updates and corrections require ADMIN role.
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


@router.post("/check-in", response_model=AttendanceResponse, status_code=201)
async def check_in(
    request: CheckInRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttendanceResponse:
    """Record a check-in for the authenticated user or a specified user.

    Args:
        request: Check-in details (optional user_id for manual).
        db: Database session.
        current_user: Authenticated user.

    Returns:
        AttendanceResponse for the created record.
    """
    user_id = request.user_id if request.user_id else current_user.id
    return await attendance_service.check_in(db, user_id, request.method)


@router.post("/check-out", response_model=AttendanceResponse)
async def check_out(
    request: CheckOutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttendanceResponse:
    """Record a check-out for a user today.

    Args:
        request: Check-out details (user_id).
        db: Database session.
        current_user: Authenticated user.

    Returns:
        Updated AttendanceResponse.
    """
    return await attendance_service.check_out(db, request.user_id)


@router.get("", response_model=PaginatedAttendanceResponse)
async def list_attendance(
    user_id: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedAttendanceResponse:
    """List attendance records with optional filters.

    Args:
        user_id: Filter by user.
        date_from: Start date.
        date_to: End date.
        status: Filter by status.
        page: Page number.
        limit: Items per page.
        db: Database session.
        current_user: Authenticated user.

    Returns:
        PaginatedAttendanceResponse.
    """
    return await attendance_service.list_attendance(
        db, user_id, date_from, date_to, status, page, limit
    )


@router.get("/{attendance_id}", response_model=AttendanceResponse)
async def get_attendance(
    attendance_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttendanceResponse:
    """Get a single attendance record by ID.

    Args:
        attendance_id: Attendance UUID.
        db: Database session.
        current_user: Authenticated user.

    Returns:
        AttendanceResponse.
    """
    return await attendance_service.get_attendance(db, attendance_id)


@router.put("/{attendance_id}", response_model=AttendanceResponse)
async def update_attendance(
    attendance_id: str,
    request: AttendanceUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> AttendanceResponse:
    """Update an attendance record (admin only).

    Args:
        attendance_id: Attendance UUID.
        request: Fields to update.
        db: Database session.
        admin: Authenticated admin user.

    Returns:
        Updated AttendanceResponse.
    """
    return await attendance_service.update_attendance(db, attendance_id, request)


@router.get("/report/daily", response_model=DailyReportResponse)
async def daily_report(
    report_date: date = Query(default_factory=date.today),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DailyReportResponse:
    """Get daily attendance report.

    Args:
        report_date: Target date (default: today).
        db: Database session.
        current_user: Authenticated user.

    Returns:
        DailyReportResponse.
    """
    return await attendance_service.daily_report(db, report_date)


@router.get("/report/monthly", response_model=MonthlyReportResponse)
async def monthly_report(
    year: int = Query(default_factory=lambda: date.today().year),
    month: int = Query(default_factory=lambda: date.today().month),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MonthlyReportResponse:
    """Get monthly attendance report.

    Args:
        year: Report year.
        month: Report month (1-12).
        db: Database session.
        current_user: Authenticated user.

    Returns:
        MonthlyReportResponse.
    """
    return await attendance_service.monthly_report(db, year, month)


@router.get("/report/export")
async def export_report(
    month: int = Query(default_factory=lambda: date.today().month),
    year: int = Query(default_factory=lambda: date.today().year),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Export attendance data as CSV.

    Args:
        month: Month number.
        year: Year.
        db: Database session.
        current_user: Authenticated user.

    Returns:
        CSV file response.
    """
    csv_data = await attendance_service.export_csv(db, month, year)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=attendance_{year}_{month:02d}.csv"
        },
    )
