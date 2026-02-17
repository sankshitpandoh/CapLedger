from collections.abc import Generator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models import Employee, User, UserRole

settings = get_settings()


def get_db_session() -> Generator[Session, None, None]:
    yield from get_db()


def get_current_user(request: Request, db: Session = Depends(get_db_session)) -> User:
    if not settings.auth_enabled:
        stub = db.scalar(select(User).where(User.role == UserRole.ADMIN).limit(1))
        if stub is not None:
            return stub
        raise HTTPException(status_code=503, detail="Auth disabled but no admin user exists")

    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    user = db.get(User, int(user_id))
    if user is None:
        request.session.clear()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    return user


def get_current_user_optional(request: Request, db: Session = Depends(get_db_session)) -> User | None:
    if not settings.auth_enabled:
        return db.scalar(select(User).where(User.role == UserRole.ADMIN).limit(1))

    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.get(User, int(user_id))


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


def get_current_employee_record(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> Employee | None:
    if current_user.employee_id is not None:
        employee = db.get(Employee, current_user.employee_id)
        if employee is not None:
            return employee

    return db.scalar(select(Employee).where(Employee.email == current_user.email).limit(1))
