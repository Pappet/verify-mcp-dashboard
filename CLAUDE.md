# CLAUDE.md

## Agent Instructions & Coding Conventions

When working on the **Verify MCP Dashboard**, follow these guidelines:

### Development Loop

- **Define → Work → Verify → Fix**: Every code change MUST use the `verify-mcp-server` contract-based verification.
  - Call `verify_create_contract` before starting execution.
  - Implement changes.
  - Call `verify_run_contract` after execution.
  - Fix any failures until all checks pass, and ONLY then commit the result.

### Tech Stack & Libraries

- **Backend**: Python 3.8+, Flask, sqlite3.
- **Frontend**: HTML5, Jinja2, Vanilla JS, Bootstrap 5.
- **Styling**: Vanilla CSS, Dark Mode first. Do NOT add TailwindCSS or other bloated frameworks unless requested.
- **Database**: `sqlite3` driver. Do NOT add ORMs (like SQLAlchemy) for this project. Stick to raw SQL queries as implemented in `src/app.py`.

### Conventions

- **Database Connections**: Always use `get_db()` for the main Verify database, and `get_dashboard_db_path()` for local dashboard storage. Catch `FileNotFoundError` when connecting to `get_db()` to gracefully handle a missing `verify.db` (usually by showing an empty state or error alert in the UI, not crashing the app).
- **Templates**: Always extend `base.html` for new pages so the navigation and layout remain consistent.
- **Routing**: Return rendered HTML for standard views. For endpoints returning data to JavaScript (like the chart data or template saving), prefix the route with `/api/` and return `jsonify()`.
- **Aesthetics**: Ensure the UI looks "Wow", using modern responsive designs. Rely on the dark mode styling provided in the base app, use Bootstrap utility classes carefully.

### Common Tasks

- **Adding a new Check Type to Builder**: Update the `/api/schema` in `src/app.py` and the corresponding JS handling the dynamic form.
- **Adjusting Anomaly Thresholds**: Modify the `ORPHAN_THRESHOLD_HOURS` and `ABANDONED_THRESHOLD_HOURS` constants in `src/app.py`.
