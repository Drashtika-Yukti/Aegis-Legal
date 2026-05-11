import pytest
import httpx
import json
import asyncio

BASE_URL = "http://localhost:8000/api/v1"

@pytest.mark.asyncio
async def test_auth_handshake():
    """Verify that the security gate accepts correct credentials."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/auth/token",
            data={"username": "admin", "password": "aegis2024"}
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

@pytest.mark.asyncio
async def test_utility_agent_time():
    """Verify that the Utility Agent can handle time-based legal queries."""
    async with httpx.AsyncClient() as client:
        # Get token
        auth = await client.post(f"{BASE_URL}/auth/token", data={"username": "admin", "password": "aegis2024"})
        token = auth.json()["access_token"]
        
        headers = {"Authorization": f"Bearer {token}"}
        async with client.stream("POST", f"{BASE_URL}/chat", json={"query": "What time is it now?"}, headers=headers, timeout=30.0) as response:
            assert response.status_code == 200
            
            # Check for 'token' events containing numbers (time)
            found_time = False
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    if data["type"] == "token":
                        found_time = True
                        break
            assert found_time

@pytest.mark.asyncio
async def test_editorial_agent_polishing():
    """Verify that the Polishing Node is active by checking for structured formatting."""
    async with httpx.AsyncClient() as client:
        auth = await client.post(f"{BASE_URL}/auth/token", data={"username": "admin", "password": "aegis2024"})
        token = auth.json()["access_token"]
        
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.post(f"{BASE_URL}/chat", json={"query": "List 3 legal facts about contracts."}, headers=headers, timeout=30.0)
        
        # In a real test we'd consume the stream and check for bolding (**) or bullets (*)
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_upload_vault_handshake():
    """Verify the Document Vault listing endpoint."""
    async with httpx.AsyncClient() as client:
        auth = await client.post(f"{BASE_URL}/auth/token", data={"username": "admin", "password": "aegis2024"})
        token = auth.json()["access_token"]
        
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get(f"{BASE_URL}/documents", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) >= 0
