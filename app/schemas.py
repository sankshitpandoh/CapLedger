from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import EmployeeStatus, UserRole


class EmployeeBase(BaseModel):
    employee_code: str = Field(min_length=2, max_length=50)
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    joining_date: date
    status: EmployeeStatus = EmployeeStatus.ACTIVE

    @model_validator(mode="after")
    def validate_email(self) -> "EmployeeBase":
        if "@" not in self.email or self.email.startswith("@") or self.email.endswith("@"):
            raise ValueError("Invalid email format")
        return self


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    employee_code: str | None = Field(default=None, min_length=2, max_length=50)
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    email: str | None = Field(default=None, min_length=5, max_length=255)
    joining_date: date | None = None
    status: EmployeeStatus | None = None

    @model_validator(mode="after")
    def validate_email(self) -> "EmployeeUpdate":
        if self.email is not None and ("@" not in self.email or self.email.startswith("@") or self.email.endswith("@")):
            raise ValueError("Invalid email format")
        return self


class EmployeeRead(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class GrantBase(BaseModel):
    employee_id: int
    grant_name: str = Field(min_length=2, max_length=120)
    grant_date: date
    total_options: int = Field(gt=0)
    strike_price_cents: int = Field(ge=0)
    vesting_start_date: date
    cliff_months: int = Field(default=12, ge=0, le=120)
    vesting_months: int = Field(default=48, gt=0, le=240)
    vesting_frequency_months: int = Field(default=1, ge=1, le=12)
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_vesting(self) -> "GrantBase":
        if self.cliff_months > self.vesting_months:
            raise ValueError("cliff_months cannot exceed vesting_months")
        if self.vesting_months % self.vesting_frequency_months != 0:
            raise ValueError("vesting_months must be divisible by vesting_frequency_months")
        if self.cliff_months % self.vesting_frequency_months != 0:
            raise ValueError("cliff_months must be divisible by vesting_frequency_months")
        return self


class GrantCreate(GrantBase):
    pass


class GrantUpdate(BaseModel):
    grant_name: str | None = Field(default=None, min_length=2, max_length=120)
    grant_date: date | None = None
    total_options: int | None = Field(default=None, gt=0)
    strike_price_cents: int | None = Field(default=None, ge=0)
    vesting_start_date: date | None = None
    cliff_months: int | None = Field(default=None, ge=0, le=120)
    vesting_months: int | None = Field(default=None, gt=0, le=240)
    vesting_frequency_months: int | None = Field(default=None, ge=1, le=12)
    notes: str | None = Field(default=None, max_length=2000)


class GrantRead(GrantBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class ExerciseCreate(BaseModel):
    exercise_date: date
    options_exercised: int = Field(gt=0)
    price_per_option_cents: int | None = Field(default=None, ge=0)


class ExerciseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    grant_id: int
    exercise_date: date
    options_exercised: int
    price_per_option_cents: int
    created_at: datetime


class GrantVestingSummary(BaseModel):
    grant_id: int
    employee_id: int
    employee_name: str
    grant_name: str
    as_of: date
    total_options: int
    vested_options: int
    unvested_options: int
    exercised_options: int
    available_to_exercise: int
    outstanding_options: int


class DashboardSummary(BaseModel):
    as_of: date
    total_employees: int
    active_employees: int
    total_grants: int
    pool_size: int
    pool_allocated: int
    pool_remaining: int
    vested_options: int
    unvested_options: int
    exercised_options: int
    grant_summaries: list[GrantVestingSummary]


class AuthUser(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    employee_id: int | None


class AuthSession(BaseModel):
    authenticated: bool
    user: AuthUser | None = None
