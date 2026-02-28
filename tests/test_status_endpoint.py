"""Tests für die neue /api/status Route (status_endpoint)."""
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import app as flask_app


def test_status_endpoint_returns_200():
    """GET /api/status antwortet mit HTTP 200."""
    client = flask_app.app.test_client()
    response = client.get('/api/status')
    assert response.status_code == 200, f"Erwartet 200, bekam {response.status_code}"


def test_status_endpoint_returns_json():
    """GET /api/status gibt valides JSON zurück."""
    client = flask_app.app.test_client()
    response = client.get('/api/status')
    assert response.content_type.startswith('application/json'), \
        f"Content-Type soll JSON sein, bekam: {response.content_type}"


def test_status_endpoint_has_status_key():
    """Response enthält 'status'-Schlüssel mit Wert 'ok'."""
    client = flask_app.app.test_client()
    response = client.get('/api/status')
    data = json.loads(response.data)
    assert 'status' in data, "'status'-Schlüssel fehlt in der Response"
    assert data['status'] == 'ok', f"Erwartet 'ok', bekam '{data['status']}'"


def test_status_endpoint_has_required_fields():
    """Response enthält alle erwarteten Felder."""
    client = flask_app.app.test_client()
    response = client.get('/api/status')
    data = json.loads(response.data)
    required_fields = ['status', 'version', 'app', 'db_available']
    for field in required_fields:
        assert field in data, f"Fehlendes Feld '{field}' in Response: {data}"


def test_status_endpoint_function_exists():
    """Sicherstellt, dass die Funktion status_endpoint im Modul vorhanden ist."""
    assert hasattr(flask_app, 'status_endpoint'), \
        "Funktion 'status_endpoint' nicht in app-Modul gefunden"
