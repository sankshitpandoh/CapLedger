from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_employee_record, get_current_user, get_db_session, require_admin
from app.models import Employee, EmployeeStatus, User, UserRole
from app.schemas import EmployeeCreate, EmployeeRead, EmployeeUpdate

router = APIRouter(prefix="/api/employees", tags=["employees"])


@router.post("", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(get_db_session),
    current_admin: User = Depends(require_admin),
) -> Employee:
    if payload.email.strip().lower() == current_admin.email.lower():
        raise HTTPException(status_code=403, detail="Admins cannot create their own employee record")

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
    current_user: User = Depends(get_current_user),
    current_employee: Employee | None = Depends(get_current_employee_record),
) -> list[Employee]:
    if current_user.role == UserRole.EMPLOYEE:
        if current_employee is None:
            return []
        return [current_employee]

    stmt = select(Employee).order_by(Employee.id.desc()).limit(limit).offset(offset)
    if status_filter is not None:
        stmt = stmt.where(Employee.status == status_filter)
    return list(db.scalars(stmt).all())


@router.get("/{employee_id}", response_model=EmployeeRead)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    current_employee: Employee | None = Depends(get_current_employee_record),
) -> Employee:
    if current_user.role == UserRole.EMPLOYEE:
        if current_employee is None or current_employee.id != employee_id:
            raise HTTPException(status_code=403, detail="Not allowed")
        return current_employee

    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


@router.patch("/{employee_id}", response_model=EmployeeRead)
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db_session),
    current_admin: User = Depends(require_admin),
) -> Employee:
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    if employee.email.lower() == current_admin.email.lower():
        raise HTTPException(status_code=403, detail="Admins cannot update their own employee record")

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
def deactivate_employee(
    employee_id: int,
    db: Session = Depends(get_db_session),
    current_admin: User = Depends(require_admin),
) -> Employee:
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    if employee.email.lower() == current_admin.email.lower():
        raise HTTPException(status_code=403, detail="Admins cannot deactivate their own employee record")

    employee.status = EmployeeStatus.INACTIVE
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee
