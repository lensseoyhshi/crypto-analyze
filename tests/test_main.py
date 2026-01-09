"""Tests for main application."""
import pytest
from fastapi.testclient import TestClient
from app.main import app


class TestMainApp:
	"""Test suite for main FastAPI application."""
	
	def test_health_endpoint(self):
		"""Test health check endpoint."""
		client = TestClient(app)
		response = client.get("/health")
		
		assert response.status_code == 200
		data = response.json()
		assert data["status"] == "ok"
		assert "app" in data
	
	def test_root_endpoint(self):
		"""Test root endpoint."""
		client = TestClient(app)
		response = client.get("/")
		
		assert response.status_code == 200
		data = response.json()
		assert "message" in data
		assert "docs" in data
		assert "health" in data

