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

def get_dashboard_db_path():
    xdg_data = os.environ.get("XDG_DATA_HOME")
    if xdg_data:
        base = os.path.join(xdg_data, "verify-mcp")
    else:
        base = os.path.join(os.path.expanduser("~"), ".local", "share", "verify-mcp")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "dashboard_local.db")

def init_dashboard_db():
    db_path = get_dashboard_db_path()
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_dashboard_db()

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
    
    stats = {'total': 0, 'passed': 0, 'failed': 0, 'running': 0, 'pending': 0, 'rejected': 0, 'rate': 0.0}
    for r in rows:
        st = r['status']
        cnt = r['count']
        stats['total'] += cnt
        if st in stats:
            stats[st] += cnt
            
    completed = stats['passed'] + stats['failed'] + stats['rejected']
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
    
    stats = {'total': 0, 'passed': 0, 'failed': 0, 'running': 0, 'pending': 0, 'rejected': 0, 'rate': 0.0}
    for r in rows:
        st = r['status']
        cnt = r['count']
        stats['total'] += cnt
        if st in stats:
            stats[st] += cnt
            
    completed = stats['passed'] + stats['failed'] + stats['rejected']
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

@app.route('/builder')
def builder():
    return render_template('builder.html')

@app.route('/api/schema')
def api_schema():
    # Definiert das Schema der unterstützten Checks für das Frontend
    schema = {
        "check_types": [
            {"id": "command_succeeds", "name": "Command Succeeds", "fields": [{"name": "command", "type": "string"}]},
            {"id": "command_output_matches", "name": "Command Output Matches", "fields": [{"name": "command", "type": "string"}, {"name": "pattern", "type": "string"}]},
            {"id": "file_exists", "name": "File Exists", "fields": [{"name": "path", "type": "string"}]},
            {"id": "file_contains_patterns", "name": "File Contains Patterns", "fields": [{"name": "path", "type": "string"}, {"name": "patterns", "type": "array"}]},
            {"id": "file_excludes_patterns", "name": "File Excludes Patterns", "fields": [{"name": "path", "type": "string"}, {"name": "patterns", "type": "array"}]},
            {"id": "json_schema_valid", "name": "JSON Schema Valid", "fields": [{"name": "schema_path", "type": "string"}, {"name": "json_path", "type": "string"}]},
            {"id": "value_in_range", "name": "Value In Range", "fields": [{"name": "value", "type": "number"}, {"name": "min", "type": "number"}, {"name": "max", "type": "number"}]},
            {"id": "diff_size_limit", "name": "Diff Size Limit", "fields": [{"name": "max_lines", "type": "number"}]},
            {"id": "assertion", "name": "Assertion", "fields": [{"name": "condition", "type": "string"}]},
            {"id": "python_type_check", "name": "Python Type Check", "fields": [{"name": "path", "type": "string"}]},
            {"id": "pytest_result", "name": "Pytest Result", "fields": [{"name": "path", "type": "string"}]},
            {"id": "python_import_graph", "name": "Python Import Graph", "fields": [{"name": "path", "type": "string"}, {"name": "forbidden_imports", "type": "array"}]},
            {"id": "json_registry_consistency", "name": "JSON Registry Consistency", "fields": [{"name": "registry_path", "type": "string"}, {"name": "schema_path", "type": "string"}]}
        ],
        "severities": ["info", "warning", "error"]
    }
    return jsonify(schema)

