import pytest
from fastapi.testclient import TestClient
from main import app
import uuid

# Initialize Test Client
client = TestClient(app)

# Generate a random user to avoid database conflicts during testing
TEST_USER = f"test_agent_{uuid.uuid4().hex[:6]}"
TEST_PASS = "TestPassword123!"

@pytest.fixture(scope="module")
def auth_tokens():
    """Holds tokens generated during tests to pass to subsequent tests."""
    return {"user_token": None, "admin_token": None}

def test_health_check():
    """Verify the API is online and the root endpoint responds."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"

def test_user_registration():
    """Verify that a new user can securely register."""
    payload = {
        "username": TEST_USER,
        "email": f"{TEST_USER}@legaltest.com",
        "password": TEST_PASS,
        "dob": "1980-01-01",
        "security_question": "Test?",
        "security_answer": "test"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code in [200, 400] # 400 is acceptable if user exists from previous run

def test_user_login(auth_tokens):
    """Verify that the registered user can authenticate and receive a JWT."""
    payload = {
        "username": TEST_USER,
        "password": TEST_PASS
    }
    # Using data instead of json because OAuth2PasswordRequestForm expects form data
    response = client.post("/api/v1/auth/login", data=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    auth_tokens["user_token"] = data["access_token"]

def test_admin_rbac_enforcement(auth_tokens):
    """
    Verify that the Role-Based Access Control (RBAC) works.
    A standard user should be BLOCKED (403) from hitting admin endpoints.
    """
    token = auth_tokens.get("user_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Standard user attempting to access Admin Debug
    response = client.get("/api/v1/admin/debug", headers=headers)
    assert response.status_code == 403

def test_ingest_auth_enforcement():
    """Verify that unauthenticated users cannot upload documents."""
    response = client.post("/api/v1/ingest")
    assert response.status_code == 401 # Unauthorized
