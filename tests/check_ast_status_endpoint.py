#!/usr/bin/env python3
"""Prüft per AST ob die Funktion 'status_endpoint' in src/app.py existiert."""
import ast
import sys

with open('/home/peter/Projekte/verify-mcp-dashboard/src/app.py', 'r') as f:
    source = f.read()

tree = ast.parse(source)
funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]

if 'status_endpoint' in funcs:
    print("OK: Funktion 'status_endpoint' gefunden")
    sys.exit(0)
else:
    print(f"FEHLER: 'status_endpoint' nicht gefunden. Vorhandene Funktionen: {funcs}")
    sys.exit(1)