@app.route('/api/templates', methods=['GET', 'POST'])
def api_templates():
    db_path = get_dashboard_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    if request.method == 'POST':
        data = request.json
        name = data.get('name', 'Unnamed Template')
        payload = json.dumps(data.get('payload', {}))
        
        cur.execute("INSERT INTO templates (name, payload) VALUES (?, ?)", (name, payload))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Template saved"}), 201
        
    else:
        cur.execute("SELECT * FROM templates ORDER BY created_at DESC")
        rows = cur.fetchall()
        templates = [{"id": r["id"], "name": r["name"], "payload": json.loads(r["payload"]), "created_at": r["created_at"]} for r in rows]
        conn.close()
        return jsonify({"templates": templates})

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
            daily_stats[day] = {'passed': 0, 'failed': 0, 'rejected': 0, 'total': 0}
        st = r['status']
        cnt = r['count']
        if st in ['passed', 'failed', 'rejected']:
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
        for evt in events:
            if evt['event_type'] == 'contract_created':
                try:
                    created_time = datetime.fromisoformat(evt['created_at'].replace('Z', '+00:00'))
                except:
                    pass
            elif evt['event_type'] == 'verification_passed':
                try:
                    passed_time = datetime.fromisoformat(evt['created_at'].replace('Z', '+00:00'))
                except:
                    pass
            elif evt['event_type'] == 'verification_failed':
                # Parse details for failing checks
                if evt['details']:
                    try:
                        details_json = json.loads(evt['details'])
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
    
    # Legacy DB Failing Checks
    cur.execute("""
        SELECT check_name as name, COUNT(*) as count 
        FROM check_results 
        WHERE status = 'failed' 
        GROUP BY name 
        ORDER BY count DESC 
        LIMIT 10
    """)
    failing_checks = [{'name': r['name'], 'count': r['count']} for r in cur.fetchall()]
    
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
    db_results = cur.fetchall()
    
    breaks_json = contract['checks_json']
    checks_definition_map = {}
    if breaks_json:
        try:
            checks_data = json.loads(breaks_json)
            if isinstance(checks_data, list):
                for chk in checks_data:
                    checks_definition_map[chk.get('name')] = chk.get('check_type', {})
        except Exception:
            pass

    results = []
    for r in db_results:
        r_dict = dict(r)
        check_name = r_dict.get('check_name')
        if check_name in checks_definition_map:
            try:
                r_dict['definition_json'] = json.dumps(checks_definition_map[check_name], indent=2)
            except Exception:
                r_dict['definition_json'] = "{}"
        else:
            r_dict['definition_json'] = "{}"
        results.append(r_dict)
    
    # Audit Timeline laden
    cur.execute("SELECT * FROM audit_events WHERE contract_id = ? ORDER BY created_at ASC", (contract_id,))
    audit_rows = cur.fetchall()
    
    audit_events = []
    rejection_reason = None
    for row in audit_rows:
        event = dict(row)
        # Rejection reason aus contract_rejected Event extrahieren
        if event['event_type'] == 'contract_rejected' and event['details']:
            rejection_reason = event['details']
        # Check Details extrahieren, um bei Failed direkt den Schuldigen zu sehen
        if event['event_type'] == 'verification_failed' and event['details']:
            try:
                details_json = json.loads(event['details'])
                if isinstance(details_json, list) and len(details_json) > 0:
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
        # Für rejected contracts kann checks_json malformed sein
        pass

    return render_template('detail.html', contract=contract_dict, results=results, 
                           audit_events=audit_events, rejection_reason=rejection_reason)

