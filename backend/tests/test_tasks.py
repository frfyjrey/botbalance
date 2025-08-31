"""
Tests for Celery tasks and task endpoints.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestTaskEndpoints:
    """Test task-related API endpoints."""

    def test_create_echo_task_authenticated(self, authenticated_api_client):
        """Test creating echo task with authentication."""
        url = reverse("api:tasks:create_echo_task")
        data = {"message": "Test message", "delay": 1}

        with patch("botbalance.tasks.tasks.echo_task.delay") as mock_delay:
            mock_task = MagicMock()
            mock_task.id = "test-task-id-123"
            mock_delay.return_value = mock_task

            response = authenticated_api_client.post(url, data, format="json")

            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()

            assert response_data["status"] == "success"
            assert response_data["message"] == "Task created successfully"
            assert response_data["task_id"] == "test-task-id-123"
            assert "task_url" in response_data

            # Check that task was called with correct parameters
            mock_delay.assert_called_once_with("Test message", 1)

    def test_create_echo_task_unauthenticated(self, api_client):
        """Test creating echo task without authentication."""
        url = reverse("api:tasks:create_echo_task")
        data = {"message": "Test message", "delay": 1}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_echo_task_invalid_data(self, authenticated_api_client):
        """Test creating echo task with invalid data."""
        url = reverse("api:tasks:create_echo_task")
        data = {
            "delay": -1  # Invalid delay
            # Missing required 'message'
        }

        response = authenticated_api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()

        assert response_data["status"] == "error"
        assert "errors" in response_data

    def test_create_heartbeat_task(self, authenticated_api_client):
        """Test creating heartbeat task."""
        url = reverse("api:tasks:create_heartbeat_task")

        with patch("botbalance.tasks.tasks.heartbeat_task.delay") as mock_delay:
            mock_task = MagicMock()
            mock_task.id = "heartbeat-task-123"
            mock_delay.return_value = mock_task

            response = authenticated_api_client.post(url)

            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()

            assert response_data["status"] == "success"
            assert response_data["message"] == "Heartbeat task created"
            assert response_data["task_id"] == "heartbeat-task-123"

            mock_delay.assert_called_once()

    def test_create_long_task(self, authenticated_api_client):
        """Test creating long-running task."""
        url = reverse("api:tasks:create_long_task")
        data = {"duration": 30}

        with patch("botbalance.tasks.tasks.long_running_task.delay") as mock_delay:
            mock_task = MagicMock()
            mock_task.id = "long-task-123"
            mock_delay.return_value = mock_task

            response = authenticated_api_client.post(url, data, format="json")

            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()

            assert response_data["status"] == "success"
            assert "Long task created (duration: 30s)" in response_data["message"]
            assert response_data["task_id"] == "long-task-123"

            mock_delay.assert_called_once_with(30)


@pytest.mark.django_db
class TestTaskStatusEndpoint:
    """Test task status endpoint."""

    def test_get_task_status_success(self, authenticated_api_client):
        """Test getting task status for successful task."""
        url = reverse("api:tasks:task_status")

        with patch("botbalance.api.views.AsyncResult") as mock_result:
            mock_task = MagicMock()
            mock_task.state = "SUCCESS"
            mock_task.result = {"message": "Task completed", "status": "completed"}
            mock_task.info = {"message": "Task completed", "status": "completed"}
            mock_task.traceback = None
            mock_task.successful.return_value = True
            mock_task.ready.return_value = True
            mock_result.return_value = mock_task

            response = authenticated_api_client.get(url, {"task_id": "test-task-123"})

            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()

            assert response_data["status"] == "success"
            assert response_data["task"]["task_id"] == "test-task-123"
            assert response_data["task"]["state"] == "SUCCESS"
            assert response_data["task"]["successful"] is True
            assert response_data["task"]["ready"] is True

    def test_get_task_status_pending(self, authenticated_api_client):
        """Test getting task status for pending task."""
        url = reverse("api:tasks:task_status")

        with patch("botbalance.api.views.AsyncResult") as mock_result:
            mock_task = MagicMock()
            mock_task.state = "PENDING"
            mock_task.result = None
            mock_task.info = None
            mock_task.traceback = None
            mock_task.successful.return_value = None
            mock_task.ready.return_value = False
            mock_result.return_value = mock_task

            response = authenticated_api_client.get(
                url, {"task_id": "pending-task-123"}
            )

            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()

            assert response_data["status"] == "success"
            assert response_data["task"]["state"] == "PENDING"
            assert response_data["task"]["ready"] is False

    def test_get_task_status_progress(self, authenticated_api_client):
        """Test getting task status for task in progress."""
        url = reverse("api:tasks:task_status")

        with patch("botbalance.api.views.AsyncResult") as mock_result:
            mock_task = MagicMock()
            mock_task.state = "PROGRESS"
            mock_task.result = None
            mock_task.info = {
                "current": 5,
                "total": 10,
                "status": "Processing step 5/10",
            }
            mock_task.traceback = None
            mock_task.successful.return_value = None
            mock_task.ready.return_value = False
            mock_result.return_value = mock_task

            response = authenticated_api_client.get(
                url, {"task_id": "progress-task-123"}
            )

            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()

            assert response_data["status"] == "success"
            assert response_data["task"]["state"] == "PROGRESS"
            assert "progress" in response_data["task"]
            assert response_data["task"]["progress"]["current"] == 5
            assert response_data["task"]["progress"]["total"] == 10
            assert response_data["task"]["progress"]["percentage"] == 50.0

    def test_get_task_status_missing_task_id(self, authenticated_api_client):
        """Test getting task status without task_id parameter."""
        url = reverse("api:tasks:task_status")

        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()

        assert response_data["status"] == "error"
        assert "task_id parameter is required" in response_data["message"]

    def test_get_task_status_unauthenticated(self, api_client):
        """Test getting task status without authentication."""
        url = reverse("api:tasks:task_status")

        response = api_client.get(url, {"task_id": "test-task-123"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# Note: Direct task logic tests are complex with Celery bindings.
# In a real project, you might use celery.contrib.testing.worker
# or integration tests with a real worker.
# For this botbalance, API endpoint tests provide sufficient coverage.
