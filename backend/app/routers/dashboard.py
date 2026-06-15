"""Dashboard router: aggregated statistics for the main dashboard view.

Provides KPI data, attendance trends, and recent check-ins.
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.dependencies import get_current_user, get_db
from app.models.attendance import Attendance
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get aggregated dashboard statistics.

    Args:
        db: Database session.
        current_user: Authenticated user.

    Returns:
        dict with total_users, present_today, absent_today, late_today,
        attendance_rate_today, attendance_rate_week,
        attendance_last_7_days, and recent_checkins.
    """
    today = date.today()
    week_ago = today - timedelta(days=6)

    total_result = await db.execute(
        select(func.count()).select_from(select(User).where(User.is_active == True).subquery())
    )
    total_users = total_result.scalar() or 0

    today_att_result = await db.execute(
        select(Attendance).where(Attendance.date == today)
    )
    today_records = today_att_result.scalars().all()

    present_today = sum(1 for r in today_records if r.status == "PRESENT")
    late_today = sum(1 for r in today_records if r.status == "LATE")
    absent_today = total_users - present_today - late_today

    rate_today = round(((present_today + late_today) / total_users * 100), 2) if total_users > 0 else 0

    week_att_result = await db.execute(
        select(Attendance).where(Attendance.date >= week_ago, Attendance.date <= today)
    )
    week_records = week_att_result.scalars().all()

    week_dates = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
    last_7_days: List[Dict] = []
    week_total_present = 0

    for d in week_dates:
        day_records = [r for r in week_records if r.date == d]
        present = sum(1 for r in day_records if r.status == "PRESENT")
        late = sum(1 for r in day_records if r.status == "LATE")
        absent = total_users - present - late
        last_7_days.append({
            "date": d.isoformat(),
            "present": present,
            "absent": absent,
            "late": late,
        })
        week_total_present += present + late

    week_total_days = len(week_dates)
    attendance_rate_week = round(
        (week_total_present / (total_users * week_total_days) * 100), 2
    ) if total_users > 0 and week_total_days > 0 else 0

    recent_result = await db.execute(
        select(Attendance)
        .options(joinedload(Attendance.user))
        .where(Attendance.date == today)
        .order_by(Attendance.check_in.desc().nullslast())
        .limit(10)
    )
    recent_records = recent_result.scalars().all()

    recent_checkins: List[Dict] = []
    for rec in recent_records:
        recent_checkins.append({
            "user_name": rec.user.full_name if rec.user else "Unknown",
            "time": rec.check_in.isoformat() if rec.check_in else None,
            "status": rec.status,
        })

    return {
        "total_users": total_users,
        "present_today": present_today,
        "absent_today": absent_today,
        "late_today": late_today,
        "attendance_rate_today": rate_today,
        "attendance_rate_week": attendance_rate_week,
        "attendance_last_7_days": last_7_days,
        "recent_checkins": recent_checkins,
    }
