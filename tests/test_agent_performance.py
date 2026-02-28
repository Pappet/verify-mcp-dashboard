import sys
import os
import json
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

try:
    import app as flask_app
except ImportError:
    pass

@pytest.fixture
def client():
    flask_app.app.config['TESTING'] = True
    with flask_app.app.test_client() as client:
        yield client

def test_agent_performance_endpoint_returns_200(client):
    """GET /api/agent_performance gibt HTTP 200 zurück."""
    response = client.get('/api/agent_performance')
    assert response.status_code == 200, f"Erwartet 200, bekam {response.status_code}"

def test_agent_performance_returns_json(client):
    """Response enthält 'agents'-Schlüssel als Liste."""
    response = client.get('/api/agent_performance')
    data = json.loads(response.data)
    
    assert 'agents' in data, "'agents'-Schlüssel fehlt in der Response"
    assert isinstance(data['agents'], list), "'agents' ist keine Liste"

def test_agent_performance_has_required_fields(client):
    """Jeder Agent-Eintrag hat die erforderlichen Felder und die pass_rate ist korrekt."""
    response = client.get('/api/agent_performance')
    data = json.loads(response.data)
    
    agents = data.get('agents', [])
    if not agents:
        pytest.skip("Test database is empty, cannot verify agent fields.")
        
    required_fields = ['agent_id', 'total_contracts', 'passed', 'failed', 'rejected', 'pass_rate']
    
    for agent in agents:
        for field in required_fields:
            assert field in agent, f"Fehlendes Feld '{field}' in Agent-Eintrag: {agent}"
            
        # 4. pass_rate ist ein float zwischen 0 und 100
        pass_rate = agent['pass_rate']
        assert isinstance(pass_rate, (float, int)), f"pass_rate muss numerisch sein, ist {type(pass_rate)}"
        assert 0 <= pass_rate <= 100, f"pass_rate muss zwischen 0 und 100 liegen, ist {pass_rate}"