@app.route('/rejected')
def rejected():
    try:
        conn = get_db()
    except FileNotFoundError as e:
        return render_template('rejected.html', contracts=[], page=1, total_pages=1, error=str(e))

    cur = conn.cursor()
    
    search_query = request.args.get('q', '').strip()
    page = int(request.args.get('page', 1))
    per_page = 50
    offset = (page - 1) * per_page
    
    query = "SELECT id, description, task, agent_id, checks_json, created_at FROM contracts WHERE status = 'rejected'"
    count_query = "SELECT COUNT(*) FROM contracts WHERE status = 'rejected'"
    params = []
    
    if search_query:
        query += " AND (description LIKE ? OR task LIKE ? OR agent_id LIKE ?)"
        count_query += " AND (description LIKE ? OR task LIKE ? OR agent_id LIKE ?)"
        params.extend([f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"])
    
    cur.execute(count_query, params)
    total_count = cur.fetchone()[0]
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
    
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.append(per_page)
    params.append(offset)
    cur.execute(query, params)
    rows = cur.fetchall()
    
    # Rejection reasons aus audit_events joinen
    contracts = []
    for row in rows:
        c = dict(row)
        cur.execute(
            "SELECT details FROM audit_events WHERE contract_id = ? AND event_type = 'contract_rejected' LIMIT 1",
            (c['id'],)
        )
        reason_row = cur.fetchone()
        c['rejection_reason'] = reason_row['details'] if reason_row else 'Unknown reason'
        contracts.append(c)
    
    conn.close()
    
    return render_template('rejected.html', contracts=contracts, page=page, total_pages=total_pages)

@app.route('/api/rejected')
def api_rejected():
    try:
        conn = get_db()
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 500

    cur = conn.cursor()
    cur.execute("""
        SELECT c.id, c.description, c.task, c.agent_id, c.created_at,
               ae.details as rejection_reason
        FROM contracts c
        LEFT JOIN audit_events ae ON ae.contract_id = c.id AND ae.event_type = 'contract_rejected'
        WHERE c.status = 'rejected'
        ORDER BY c.created_at DESC
        LIMIT 100
    """)
    rows = cur.fetchall()
    contracts = [dict(r) for r in rows]
    conn.close()
    
    return jsonify({"rejected_contracts": contracts})

@app.route('/api/agent_performance')
def api_agent_performance():
    try:
        conn = get_db()
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 500

    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Base stats per agent
    cur.execute("""
        SELECT agent_id,
               COUNT(*) as total_contracts,
               SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) as passed,
               SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
               SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected
        FROM contracts
        WHERE agent_id IS NOT NULL AND agent_id != ''
        GROUP BY agent_id
    """)
    agent_rows = cur.fetchall()
    
    # Audit events for resolution times and struggle scores
    cur.execute("""
        SELECT contract_id,
               c.agent_id,
               ae.event_type,
               ae.created_at,
               ae.details
        FROM audit_events ae
        JOIN contracts c ON ae.contract_id = c.id
        WHERE c.agent_id IS NOT NULL AND c.agent_id != ''
        ORDER BY c.agent_id, ae.contract_id, ae.created_at ASC
    """)
    audit_rows = cur.fetchall()
    
    # Organize audit events by agent and contract
    # agent_id -> { contract_id: [events] }
    agent_events = {}
    for r in audit_rows:
        aid = r['agent_id']
        cid = r['contract_id']
        if aid not in agent_events:
            agent_events[aid] = {}
        if cid not in agent_events[aid]:
            agent_events[aid][cid] = []
        agent_events[aid][cid].append(dict(r))
        
    agents_data = []
    
    for row in agent_rows:
        aid = row['agent_id']
        total = row['total_contracts']
        passed = row['passed']
        failed = row['failed']
        rejected = row['rejected']
        
        completed = passed + failed + rejected
        pass_rate = 0.0
        if completed > 0:
            pass_rate = round((passed / completed) * 100, 1)
            
        # Calculate avg resolution and most common failure
        events_by_contract = agent_events.get(aid, {})
        
        total_res_seconds = 0.0
        resolved_count = 0
        struggle_scores = {}
        
        for cid, events in events_by_contract.items():
            created_time = None
            passed_time = None
            
            for evt in events:
                if evt['event_type'] == 'contract_created':
                    try:
                        created_time = datetime.fromisoformat(evt['created_at'].replace('Z', '+00:00'))
                    except Exception:
                        pass
                elif evt['event_type'] == 'verification_passed':
                    try:
                        passed_time = datetime.fromisoformat(evt['created_at'].replace('Z', '+00:00'))
                    except Exception:
                        pass
                elif evt['event_type'] == 'verification_failed':
                    if evt['details']:
                        try:
                            details_json = json.loads(evt['details'])
                            if isinstance(details_json, list):
                                for c in details_json:
                                    if c.get('status') == 'failed':
                                        cname = c.get('check', 'Unknown')
                                        struggle_scores[cname] = struggle_scores.get(cname, 0) + 1
                        except Exception:
                            pass
                            
            if created_time and passed_time:
                delta = (passed_time - created_time).total_seconds()
                if delta > 0:
                    total_res_seconds += delta
                    resolved_count += 1
                    
        avg_resolution_minutes = 0.0
        if resolved_count > 0:
            avg_resolution_minutes = round((total_res_seconds / resolved_count) / 60, 2)
            
        most_common_failure = "none"
        if struggle_scores:
            most_common_failure = max(struggle_scores.items(), key=lambda x: x[1])[0]
            
        agents_data.append({
            "agent_id": aid,
            "total_contracts": total,
            "passed": passed,
            "failed": failed,
            "rejected": rejected,
            "pass_rate": pass_rate,
            "avg_resolution_minutes": avg_resolution_minutes,
            "most_common_failure": most_common_failure
        })
        
    conn.close()
    
    return jsonify({"agents": agents_data})

@app.route('/api/status')
def status_endpoint():
    """Gibt den aktuellen Status der Anwendung als JSON zurück."""
    db_available = True
    try:
        conn = get_db()
        conn.close()
    except FileNotFoundError:
        db_available = False

    return jsonify({
        "status": "ok",
        "version": "1.0.0",
        "app": "verify-mcp-dashboard",
        "db_available": db_available,
    })


if __name__ == '__main__':
    # Startet lokal, Debug-Modus an für schnelle Iteration
    app.run(host='127.0.0.1', port=5000, debug=True)
