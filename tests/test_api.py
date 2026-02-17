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
