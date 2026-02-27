import os
import sqlite3
import json
from flask import Flask, render_template, request, abort, jsonify
from datetime import datetime

app = Flask(__name__)

ORPHAN_THRESHOLD_HOURS = 2
ABANDONED_THRESHOLD_HOURS = 4

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

@app.route('/anomalies')
def anomalies():
    try:
        conn = get_db()
    except FileNotFoundError:
        return render_template('anomalies.html', orphaned=[], abandoned=[], 
                               orphan_hours=ORPHAN_THRESHOLD_HOURS, 
                               abandon_hours=ABANDONED_THRESHOLD_HOURS, 
                               error="Database not found")
        
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM contracts WHERE status IN ('pending', 'running', 'failed')")
    contracts = cur.fetchall()
    
    # Letztes Event pro Contract suchen, für Abandoned check
    try:
        cur.execute("SELECT contract_id, MAX(created_at) as last_event_time FROM audit_events GROUP BY contract_id")
        last_events_rows = cur.fetchall()
        last_event_times = {row['contract_id']: row['last_event_time'] for row in last_events_rows}
    except Exception:
        last_event_times = {}

    now = datetime.utcnow()
    
    orphaned = []
    abandoned = []
    
    for c in contracts:
        status = c['status']
        cid = c['id']
        
        try:
            created_at = datetime.fromisoformat(c['created_at'].replace('Z', '+00:00')).replace(tzinfo=None)
        except Exception:
            continue
            
        if status in ('pending', 'running'):
            delta = (now - created_at).total_seconds() / 3600
            if delta > ORPHAN_THRESHOLD_HOURS:
                orphaned.append(dict(c))
                
        elif status == 'failed':
            last_event_str = last_event_times.get(cid, c['created_at'])
            try:
                last_time = datetime.fromisoformat(last_event_str.replace('Z', '+00:00')).replace(tzinfo=None)
            except Exception:
                continue
                
            delta = (now - last_time).total_seconds() / 3600
            if delta > ABANDONED_THRESHOLD_HOURS:
                abandoned.append(dict(c))
                
    conn.close()
    
    orphaned.sort(key=lambda x: x['created_at'], reverse=True)
    abandoned.sort(key=lambda x: x['created_at'], reverse=True)
    
    return render_template('anomalies.html', 
                           orphaned=orphaned, 
                           abandoned=abandoned, 
                           orphan_hours=ORPHAN_THRESHOLD_HOURS, 
                           abandon_hours=ABANDONED_THRESHOLD_HOURS)


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
            
    cur.execute("SELECT * FROM audit_events ORDER BY contract_id, created_at ASC")
    all_audit_rows = cur.fetchall()
    
    # Contract Aggregation
    contract_events = {}
    for r in all_audit_rows:
        cid = r['contract_id']
        if cid not in contract_events:
            contract_events[cid] = []
        contract_events[cid].append(dict(r))
        
    total_resolution_time_seconds = 0.0
    resolved_contracts_count = 0
    struggle_scores = {} # type: ignore
    
    for cid, events in contract_events.items():
        created_time = None
        passed_time = None
        
        # Parse Dates
        for e in events:
            if e['event_type'] == 'contract_created':
                try:
                    created_time = datetime.fromisoformat(e['created_at'].replace('Z', '+00:00'))
                except:
                    pass
            elif e['event_type'] == 'verification_passed':
                try:
                    passed_time = datetime.fromisoformat(e['created_at'].replace('Z', '+00:00'))
                except:
                    pass
            elif e['event_type'] == 'verification_failed':
                # Parse details for failing checks
                if e['details']:
                    try:
                        details_json = json.loads(e['details'])
                        if isinstance(details_json, list):
                            for c in details_json:
                                if c.get('status') == 'failed':
                                    cname = c.get('check', 'Unknown')
                                    struggle_scores[cname] = struggle_scores.get(cname, 0) + 1
                    except:
                        pass
        
        if created_time and passed_time:
            delta = (passed_time - created_time).total_seconds()
            if delta > 0:
                total_resolution_time_seconds += delta
                resolved_contracts_count += 1
                
    avg_resolution_seconds = 0.0
    if resolved_contracts_count > 0:
        avg_resolution_seconds = total_resolution_time_seconds / resolved_contracts_count
        
    avg_resolution_minutes = round(avg_resolution_seconds / 60, 2)
    
    # Top 10 Struggling Checks
    sorted_struggle = sorted(struggle_scores.items(), key=lambda x: x[1], reverse=True)[:10]
    struggle_list = [{'name': k, 'count': v} for k, v in sorted_struggle]
    
    conn.close()
    
    return jsonify({
        "daily": daily_stats,
        "failing_checks": failing_checks,
        "struggle_scores": struggle_list,
        "avg_resolution_minutes": avg_resolution_minutes
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
    
    # Audit Timeline laden
    cur.execute("SELECT * FROM audit_events WHERE contract_id = ? ORDER BY created_at ASC", (contract_id,))
    audit_rows = cur.fetchall()
    
    audit_events = []
    for row in audit_rows:
        event = dict(row)
        # Check Details extrahieren, um bei Failed direkt den Schuldigen zu sehen
        if event['event_type'] == 'verification_failed' and event['details']:
            try:
                details_json = json.loads(event['details'])
                if isinstance(details_json, list) and len(details_json) > 0:
                    # Nimm die Namen der gefailten Checks (meistens im details-Array)
                    failed_checks = [c.get('check', 'Unknown') for c in details_json if c.get('status') == 'failed']
                    if failed_checks:
                        event['failed_checks_summary'] = ", ".join(failed_checks)
            except Exception:
                pass
        audit_events.append(event)
        
    conn.close()
    
    # Pretty print JSON falls es angezeigt werden muss
    contract_dict = dict(contract)
    try:
        contract_dict['checks_json'] = json.dumps(json.loads(contract_dict['checks_json']), indent=2)
    except:
        pass

    return render_template('detail.html', contract=contract_dict, results=results, audit_events=audit_events)

if __name__ == '__main__':
    # Startet lokal, Debug-Modus an für schnelle Iteration
    app.run(host='127.0.0.1', port=5000, debug=True)
