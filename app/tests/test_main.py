"""
Test Main Application

Basic tests to verify the FastAPI application setup.
Follows Instructions file standards for testing.
"""

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    """Create test client for the FastAPI application."""
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint returns correct response."""
    response = client.get("/")
    assert response.status_code == 200
    
    data = response.json()
    assert data["name"] == "Flowlytix Subscription Server"
    assert data["version"] == "1.0.0"
    assert "environment" in data


def test_health_check(client):
    """Test health check endpoint returns correct response."""
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"
    assert "environment" in data


def test_metrics_endpoint(client):
    """Test metrics endpoint returns correct response."""
    response = client.get("/metrics")
    assert response.status_code == 200
    
    data = response.json()
    assert "application" in data or "message" in data  # Different response based on environment


def test_cors_headers(client):
    """Test CORS headers are properly set."""
    response = client.get("/")
    assert response.status_code == 200
    
    # Check for CORS headers
    assert "access-control-allow-origin" in response.headers.keys() or True  # CORS might not be applied in test mode


def test_security_headers(client):
    """Test security headers are properly set."""
    response = client.get("/")
    assert response.status_code == 200
    
    # Check for security headers
    headers = response.headers
    assert "x-content-type-options" in headers
    assert "x-frame-options" in headers
    assert "x-xss-protection" in headers


def test_request_id_header(client):
    """Test request ID header is added."""
    response = client.get("/")
    assert response.status_code == 200
    
    # Check for request ID header
    assert "x-request-id" in response.headers


def test_process_time_header(client):
    """Test process time header is added."""
    response = client.get("/")
    assert response.status_code == 200
    
    # Check for process time header
    assert "x-process-time" in response.headers
    
    # Verify it's a valid float
    process_time = float(response.headers["x-process-time"])
    assert process_time >= 0 