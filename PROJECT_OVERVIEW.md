# Project Overview

## Architecture

The Verify MCP Dashboard is a lightweight frontend application built using **Flask** and **Jinja2**. It connects directly to SQLite databases to present an interactive UI without requiring a complex backend setup or ORM.

### Databases

1. **`verify.db` (Read-only for dashboard)**
   - Managed by the external `verify-mcp-server`.
   - Contains exactly what the Agents log: `contracts`, `check_results`, and `audit_events`.
   - The dashboard uses this to generate stats, history, and anomaly reports.
   
2. **`dashboard_local.db` (Read-write)**
   - Managed entirely by the dashboard.
   - Stores `templates` (saved combinations of Contract checks).
   - Located in the same folder as `verify.db` (e.g., `~/.local/share/verify-mcp/`).

### Core Components

- **`src/app.py`**: The main Flask application file. Orchestrates routing, database connections, and basic data aggregation (calculating stats, identifying anomalies). It also exposes a few JSON API endpoints for dynamic frontend interactions (like the Chart.js integration).
- **`src/templates/`**: HTML files utilizing the Jinja2 templating engine. The UI is built using Bootstrap 5 and customized with a dark theme (`baseAdmin.css`).
- **`src/static/`**: Contains static assets, including CSS (`baseAdmin.css`) and JavaScript files used across the application.

### Key Workflows

- **Monitoring**: The `/` and `/history` routes read directly from `contracts` to list what agents are doing.
- **Analytics**: The `/api/stats_data` route aggregates data for Chart.js to show pass/fail rates over time and identifies the "Top 10 Struggling Checks".
- **Anomaly Detection**: The `/anomalies` route looks for contracts stuck in `pending`/`running` for > 2 hours, or `failed` contracts untouched for > 4 hours, acting as a human oversight mechanism.
- **Contract Templating**: The UI at `/builder` uses `/api/templates` to read/write templates from the local dashboard database, serializing the JSON payload into SQLite.

## Future Expansion

- The system could add polling or WebSockets for real-time updates as the DB changes, currently, it relies on manual page reloads.
- Additional anomaly rules could be added to catch other problematic agent behaviors (like excessive retries).
