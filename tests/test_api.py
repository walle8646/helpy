from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_home():
    response = client.get("/")
    assert response.status_code == 200

def test_get_examples():
    response = client.get("/api/examples")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
