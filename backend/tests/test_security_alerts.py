import os
import csv
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth.jwt_handler import create_jwt
from app.auth.security_logger import log_security_alert

client = TestClient(app)

def test_admin_alerts_unauthorized():
    response = client.get("/api/admin/security-alerts")
    assert response.status_code == 401

def test_admin_alerts_non_admin_denied():
    token = create_jwt(user_id="sales-id", email="sales@nexora.com", role="sales", full_name="Sales User")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/admin/security-alerts", headers=headers)
    assert response.status_code == 403

def test_admin_alerts_list():
    token = create_jwt(user_id="admin-id", email="admin@nexora.com", role="admin", full_name="Admin User")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/admin/security-alerts", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "alerts" in data
    assert isinstance(data["alerts"], list)

def test_log_security_alert_creates_csv():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, "data", "security_alerts.csv")
    if os.path.exists(csv_path):
        try:
            os.remove(csv_path)
        except Exception:
            pass

    log_security_alert(
        query="SELECT * FROM secrets",
        user_id="test-user-id",
        user_role="sales",
        user_name="Test User",
        alert_type="unauthorized_column_access",
        details="Access to secret column denied"
    )

    assert os.path.exists(csv_path)
    with open(csv_path, mode="r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader)
        assert headers == ["Timestamp", "User ID", "User Name", "User Role", "Query", "Alert Type", "Details"]
        row = next(reader)
        assert row[1] == "test-user-id"
        assert row[2] == "Test User"
        assert row[3] == "sales"
        assert row[4] == "SELECT * FROM secrets"
        assert row[5] == "unauthorized_column_access"
        assert row[6] == "Access to secret column denied"