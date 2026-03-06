"""Tests for the /api/stats_data endpoint."""
import sys
import os
import json
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

try:
    import app as flask_app
except ImportError:
    pass


@pytest.fixture
def client():
    flask_app.app.config['TESTING'] = True
    with flask_app.app.test_client() as client:
        yield client


def test_stats_data_endpoint_returns_200(client):
    """GET /api/stats_data returns HTTP 200."""
    response = client.get('/api/stats_data')
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"


def test_stats_data_returns_json(client):
    """Response is valid JSON with expected keys."""
    response = client.get('/api/stats_data')
    data = json.loads(response.data)
    assert 'daily' in data, "'daily' key missing from response"
    assert 'avg_resolution_minutes' in data, "'avg_resolution_minutes' key missing"
    assert 'struggle_scores' in data, "'struggle_scores' key missing"
    assert 'failing_checks' in data, "'failing_checks' key missing"


def test_struggle_scores_is_list(client):
    """struggle_scores must be a list of objects with 'name' and 'count'."""
    response = client.get('/api/stats_data')
    data = json.loads(response.data)
    scores = data['struggle_scores']
    assert isinstance(scores, list), f"struggle_scores should be a list, got {type(scores)}"
    for entry in scores:
        assert 'name' in entry, f"Entry missing 'name': {entry}"
        assert 'count' in entry, f"Entry missing 'count': {entry}"
        assert isinstance(entry['count'], int), f"count should be int, got {type(entry['count'])}"


def test_project_stats_present(client):
    """project_stats key must be present in response."""
    response = client.get('/api/stats_data')
    data = json.loads(response.data)
    assert 'project_stats' in data, "'project_stats' key missing from response"
