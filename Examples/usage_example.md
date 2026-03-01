# Usage Example

This dashboard helps abstract the verify-mcp-server process.

1. Ensure the `verify.db` exists in the local data directory.
2. Run the dashboard using `python src/app.py`.
3. Open `http://127.0.0.1:5000` to start exploring the verification history and templates.

To create a new contract testing via the CLI for testing:
```bash
verify-mcp-server run <<EOF
{
  "name": "example_check",
  "task": "Test tests exist",
  ...
}
EOF
```
