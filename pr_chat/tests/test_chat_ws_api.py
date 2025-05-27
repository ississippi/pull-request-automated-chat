
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from chat_ws_api import app, get_pr_diffs, get_history, save_to_dynamodb

client = TestClient(app)

@pytest.fixture
def sample_diffs():
    return "diff --git a/file1.txt b/file1.txt\n+Added line"

@patch("git_provider.get_supported_diffs")
def test_get_pr_diffs_success(mock_get_supported_diffs, sample_diffs):
    mock_get_supported_diffs.return_value = sample_diffs
    result = get_pr_diffs("some/repo", 123)
    print("DIFF RESULT:", result)
    assert "Added line" in result
    

@patch("git_provider.get_supported_diffs")
def test_get_pr_diffs_failure(mock_get_supported_diffs):
    mock_get_supported_diffs.return_value = None
    result = get_pr_diffs("some/repo", 123)
    assert result == "Error fetching diffs."

def test_serve_index():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

@patch("boto3.client")
def test_save_to_dynamodb(mock_boto3_client):
    mock_ddb = MagicMock()
    mock_boto3_client.return_value = mock_ddb
    history = [{"user": "Hello", "ai": "Hi there!"}]
    save_to_dynamodb("session123", history)
    mock_ddb.put_item.assert_called()

@patch("chat_ws_api.DynamoDBChatMessageHistory")
def test_get_history(mock_history_class):
    mock_instance = MagicMock()
    mock_history_class.return_value = mock_instance
    history = get_history("session123")
    assert history == mock_instance
