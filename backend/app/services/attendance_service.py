"""Attendance service: check-in/out, history, reports, CSV export.

Late detection uses the user's assigned WorkSchedule.
If no schedule is assigned, a default of 09:00 UTC with 0 grace minutes is applied.
"""

import calendar
import csv
import io
import logging
from datetime import date, datetime, time, timedelta, timezone
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
    DailyReportResponse,
    MonthlyReportResponse,
    PaginatedAttendanceResponse,
)

logger = logging.getLogger(__name__)

# Default check-in deadline when the user has no WorkSchedule assigned
_DEFAULT_START_HOUR = 9   # 09:00 UTC
_DEFAULT_GRACE_MIN = 0


# ---------------------------------------------------------------------------
# Check-in / Check-out
# ---------------------------------------------------------------------------

async def check_in(
    db: AsyncSession, user_id: str, method: str = "FACE"
) -> AttendanceResponse:
    """Record today's check-in for a user.

    Status is 'late' if the check-in time exceeds the schedule's deadline
    (expected_start_time + grace_period_minutes).  late_minutes is the
    number of minutes past that deadline.

    Raises:
        HTTPException 404: User not found.
        HTTPException 409: Already checked in today.
    """
    result = await db.execute(
        select(User)
        .options(joinedload(User.work_schedule))
        .where(User.id == user_id, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    today = date.today()
    existing = await db.execute(
        select(Attendance).where(
            Attendance.user_id == user_id,
            Attendance.date == today,
            Attendance.deleted_at.is_(None),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Check-in already recorded for today",
        )

    now = datetime.now(timezone.utc)
    attendance_status, late_min = _compute_status(now, today, user.work_schedule)

    attendance = Attendance(
        user_id=user_id,
        date=today,
        check_in=now,
        status=attendance_status,
        late_minutes=late_min,
        recognized_by=method.upper(),
    )
    db.add(attendance)
    await db.flush()
    await db.refresh(attendance)

    return _to_response(attendance, user.full_name)


async def check_out(db: AsyncSession, user_id: str) -> AttendanceResponse:
    """Record today's check-out for a user.

    Raises:
        HTTPException 404: No active check-in found for today.
    """
    today = date.today()
    result = await db.execute(
        select(Attendance).where(
            Attendance.user_id == user_id,
            Attendance.date == today,
            Attendance.deleted_at.is_(None),
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
    return _to_response(attendance, user.full_name if user else None)


# ---------------------------------------------------------------------------
# List / detail / update
# ---------------------------------------------------------------------------

async def list_attendance(
    db: AsyncSession,
    user_id: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    status_filter: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
) -> PaginatedAttendanceResponse:
    """Paginated attendance history with optional filters (non-deleted rows only)."""
    query = (
        select(Attendance)
        .options(joinedload(Attendance.user))
        .where(Attendance.deleted_at.is_(None))
    )

    if user_id:
        query = query.where(Attendance.user_id == user_id)
    if date_from:
        query = query.where(Attendance.date >= date_from)
    if date_to:
        query = query.where(Attendance.date <= date_to)
    if status_filter:
        query = query.where(Attendance.status == status_filter.lower())

    query = query.order_by(Attendance.date.desc(), Attendance.check_in.desc().nullslast())

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0

    paged = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(paged)
    records = result.scalars().all()

    return PaginatedAttendanceResponse(
        items=[_to_response(r, r.user.full_name if r.user else None) for r in records],
        total=total,
        page=page,
        limit=limit,
    )


async def get_attendance(db: AsyncSession, attendance_id: str) -> AttendanceResponse:
    """Fetch a single attendance record by UUID.

    Raises:
        HTTPException 404: Not found or soft-deleted.
    """
    result = await db.execute(
        select(Attendance)
        .options(joinedload(Attendance.user))
        .where(Attendance.id == attendance_id, Attendance.deleted_at.is_(None))
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance record not found")
    return _to_response(rec, rec.user.full_name if rec.user else None)


async def update_attendance(
    db: AsyncSession, attendance_id: str, request: AttendanceUpdateRequest
) -> AttendanceResponse:
    """Correct an attendance record (admin only).

    Raises:
        HTTPException 404: Not found.
    """
    result = await db.execute(
        select(Attendance)
        .options(joinedload(Attendance.user))
        .where(Attendance.id == attendance_id, Attendance.deleted_at.is_(None))
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance record not found")

    for field, value in request.model_dump(exclude_unset=True).items():
        if value is not None:
            # Normalise status to lowercase to match the DB ENUM
            if field == "status" and isinstance(value, str):
                value = value.lower()
            setattr(rec, field, value)

    await db.flush()
    await db.refresh(rec)
    return _to_response(rec, rec.user.full_name if rec.user else None)


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

async def daily_report(db: AsyncSession, report_date: date) -> DailyReportResponse:
    """Generate a summary for a single day."""
    users_result = await db.execute(
        select(User).where(User.deleted_at.is_(None))
    )
    all_users = users_result.scalars().all()
    total_users = len(all_users)

    att_result = await db.execute(
        select(Attendance)
        .options(joinedload(Attendance.user))
        .where(Attendance.date == report_date, Attendance.deleted_at.is_(None))
    )
    records = att_result.scalars().all()

    present_names = [r.user.full_name for r in records if r.status == "present" and r.user]
    late_names = [r.user.full_name for r in records if r.status == "late" and r.user]
    absent_count = total_users - len(present_names) - len(late_names)

    return DailyReportResponse(
        date=report_date,
        total_users=total_users,
        present=len(present_names),
        absent=max(0, absent_count),
        late=len(late_names),
        present_list=present_names,
        late_list=late_names,
        absent_list=["(non pointés)"] * max(0, absent_count),
    )


async def monthly_report(db: AsyncSession, year: int, month: int) -> MonthlyReportResponse:
    """Generate per-day stats for an entire month."""
    users_result = await db.execute(select(User).where(User.deleted_at.is_(None)))
    total_users = len(users_result.scalars().all())

    _, last_day = calendar.monthrange(year, month)
    start_date = date(year, month, 1)
    end_date = date(year, month, last_day)

    result = await db.execute(
        select(Attendance).where(
            Attendance.date >= start_date,
            Attendance.date <= end_date,
            Attendance.deleted_at.is_(None),
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
        s = daily_map.get(current_date, {"present": 0, "absent": total_users, "late": 0})
        present_count = s["present"]
        late_count = s["late"]
        day_rate = ((present_count + late_count) / total_users * 100) if total_users > 0 else 0
        total_rate += day_rate
        daily_stats.append({
            "date": current_date.isoformat(),
            "present": present_count,
            "absent": total_users - present_count - late_count,
            "late": late_count,
            "rate": round(day_rate, 2),
        })

    return MonthlyReportResponse(
        year=year,
        month=month,
        total_users=total_users,
        total_days=last_day,
        average_daily_rate=round(total_rate / last_day, 2) if last_day > 0 else 0.0,
        daily_stats=daily_stats,
    )


async def export_csv(db: AsyncSession, month: int, year: int) -> bytes:
    """Export attendance rows for a month as UTF-8 CSV bytes."""
    _, last_day = calendar.monthrange(year, month)
    start_date = date(year, month, 1)
    end_date = date(year, month, last_day)

    result = await db.execute(
        select(Attendance)
        .options(joinedload(Attendance.user))
        .where(
            Attendance.date >= start_date,
            Attendance.date <= end_date,
            Attendance.deleted_at.is_(None),
        )
        .order_by(Attendance.date, Attendance.user_id)
    )
    records = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Nom", "Arrivée", "Départ", "Statut", "Retard (min)", "Méthode"])

    for rec in records:
        writer.writerow([
            rec.date.isoformat(),
            rec.user.full_name if rec.user else "",
            rec.check_in.isoformat() if rec.check_in else "",
            rec.check_out.isoformat() if rec.check_out else "",
            rec.status,
            rec.late_minutes if rec.late_minutes is not None else "",
            rec.recognized_by,
        ])

    return output.getvalue().encode("utf-8-sig")  # UTF-8 BOM for Excel compatibility


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _compute_status(
    now: datetime,
    today: date,
    work_schedule,
) -> tuple[str, Optional[int]]:
    """Return (status, late_minutes) based on the work schedule and current time."""
    if work_schedule:
        # Treat expected_start_time as UTC; add the grace period
        deadline = datetime.combine(today, work_schedule.expected_start_time).replace(
            tzinfo=timezone.utc
        ) + timedelta(minutes=work_schedule.grace_period_minutes)
    else:
        # Fallback: 09:00 UTC, no grace
        deadline = datetime.combine(today, time(_DEFAULT_START_HOUR, 0)).replace(
            tzinfo=timezone.utc
        ) + timedelta(minutes=_DEFAULT_GRACE_MIN)

    if now > deadline:
        late_min = max(1, int((now - deadline).total_seconds() / 60))
        return "late", late_min

    return "present", None


def _to_response(attendance: Attendance, user_name: Optional[str]) -> AttendanceResponse:
    """Map an Attendance ORM row to the response schema."""
    return AttendanceResponse(
        id=attendance.id,
        user_id=attendance.user_id,
        user_name=user_name,
        date=attendance.date,
        check_in=attendance.check_in,
        check_out=attendance.check_out,
        status=attendance.status,
        late_minutes=attendance.late_minutes,
        recognized_by=attendance.recognized_by,
        notes=attendance.notes,
    )
