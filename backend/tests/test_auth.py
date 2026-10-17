from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)



def test_me_without_token():
    response = client.get("/me")


    assert response.status_code ==401