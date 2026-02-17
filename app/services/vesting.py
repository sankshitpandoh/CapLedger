from datetime import date

from app.models import Grant
from app.schemas import GrantVestingSummary


def complete_months_between(start: date, end: date) -> int:
    if end < start:
        return -1
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1
    return months


def vested_options_for_grant(grant: Grant, as_of: date) -> int:
    if as_of < grant.vesting_start_date:
        return 0

    total_periods = grant.vesting_months // grant.vesting_frequency_months
    elapsed_months = min(complete_months_between(grant.vesting_start_date, as_of), grant.vesting_months)
    elapsed_periods = max(0, elapsed_months // grant.vesting_frequency_months)
    cliff_periods = grant.cliff_months // grant.vesting_frequency_months

    if elapsed_periods < cliff_periods:
        return 0

    vested_periods = min(elapsed_periods, total_periods)
    if vested_periods >= total_periods:
        return grant.total_options

    return (grant.total_options * vested_periods) // total_periods


def summarize_grant(grant: Grant, as_of: date) -> GrantVestingSummary:
    vested = vested_options_for_grant(grant, as_of)
    exercised = sum(ex.options_exercised for ex in grant.exercises if ex.exercise_date <= as_of)
    exercised = min(exercised, grant.total_options)

    available_to_exercise = max(vested - exercised, 0)
    unvested = max(grant.total_options - vested, 0)
    outstanding = max(grant.total_options - exercised, 0)

    return GrantVestingSummary(
        grant_id=grant.id,
        employee_id=grant.employee_id,
        employee_name=grant.employee.full_name,
        grant_name=grant.grant_name,
        as_of=as_of,
        total_options=grant.total_options,
        vested_options=vested,
        unvested_options=unvested,
        exercised_options=exercised,
        available_to_exercise=available_to_exercise,
        outstanding_options=outstanding,
    )
