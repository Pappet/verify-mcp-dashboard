# Verify MCP Dashboard

A modern, responsive dashboard to monitor, manage, and interact with the [Verify MCP Server](https://github.com/Pappet/verify-mcp-server).

## Description

The Verify MCP Server tracks "verification contracts" (checks that ensure AI agents write correct code before committing). This dashboard visualizes the data from the verify MCP server's SQLite database, offering:

- **Dashboard overview**: High-level statistics, success rates, agent trust scores, and recent active contracts.
- **Contract History**: Pagination and filtering of all historical verification contracts, including agent identities.
- **Anomalies Detection**: Identify "orphaned" (stuck in pending/running) or "abandoned" (failed and untouched) contracts.
- **Contract Builder**: A visual UI to build new contracts, integrating available server templates directly from the MCP server.
- **Detailed Audit Trails**: View the exact timeline of a contract, see which checks failed, and how the agent recovered.

## Prerequisites

- Python 3.8+
- The Verify MCP Server database should be located at `~/.local/share/verify-mcp/verify.db` or defined by your `XDG_DATA_HOME` environment variable.

## Setup & Run

1. **Clone the repository** (if not already done).

2. **Install requirements**:
   We recommend using a virtual environment.
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Run the Flask application**:
   ```bash
   flask --app src/app run --debug
   # OR
   python src/app.py
   ```
   The dashboard will be available at [http://127.0.0.1:5000](http://127.0.0.1:5000).

## Usage

- **Home**: View current statistics and the most recent contracts.
- **History**: Search contracts by description or task, and filter by status.
- **Anomalies**: Keep an eye out for contracts that the AI agents left hanging or failed to resolve.
- **Builder**: Experiment with what different contracts look like and save useful combinations.

## Data Storage

- The dashboard reads entirely from `verify.db` (usually managed by the MCP server).
- It queries the `templates` table directly from the MCP server, providing always-up-to-date built-in and promoted templates.
- **Project Mapping**: You can create a `projects.json` file in the same directory as the database (e.g. `~/.local/share/verify-mcp/projects.json`) with the format `{"workspace_hash": "Project Name"}` to automatically display readable project names instead of raw hashes on the dashboard.

## Contribution

Contributions are welcome! If you'd like to improve the dashboard or add new features:
1. Fork the repository.
2. Create your feature branch (`git checkout -b feature/my-new-feature`).
3. Commit your changes (`git commit -am 'Add some feature'`).
4. Ensure all code passes the Verify Contract checks before committing.
5. Push to the branch (`git push origin feature/my-new-feature`).
6. Open a new Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
