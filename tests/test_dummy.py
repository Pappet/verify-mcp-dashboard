import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

def test_dummy():
    import app
    assert hasattr(app, 'api_stats_data')
