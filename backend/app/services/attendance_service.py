"""Attendance service: check-in/out, history, reports.

Manages daily attendance records with duplicate detection,
status calculation, and report generation.
"""

import csv
import io
import logging
from datetime import date, datetime, timezone
from typing import Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.attendance import Attendance
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

logger = logging.getLogger(__name__)


async def check_in(
    db: AsyncSession, user_id: str, method: str = "FACE"
) -> AttendanceResponse:
    """Record a check-in for a user today.

    Args:
        db: Database session.
        user_id: User UUID.
        method: Recognition method (FACE or MANUAL).

    Returns:
        AttendanceResponse with created record.

    Raises:
        HTTPException 404: If user not found.
        HTTPException 409: If check-in already exists for today.
    """
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    today = date.today()
    existing = await db.execute(
        select(Attendance).where(
            Attendance.user_id == user_id, Attendance.date == today
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Check-in already recorded for today",
        )

    now = datetime.now(timezone.utc)
    is_late = now.hour >= 9

    attendance = Attendance(
        user_id=user_id,
        date=today,
        check_in=now,
        status="LATE" if is_late else "PRESENT",
        recognized_by=method.upper(),
    )
    db.add(attendance)
    await db.flush()
    await db.refresh(attendance)

    return AttendanceResponse(
        id=attendance.id,
        user_id=attendance.user_id,
        user_name=user.full_name,
        date=attendance.date,
        check_in=attendance.check_in,
        check_out=attendance.check_out,
        status=attendance.status,
        recognized_by=attendance.recognized_by,
        notes=attendance.notes,
    )


async def check_out(
    db: AsyncSession, user_id: str
) -> AttendanceResponse:
    """Record a check-out for a user today.

    Args:
        db: Database session.
        user_id: User UUID.

    Returns:
        AttendanceResponse with updated record.

    Raises:
        HTTPException 404: If no check-in found for today.
    """
    today = date.today()
    result = await db.execute(
        select(Attendance).where(
            Attendance.user_id == user_id, Attendance.date == today
        )
    )
    attendance = result.scalar_one_or_none()
    if not attendance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No check-in found for today",
        )

    attendance.check_out = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(attendance)

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    return AttendanceResponse(
        id=attendance.id,
        user_id=attendance.user_id,
        user_name=user.full_name if user else None,
        date=attendance.date,
        check_in=attendance.check_in,
        check_out=attendance.check_out,
        status=attendance.status,
        recognized_by=attendance.recognized_by,
        notes=attendance.notes,
    )


async def list_attendance(
    db: AsyncSession,
    user_id: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    status_filter: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
) -> PaginatedAttendanceResponse:
    """List attendance records with optional filters and pagination.

    Args:
        db: Database session.
        user_id: Filter by user.
        date_from: Start date filter.
        date_to: End date filter.
        status_filter: Status filter (PRESENT, ABSENT, LATE).
        page: Page number.
        limit: Items per page.

    Returns:
        PaginatedAttendanceResponse.
    """
    query = select(Attendance).options(joinedload(Attendance.user))

    if user_id:
        query = query.where(Attendance.user_id == user_id)
    if date_from:
        query = query.where(Attendance.date >= date_from)
    if date_to:
        query = query.where(Attendance.date <= date_to)
    if status_filter:
        query = query.where(Attendance.status == status_filter.upper())

    query = query.order_by(Attendance.date.desc(), Attendance.check_in.desc().nullslast())

    total_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = total_result.scalar() or 0

    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    records = result.scalars().all()

    items = []
    for rec in records:
        items.append(
            AttendanceResponse(
                id=rec.id,
                user_id=rec.user_id,
                user_name=rec.user.full_name if rec.user else None,
                date=rec.date,
                check_in=rec.check_in,
                check_out=rec.check_out,
                status=rec.status,
                recognized_by=rec.recognized_by,
                notes=rec.notes,
            )
        )

    return PaginatedAttendanceResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
    )


async def get_attendance(db: AsyncSession, attendance_id: str) -> AttendanceResponse:
    """Get a single attendance record by ID.

    Args:
        db: Database session.
        attendance_id: Attendance UUID.

    Returns:
        AttendanceResponse.

    Raises:
        HTTPException 404: If not found.
    """
    result = await db.execute(
        select(Attendance)
        .options(joinedload(Attendance.user))
        .where(Attendance.id == attendance_id)
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance record not found",
        )

    return AttendanceResponse(
        id=rec.id,
        user_id=rec.user_id,
        user_name=rec.user.full_name if rec.user else None,
        date=rec.date,
        check_in=rec.check_in,
        check_out=rec.check_out,
        status=rec.status,
        recognized_by=rec.recognized_by,
        notes=rec.notes,
    )


