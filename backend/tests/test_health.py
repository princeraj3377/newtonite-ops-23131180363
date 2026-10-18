from fastapi.testclient import TestClient
from app.main import app
from sqlalchemy.exc import OperationalError
from unittest.mock import patch


def test_health_does_not_require_database():
    with patch("app.main.engine.connect", side_effect=AssertionError("Unexpected DB call")):
        response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_readiness_hides_database_connection_errors():
    error = OperationalError("private database connection", {}, Exception("secret"))
    with patch("app.main.engine.connect", side_effect=error):
        response = TestClient(app).get("/ready")
    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")


    assert response.status_code ==200
