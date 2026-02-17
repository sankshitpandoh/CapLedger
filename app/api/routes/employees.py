from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.models import Employee, EmployeeStatus
from app.schemas import EmployeeCreate, EmployeeRead, EmployeeUpdate

router = APIRouter(prefix="/api/employees", tags=["employees"])


@router.post("", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db_session)) -> Employee:
    code_exists = db.scalar(select(func.count()).select_from(Employee).where(Employee.employee_code == payload.employee_code))
    if code_exists:
        raise HTTPException(status_code=409, detail="Employee code already exists")

    email_exists = db.scalar(select(func.count()).select_from(Employee).where(Employee.email == payload.email))
    if email_exists:
        raise HTTPException(status_code=409, detail="Employee email already exists")

    employee = Employee(**payload.model_dump())
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


@router.get("", response_model=list[EmployeeRead])
def list_employees(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status_filter: EmployeeStatus | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db_session),
) -> list[Employee]:
    stmt = select(Employee).order_by(Employee.id.desc()).limit(limit).offset(offset)
    if status_filter is not None:
        stmt = stmt.where(Employee.status == status_filter)
    return list(db.scalars(stmt).all())


@router.get("/{employee_id}", response_model=EmployeeRead)
def get_employee(employee_id: int, db: Session = Depends(get_db_session)) -> Employee:
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


@router.patch("/{employee_id}", response_model=EmployeeRead)
def update_employee(employee_id: int, payload: EmployeeUpdate, db: Session = Depends(get_db_session)) -> Employee:
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")

    data = payload.model_dump(exclude_unset=True)
    if "employee_code" in data:
        code_exists = db.scalar(
            select(func.count()).select_from(Employee).where(
                Employee.employee_code == data["employee_code"], Employee.id != employee_id
            )
        )
        if code_exists:
            raise HTTPException(status_code=409, detail="Employee code already exists")

    if "email" in data:
        email_exists = db.scalar(
            select(func.count()).select_from(Employee).where(Employee.email == data["email"], Employee.id != employee_id)
        )
        if email_exists:
            raise HTTPException(status_code=409, detail="Employee email already exists")

    for key, value in data.items():
        setattr(employee, key, value)

    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


@router.delete("/{employee_id}", response_model=EmployeeRead)
def deactivate_employee(employee_id: int, db: Session = Depends(get_db_session)) -> Employee:
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")

    employee.status = EmployeeStatus.INACTIVE
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee
