import os
import sqlite3
import json
from flask import Flask, render_template, request, abort, jsonify

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

@app.route('/api/dashboard')
def api_dashboard():
    try:
        conn = get_db()
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 500

    cur = conn.cursor()
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

    cur.execute("""
        SELECT id, description, task, status, created_at 
        FROM contracts 
        ORDER BY created_at DESC LIMIT 10
    """)
    active_contracts = [dict(row) for row in cur.fetchall()]
    conn.close()

    return jsonify({"stats": stats, "active_contracts": active_contracts})

@app.route('/history')
def history():
    conn = get_db()
    cur = conn.cursor()
    
    search_query = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    page = int(request.args.get('page', 1))
    per_page = 50
    offset = (page - 1) * per_page
    
    query = "SELECT id, description, task, status, created_at FROM contracts WHERE 1=1"
    count_query = "SELECT COUNT(*) FROM contracts WHERE 1=1"
    params = []
    
    if search_query:
        query += " AND (description LIKE ? OR task LIKE ?)"
        count_query += " AND (description LIKE ? OR task LIKE ?)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])
        
    if status_filter:
        query += " AND status = ?"
        count_query += " AND status = ?"
        params.append(status_filter)
        
    if start_date:
        query += " AND created_at >= ?"
        count_query += " AND created_at >= ?"
        params.append(start_date + "T00:00:00")
        
    if end_date:
        query += " AND created_at <= ?"
        count_query += " AND created_at <= ?"
        params.append(end_date + "T23:59:59")
        
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    
    cur.execute(count_query, params)
    total_count = cur.fetchone()[0]
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
    
    params.append(per_page)
    params.append(offset)
    cur.execute(query, params)
    contracts = cur.fetchall()
    conn.close()
    
    return render_template('history.html', contracts=contracts, page=page, total_pages=total_pages)

@app.route('/stats')
def stats():
    return render_template('stats.html')

@app.route('/api/stats_data')
def api_stats_data():
    try:
        conn = get_db()
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 500

    cur = conn.cursor()
    
    cur.execute("""
        SELECT date(created_at) as day, status, COUNT(*) as count 
        FROM contracts 
        GROUP BY day, status
        ORDER BY day ASC
    """)
    daily_rows = cur.fetchall()
    
    daily_stats = {}
    for r in daily_rows:
        day = r['day']
        if day not in daily_stats:
            daily_stats[day] = {'passed': 0, 'failed': 0, 'total': 0}
        st = r['status']
        cnt = r['count']
        if st in ['passed', 'failed']:
            daily_stats[day][st] += cnt
            daily_stats[day]['total'] += cnt
            
    cur.execute("""
        SELECT check_name, COUNT(*) as count 
        FROM check_results 
        WHERE status = 'failed' 
        GROUP BY check_name 
        ORDER BY count DESC 
        LIMIT 10
    """)
    failing_checks_rows = cur.fetchall()
    failing_checks = [{'name': r['check_name'], 'count': r['count']} for r in failing_checks_rows]
    
    conn.close()
    
    return jsonify({
        "daily": daily_stats,
        "failing_checks": failing_checks
    })

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
