from datetime import date, datetime, timezone
from enum import Enum

from sqlalchemy import Date, DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EmployeeStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    joining_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[EmployeeStatus] = mapped_column(
        SQLEnum(EmployeeStatus), default=EmployeeStatus.ACTIVE, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    grants: Mapped[list["Grant"]] = relationship(back_populates="employee", cascade="all, delete-orphan")


class Grant(Base):
    __tablename__ = "grants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False, index=True)
    grant_name: Mapped[str] = mapped_column(String(120), nullable=False)
    grant_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_options: Mapped[int] = mapped_column(Integer, nullable=False)
    strike_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    vesting_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    cliff_months: Mapped[int] = mapped_column(Integer, default=12, nullable=False)
    vesting_months: Mapped[int] = mapped_column(Integer, default=48, nullable=False)
    vesting_frequency_months: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    employee: Mapped[Employee] = relationship(back_populates="grants")
    exercises: Mapped[list["Exercise"]] = relationship(back_populates="grant", cascade="all, delete-orphan")


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    grant_id: Mapped[int] = mapped_column(ForeignKey("grants.id"), nullable=False, index=True)
    exercise_date: Mapped[date] = mapped_column(Date, nullable=False)
    options_exercised: Mapped[int] = mapped_column(Integer, nullable=False)
    price_per_option_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    grant: Mapped[Grant] = relationship(back_populates="exercises")
