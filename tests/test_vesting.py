from datetime import date
from types import SimpleNamespace

from app.services.vesting import complete_months_between, vested_options_for_grant


def test_complete_months_between_handles_day_boundary() -> None:
    assert complete_months_between(date(2024, 1, 15), date(2025, 1, 14)) == 11
    assert complete_months_between(date(2024, 1, 15), date(2025, 1, 15)) == 12


def test_vesting_respects_cliff_and_full_term() -> None:
    grant = SimpleNamespace(
        vesting_start_date=date(2024, 1, 1),
        vesting_months=48,
        vesting_frequency_months=1,
        cliff_months=12,
        total_options=4800,
    )

    assert vested_options_for_grant(grant, date(2024, 12, 31)) == 0
    assert vested_options_for_grant(grant, date(2025, 1, 1)) == 1200
    assert vested_options_for_grant(grant, date(2028, 1, 1)) == 4800
