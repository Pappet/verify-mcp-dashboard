#!/usr/bin/env python3
"""Prüft HTTP-Response von /api/status via Flask-Test-Client."""
import sys
import json

sys.path.insert(0, '/home/peter/Projekte/verify-mcp-dashboard/src')
from app import app  # noqa: E402

client = app.test_client()
response = client.get('/api/status')

if response.status_code != 200:
    print(f"FEHLER: HTTP-Status {response.status_code}, erwartet 200")
    sys.exit(1)

data = json.loads(response.data)

if 'status' not in data:
    print(f"FEHLER: 'status'-Schlüssel fehlt. Response: {data}")
    sys.exit(1)

print(f"OK: Route /api/status antwortet korrekt: {data}")
sys.exit(0)
