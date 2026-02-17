from types import SimpleNamespace
from datetime import date, datetime, timezone

from app.api.deps import get_current_employee_record, get_current_user, get_current_user_optional
from app.main import app
from app.models import UserRole


def test_employee_grant_and_dashboard_flow(client) -> None:
    employee_payload = {
        "employee_code": "E-1001",
        "full_name": "Jane Doe",
        "email": "jane@example.com",
        "joining_date": "2024-01-01",
        "status": "active",
    }

    create_employee = client.post("/api/employees", json=employee_payload)
    assert create_employee.status_code == 201
    employee_id = create_employee.json()["id"]

    grant_payload = {
        "employee_id": employee_id,
        "grant_name": "Founding Team Grant",
        "grant_date": "2024-01-01",
        "total_options": 4800,
        "strike_price_cents": 250,
        "vesting_start_date": "2024-01-01",
        "cliff_months": 12,
        "vesting_months": 48,
        "vesting_frequency_months": 1,
        "notes": "Core leadership grant",
    }

    create_grant = client.post("/api/grants", json=grant_payload)
    assert create_grant.status_code == 201
    grant_id = create_grant.json()["id"]

    summary = client.get(f"/api/grants/{grant_id}/summary", params={"as_of": "2025-01-01"})
    assert summary.status_code == 200
    summary_json = summary.json()
    assert summary_json["vested_options"] == 1200
    assert summary_json["available_to_exercise"] == 1200

    record_exercise = client.post(
        f"/api/grants/{grant_id}/exercises",
        json={"exercise_date": "2025-01-01", "options_exercised": 300, "price_per_option_cents": 250},
    )
    assert record_exercise.status_code == 201

    dashboard = client.get("/api/dashboard/summary", params={"as_of": "2025-01-01"})
    assert dashboard.status_code == 200
    dashboard_json = dashboard.json()
    assert dashboard_json["total_employees"] == 1
    assert dashboard_json["total_grants"] == 1
    assert dashboard_json["exercised_options"] == 300


def test_exercise_cannot_exceed_vested(client) -> None:
    create_employee = client.post(
        "/api/employees",
        json={
            "employee_code": "E-1002",
            "full_name": "John Smith",
            "email": "john@example.com",
            "joining_date": "2024-01-01",
            "status": "active",
        },
    )
    employee_id = create_employee.json()["id"]

    create_grant = client.post(
        "/api/grants",
        json={
            "employee_id": employee_id,
            "grant_name": "Standard Grant",
            "grant_date": "2024-01-01",
            "total_options": 1200,
            "strike_price_cents": 100,
            "vesting_start_date": "2024-01-01",
            "cliff_months": 12,
            "vesting_months": 48,
            "vesting_frequency_months": 1,
            "notes": None,
        },
    )
    grant_id = create_grant.json()["id"]

    over_exercise = client.post(
        f"/api/grants/{grant_id}/exercises",
        json={"exercise_date": "2024-06-01", "options_exercised": 10, "price_per_option_cents": 100},
    )
    assert over_exercise.status_code == 400
    assert "vested" in over_exercise.json()["detail"].lower()


def test_employee_role_is_read_only_and_scoped(client) -> None:
    admin_create_employee = client.post(
        "/api/employees",
        json={
            "employee_code": "E-2001",
            "full_name": "Role Scoped User",
            "email": "user@example.com",
            "joining_date": "2024-01-01",
            "status": "active",
        },
    )
    assert admin_create_employee.status_code == 201
    employee_id = admin_create_employee.json()["id"]

    admin_create_grant = client.post(
        "/api/grants",
        json={
            "employee_id": employee_id,
            "grant_name": "User Grant",
            "grant_date": "2024-01-01",
            "total_options": 1200,
            "strike_price_cents": 100,
            "vesting_start_date": "2024-01-01",
            "cliff_months": 12,
            "vesting_months": 48,
            "vesting_frequency_months": 1,
            "notes": None,
        },
    )
    assert admin_create_grant.status_code == 201

    fake_employee_user = SimpleNamespace(
        id=22,
        email="user@example.com",
        full_name="Role Scoped User",
        role=UserRole.EMPLOYEE,
        employee_id=employee_id,
    )
    fake_employee_record = SimpleNamespace(
        id=employee_id,
        employee_code="E-2001",
        full_name="Role Scoped User",
        email="user@example.com",
        joining_date=date(2024, 1, 1),
        status="active",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    app.dependency_overrides[get_current_user] = lambda: fake_employee_user
    app.dependency_overrides[get_current_user_optional] = lambda: fake_employee_user
    app.dependency_overrides[get_current_employee_record] = lambda: fake_employee_record
    try:
        blocked_create = client.post(
            "/api/employees",
            json={
                "employee_code": "E-9999",
                "full_name": "Blocked",
                "email": "blocked@example.com",
                "joining_date": "2024-01-01",
                "status": "active",
            },
        )
        assert blocked_create.status_code == 403

        employees_visible = client.get("/api/employees")
        assert employees_visible.status_code == 200
        rows = employees_visible.json()
        assert len(rows) == 1
        assert rows[0]["email"] == "user@example.com"

        grants_visible = client.get("/api/grants")
        assert grants_visible.status_code == 200
        grant_rows = grants_visible.json()
        assert len(grant_rows) == 1
        assert grant_rows[0]["employee_id"] == employee_id
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_current_user_optional, None)
        app.dependency_overrides.pop(get_current_employee_record, None)
