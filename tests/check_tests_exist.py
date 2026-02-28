#!/usr/bin/env python3
"""Prüft ob Tests für status_endpoint und api/status in den Tests vorhanden sind."""
import os
import sys

test_dir = '/home/peter/Projekte/verify-mcp-dashboard/tests'
found_status_endpoint = False
found_api_status = False

for fname in os.listdir(test_dir):
    if not fname.endswith('.py'):
        continue
    fpath = os.path.join(test_dir, fname)
    with open(fpath, 'r') as f:
        content = f.read()
    if 'status_endpoint' in content:
        found_status_endpoint = True
    if 'api/status' in content:
        found_api_status = True

if found_status_endpoint and found_api_status:
    print("OK: Tests für status_endpoint und /api/status gefunden")
    sys.exit(0)
else:
    missing = []
    if not found_status_endpoint:
        missing.append('status_endpoint')
    if not found_api_status:
        missing.append('api/status')
    print(f"FEHLER: Fehlende Tests für: {missing}")
    sys.exit(1)
