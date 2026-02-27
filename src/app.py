import os
import sqlite3
import json
from flask import Flask, render_template, request, abort

app = Flask(__name__)

def get_db_path():
    xdg_data = os.environ.get("XDG_DATA_HOME")
    if xdg_data:
        base = os.path.join(xdg_data, "verify-mcp")
    else:
        base = os.path.join(os.path.expanduser("~"), ".local", "share", "verify-mcp")
    return os.path.join(base, "verify.db")

def get_db():
    db_path = get_db_path()
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Datenbank nicht gefunden unter: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/')
def dashboard():
    try:
        conn = get_db()
    except FileNotFoundError as e:
        return str(e), 500

    cur = conn.cursor()
    
    # Statistiken
    cur.execute("SELECT status, COUNT(*) as count FROM contracts GROUP BY status")
    rows = cur.fetchall()
    
    stats = {'total': 0, 'passed': 0, 'failed': 0, 'running': 0, 'pending': 0, 'rate': 0.0}
    for r in rows:
        st = r['status']
        cnt = r['count']
        stats['total'] += cnt
        if st in stats:
            stats[st] += cnt
            
    completed = stats['passed'] + stats['failed']
    if completed > 0:
        stats['rate'] = round((stats['passed'] / completed) * 100, 1)

    # Letzte 10 aktive/neue Contracts
    cur.execute("""
        SELECT id, description, task, status, created_at 
        FROM contracts 
        ORDER BY created_at DESC LIMIT 10
    """)
    active_contracts = cur.fetchall()
    conn.close()

    return render_template('dashboard.html', stats=stats, active_contracts=active_contracts)

@app.route('/history')
def history():
    conn = get_db()
    cur = conn.cursor()
    
    search_query = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '').strip()
    
    query = "SELECT id, description, task, status, created_at FROM contracts WHERE 1=1"
    params = []
    
    if search_query:
        query += " AND (description LIKE ? OR task LIKE ?)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])
        
    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)
        
    query += " ORDER BY created_at DESC LIMIT 100"
    
    cur.execute(query, params)
    contracts = cur.fetchall()
    conn.close()
    
    return render_template('history.html', contracts=contracts)

@app.route('/contract/<contract_id>')
def contract_detail(contract_id):
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM contracts WHERE id = ?", (contract_id,))
    contract = cur.fetchone()
    
    if not contract:
        abort(404, description="Contract not found")
        
    cur.execute("SELECT * FROM check_results WHERE contract_id = ? ORDER BY id ASC", (contract_id,))
    results = cur.fetchall()
    conn.close()
    
    # Pretty print JSON falls es angezeigt werden muss
    contract_dict = dict(contract)
    try:
        contract_dict['checks_json'] = json.dumps(json.loads(contract_dict['checks_json']), indent=2)
    except:
        pass

    return render_template('detail.html', contract=contract_dict, results=results)

if __name__ == '__main__':
    # Startet lokal, Debug-Modus an für schnelle Iteration
    app.run(host='127.0.0.1', port=5000, debug=True)