async def update_attendance(
    db: AsyncSession, attendance_id: str, request: AttendanceUpdateRequest
) -> AttendanceResponse:
    """Update an attendance record (admin only).

    Args:
        db: Database session.
        attendance_id: Attendance UUID.
        request: Fields to update.

    Returns:
        Updated AttendanceResponse.

    Raises:
        HTTPException 404: If not found.
    """
    result = await db.execute(
        select(Attendance)
        .options(joinedload(Attendance.user))
        .where(Attendance.id == attendance_id)
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance record not found",
        )

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(rec, field, value)

    await db.flush()
    await db.refresh(rec)

    return AttendanceResponse(
        id=rec.id,
        user_id=rec.user_id,
        user_name=rec.user.full_name if rec.user else None,
        date=rec.date,
        check_in=rec.check_in,
        check_out=rec.check_out,
        status=rec.status,
        recognized_by=rec.recognized_by,
        notes=rec.notes,
    )


async def daily_report(db: AsyncSession, report_date: date) -> DailyReportResponse:
    """Generate a daily attendance report.

    Args:
        db: Database session.
        report_date: Target date.

    Returns:
        DailyReportResponse with stats.
    """
    users_result = await db.execute(select(User).where(User.is_active == True))
    total_users = len(users_result.scalars().all())

    att_result = await db.execute(
        select(Attendance).where(Attendance.date == report_date)
    )
    records = att_result.scalars().all()

    present = [r for r in records if r.status == "PRESENT"]
    late = [r for r in records if r.status == "LATE"]
    absent = [r for r in records if r.status == "ABSENT"]

    present_names = []
    late_names = []
    for rec in present:
        user = await db.get(User, rec.user_id)
        present_names.append(user.full_name if user else "Unknown")
    for rec in late:
        user = await db.get(User, rec.user_id)
        late_names.append(user.full_name if user else "Unknown")

    absent_count = total_users - len(present) - len(late)
    absent_names = ["(non pointés)"] * absent_count

    return DailyReportResponse(
        date=report_date,
        total_users=total_users,
        present=len(present),
        absent=absent_count,
        late=len(late),
        present_list=present_names,
        late_list=late_names,
        absent_list=absent_names,
    )


async def monthly_report(
    db: AsyncSession, year: int, month: int
) -> MonthlyReportResponse:
    """Generate a monthly attendance report.

    Args:
        db: Database session.
        year: Report year.
        month: Report month (1-12).

    Returns:
        MonthlyReportResponse with aggregated stats.
    """
    import calendar

    users_result = await db.execute(select(User).where(User.is_active == True))
    total_users = len(users_result.scalars().all())

    _, last_day = calendar.monthrange(year, month)
    start_date = date(year, month, 1)
    end_date = date(year, month, last_day)

    result = await db.execute(
        select(Attendance).where(
            Attendance.date >= start_date, Attendance.date <= end_date
        )
    )
    records = result.scalars().all()

    daily_map: Dict[date, Dict[str, int]] = {}
    for rec in records:
        if rec.date not in daily_map:
            daily_map[rec.date] = {"present": 0, "absent": 0, "late": 0}
        if rec.status in daily_map[rec.date]:
            daily_map[rec.date][rec.status] += 1

    daily_stats = []
    total_rate = 0.0
    for d in range(1, last_day + 1):
        current_date = date(year, month, d)
        stats = daily_map.get(current_date, {"present": 0, "absent": total_users, "late": 0})
        present_count = stats["present"]
        late_count = stats["late"]
        day_rate = ((present_count + late_count) / total_users * 100) if total_users > 0 else 0
        total_rate += day_rate
        daily_stats.append({
            "date": current_date.isoformat(),
            "present": present_count,
            "absent": total_users - present_count - late_count,
            "late": late_count,
            "rate": round(day_rate, 2),
        })

    avg_rate = round(total_rate / last_day, 2) if last_day > 0 else 0

    return MonthlyReportResponse(
        year=year,
        month=month,
        total_users=total_users,
        total_days=last_day,
        average_daily_rate=avg_rate,
        daily_stats=daily_stats,
    )


async def export_csv(
    db: AsyncSession, month: int, year: int
) -> bytes:
    """Export attendance records as CSV.

    Args:
        db: Database session.
        month: Month number.
        year: Year.

    Returns:
        CSV file content as bytes.
    """
    import calendar
    start_date = date(year, month, 1)
    _, last_day = calendar.monthrange(year, month)
    end_date = date(year, month, last_day)

    result = await db.execute(
        select(Attendance)
        .options(joinedload(Attendance.user))
        .where(Attendance.date >= start_date, Attendance.date <= end_date)
        .order_by(Attendance.date, Attendance.user_id)
    )
    records = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "User ID", "User Name", "Check In", "Check Out", "Status", "Method"])

    for rec in records:
        writer.writerow([
            rec.date.isoformat(),
            rec.user_id,
            rec.user.full_name if rec.user else "",
            rec.check_in.isoformat() if rec.check_in else "",
            rec.check_out.isoformat() if rec.check_out else "",
            rec.status,
            rec.recognized_by,
        ])

    return output.getvalue().encode("utf-8")
