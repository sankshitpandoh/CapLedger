from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_db_session
from app.core.config import get_settings
from app.models import Employee, EmployeeStatus, Grant
from app.schemas import DashboardSummary
from app.services.vesting import summarize_grant

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])
settings = get_settings()


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    as_of: date | None = Query(default=None),
    db: Session = Depends(get_db_session),
) -> DashboardSummary:
    effective_date = as_of or date.today()

    grants = db.scalars(
        select(Grant)
        .options(selectinload(Grant.employee), selectinload(Grant.exercises))
        .order_by(Grant.id.desc())
    ).all()

    grant_summaries = [summarize_grant(grant, effective_date) for grant in grants]

    active_employees = db.scalar(
        select(func.count()).select_from(Employee).where(Employee.status == EmployeeStatus.ACTIVE)
    )
    total_employees = db.scalar(select(func.count()).select_from(Employee))

    pool_allocated = sum(grant.total_options for grant in grants)
    pool_remaining = max(settings.esop_pool_size - pool_allocated, 0)

    vested_options = sum(item.vested_options for item in grant_summaries)
    unvested_options = sum(item.unvested_options for item in grant_summaries)
    exercised_options = sum(item.exercised_options for item in grant_summaries)

    return DashboardSummary(
        as_of=effective_date,
        total_employees=total_employees or 0,
        active_employees=active_employees or 0,
        total_grants=len(grants),
        pool_size=settings.esop_pool_size,
        pool_allocated=pool_allocated,
        pool_remaining=pool_remaining,
        vested_options=vested_options,
        unvested_options=unvested_options,
        exercised_options=exercised_options,
        grant_summaries=grant_summaries,
    )
