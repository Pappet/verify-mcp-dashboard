# Project Overview

## What it is?
The Verify MCP Dashboard is a modern, responsive web application for monitoring, managing, and interacting with the Verify MCP Server. It provides visual insights into AI agent verification contracts, helping track testing history and identify anomalies during development workflows.

## Project Stats
- **Version**: 1.0.0
- **Status**: Active / In Development
- **Tech Stack**: Python (Flask), HTML/CSS/JS (Bootstrap + Chart.js)
- **Database**: SQLite

## Architecture

The Verify MCP Dashboard is a lightweight frontend application built using **Flask** and **Jinja2**. It connects directly to SQLite databases to present an interactive UI without requiring a complex backend setup or ORM.

### Databases

1. **`verify.db` (Read-only for dashboard)**
   - Managed by the external `verify-mcp-server`.
   - Contains contracts, check results, agent metadata, trust scores, and audit events.
   - The dashboard uses this to generate stats, history, templates, and anomaly reports.

### Core Components

- **`src/app.py`**: The main Flask application file. Orchestrates routing, database connections, and basic data aggregation (calculating stats, identifying anomalies). It also exposes a few JSON API endpoints for dynamic frontend interactions (like the Chart.js integration).
- **`src/templates/`**: HTML files utilizing the Jinja2 templating engine. The UI is built using Bootstrap 5 and customized with a dark theme (`baseAdmin.css`).
- **`src/static/`**: Contains static assets, including CSS (`baseAdmin.css`) and JavaScript files used across the application.

### Key Workflows

- **Monitoring**: The `/` and `/history` routes read directly from `contracts` to list what agents are doing.
- **Analytics**: The `/api/stats_data` and `/api/agent_performance` routes aggregate data for Chart.js to show pass/fail rates, agent trust scores, and identify struggling checks.
- **Anomaly Detection**: The `/anomalies` route looks for contracts stuck in `pending`/`running`, or `failed` contracts untouched for hours. It also supports the new `review_required` statuses.
- **Contract Templating**: The UI at `/builder` uses `/api/templates` to read templates directly from the server's `verify.db`.

## Future Expansion

- The system could add polling or WebSockets for real-time updates as the DB changes, currently, it relies on manual page reloads.
- Additional anomaly rules could be added to catch other problematic agent behaviors (like excessive retries).

## Dependencies and their purpose

- **Flask** (3.0.0): The core web framework used to run the dashboard backend and serve routes/APIs.
- **Jinja2** (3.1.2): Template engine used by Flask to generate dynamic HTML content.
- **Werkzeug** (3.0.1): WSGI web application library underlying Flask, handling routing, and request/response objects.
- **mypy** (1.19.1): Static type checker for Python to guarantee type safety in the codebase.
- **pytest** (9.0.2): Testing framework to run the automated Python tests in `tests/`.
- **types-Flask** (1.1.6): Type hints for Flask, assisting `mypy` in checking Flask-related code.

## Additional References

- [Verify MCP Server GitHub Repository](https://github.com/Pappet/verify-mcp-server)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Chart.js Documentation](https://www.chartjs.org/docs/latest/)
