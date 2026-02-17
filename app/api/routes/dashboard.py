from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_employee_record, get_current_user, get_db_session
from app.core.config import get_settings
from app.models import Employee, EmployeeStatus, Grant, User, UserRole
from app.schemas import DashboardSummary
from app.services.vesting import summarize_grant

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])
settings = get_settings()


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    as_of: date | None = Query(default=None),
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    current_employee: Employee | None = Depends(get_current_employee_record),
) -> DashboardSummary:
    effective_date = as_of or date.today()

    stmt = select(Grant).options(selectinload(Grant.employee), selectinload(Grant.exercises)).order_by(Grant.id.desc())
    if current_user.role == UserRole.EMPLOYEE:
        if current_employee is None:
            grants = []
        else:
            grants = db.scalars(stmt.where(Grant.employee_id == current_employee.id)).all()
    else:
        grants = db.scalars(stmt).all()

    grant_summaries = [summarize_grant(grant, effective_date) for grant in grants]

    if current_user.role == UserRole.EMPLOYEE:
        active_employees = 1 if current_employee and current_employee.status == EmployeeStatus.ACTIVE else 0
        total_employees = 1 if current_employee else 0
        pool_allocated = 0
        pool_remaining = 0
        pool_size = 0
    else:
        active_employees = db.scalar(
            select(func.count()).select_from(Employee).where(Employee.status == EmployeeStatus.ACTIVE)
        )
        total_employees = db.scalar(select(func.count()).select_from(Employee))
        pool_allocated = sum(grant.total_options for grant in grants)
        pool_remaining = max(settings.esop_pool_size - pool_allocated, 0)
        pool_size = settings.esop_pool_size

    vested_options = sum(item.vested_options for item in grant_summaries)
    unvested_options = sum(item.unvested_options for item in grant_summaries)
    exercised_options = sum(item.exercised_options for item in grant_summaries)

    return DashboardSummary(
        as_of=effective_date,
        total_employees=total_employees or 0,
        active_employees=active_employees or 0,
        total_grants=len(grants),
        pool_size=pool_size,
        pool_allocated=pool_allocated,
        pool_remaining=pool_remaining,
        vested_options=vested_options,
        unvested_options=unvested_options,
        exercised_options=exercised_options,
        grant_summaries=grant_summaries,
    )
