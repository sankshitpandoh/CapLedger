from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_db_session
from app.core.config import get_settings
from app.models import Employee, EmployeeStatus, Exercise, Grant
from app.schemas import ExerciseCreate, ExerciseRead, GrantCreate, GrantRead, GrantUpdate, GrantVestingSummary
from app.services.vesting import summarize_grant, vested_options_for_grant

router = APIRouter(prefix="/api/grants", tags=["grants"])
settings = get_settings()


def _validate_vesting_config(cliff_months: int, vesting_months: int, vesting_frequency_months: int) -> None:
    if cliff_months > vesting_months:
        raise HTTPException(status_code=400, detail="cliff_months cannot exceed vesting_months")
    if vesting_months % vesting_frequency_months != 0:
        raise HTTPException(status_code=400, detail="vesting_months must be divisible by vesting_frequency_months")
    if cliff_months % vesting_frequency_months != 0:
        raise HTTPException(status_code=400, detail="cliff_months must be divisible by vesting_frequency_months")


@router.post("", response_model=GrantRead, status_code=status.HTTP_201_CREATED)
def create_grant(payload: GrantCreate, db: Session = Depends(get_db_session)) -> Grant:
    employee = db.get(Employee, payload.employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    if employee.status != EmployeeStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Cannot assign grants to inactive employees")

    allocated = db.scalar(select(func.coalesce(func.sum(Grant.total_options), 0)).select_from(Grant)) or 0
    if allocated + payload.total_options > settings.esop_pool_size:
        raise HTTPException(status_code=400, detail="Grant exceeds available ESOP pool")

    grant = Grant(**payload.model_dump())
    db.add(grant)
    db.commit()
    db.refresh(grant)
    return grant


@router.get("", response_model=list[GrantRead])
def list_grants(
    employee_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db_session),
) -> list[Grant]:
    stmt = select(Grant).order_by(Grant.id.desc()).limit(limit).offset(offset)
    if employee_id is not None:
        stmt = stmt.where(Grant.employee_id == employee_id)
    return list(db.scalars(stmt).all())


@router.get("/{grant_id}", response_model=GrantRead)
def get_grant(grant_id: int, db: Session = Depends(get_db_session)) -> Grant:
    grant = db.get(Grant, grant_id)
    if grant is None:
        raise HTTPException(status_code=404, detail="Grant not found")
    return grant


@router.patch("/{grant_id}", response_model=GrantRead)
def update_grant(grant_id: int, payload: GrantUpdate, db: Session = Depends(get_db_session)) -> Grant:
    grant = db.get(Grant, grant_id)
    if grant is None:
        raise HTTPException(status_code=404, detail="Grant not found")

    data = payload.model_dump(exclude_unset=True)
    cliff_months = data.get("cliff_months", grant.cliff_months)
    vesting_months = data.get("vesting_months", grant.vesting_months)
    vesting_frequency_months = data.get("vesting_frequency_months", grant.vesting_frequency_months)
    _validate_vesting_config(cliff_months, vesting_months, vesting_frequency_months)

    if "total_options" in data:
        exercised = db.scalar(
            select(func.coalesce(func.sum(Exercise.options_exercised), 0)).where(Exercise.grant_id == grant_id)
        )
        if data["total_options"] < (exercised or 0):
            raise HTTPException(status_code=400, detail="total_options cannot be lower than exercised options")

        allocated_other_grants = (
            db.scalar(select(func.coalesce(func.sum(Grant.total_options), 0)).where(Grant.id != grant_id)) or 0
        )
        if allocated_other_grants + data["total_options"] > settings.esop_pool_size:
            raise HTTPException(status_code=400, detail="Updated grant exceeds available ESOP pool")

    for key, value in data.items():
        setattr(grant, key, value)

    db.add(grant)
    db.commit()
    db.refresh(grant)
    return grant


@router.post("/{grant_id}/exercises", response_model=ExerciseRead, status_code=status.HTTP_201_CREATED)
def record_exercise(
    grant_id: int,
    payload: ExerciseCreate,
    db: Session = Depends(get_db_session),
) -> Exercise:
    grant = db.scalar(
        select(Grant)
        .options(selectinload(Grant.employee), selectinload(Grant.exercises))
        .where(Grant.id == grant_id)
    )
    if grant is None:
        raise HTTPException(status_code=404, detail="Grant not found")

    exercised_until_date = sum(ex.options_exercised for ex in grant.exercises if ex.exercise_date <= payload.exercise_date)
    vested_on_date = vested_options_for_grant(grant, payload.exercise_date)

    if exercised_until_date + payload.options_exercised > vested_on_date:
        raise HTTPException(status_code=400, detail="Exercise exceeds vested options on the selected date")

    total_exercised_after = sum(ex.options_exercised for ex in grant.exercises) + payload.options_exercised
    if total_exercised_after > grant.total_options:
        raise HTTPException(status_code=400, detail="Exercise exceeds total grant options")

    price_per_option = payload.price_per_option_cents
    if price_per_option is None:
        price_per_option = grant.strike_price_cents

    exercise = Exercise(
        grant_id=grant_id,
        exercise_date=payload.exercise_date,
        options_exercised=payload.options_exercised,
        price_per_option_cents=price_per_option,
    )
    db.add(exercise)
    db.commit()
    db.refresh(exercise)
    return exercise


@router.get("/{grant_id}/summary", response_model=GrantVestingSummary)
def grant_summary(
    grant_id: int,
    as_of: date | None = Query(default=None),
    db: Session = Depends(get_db_session),
) -> GrantVestingSummary:
    grant = db.scalar(
        select(Grant)
        .options(selectinload(Grant.employee), selectinload(Grant.exercises))
        .where(Grant.id == grant_id)
    )
    if grant is None:
        raise HTTPException(status_code=404, detail="Grant not found")

    effective_date = as_of or date.today()
    return summarize_grant(grant, effective_date)


@router.get("/{grant_id}/exercises", response_model=list[ExerciseRead])
def list_exercises(grant_id: int, db: Session = Depends(get_db_session)) -> list[Exercise]:
    grant_exists = db.scalar(select(func.count()).select_from(Grant).where(Grant.id == grant_id))
    if not grant_exists:
        raise HTTPException(status_code=404, detail="Grant not found")

    exercises = db.scalars(select(Exercise).where(Exercise.grant_id == grant_id).order_by(Exercise.exercise_date.asc())).all()
    return list(exercises)
