import os
import tempfile
import pytest
from app import create_app
from app.config import Config

class TestConfig(Config):
    TESTING = True
    UPLOAD_FOLDER = tempfile.gettempdir()
    WTF_CSRF_ENABLED = False

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    app = create_app('testing')
    
    # Create a temporary file to use as test upload
    with tempfile.NamedTemporaryFile(suffix='.epub') as f:
        app.config['TEST_EPUB'] = f.name
    with tempfile.NamedTemporaryFile(suffix='.xml') as f:
        app.config['TEST_XML'] = f.name
    
    yield app
    
    # Cleanup
    try:
        os.unlink(app.config['TEST_EPUB'])
        os.unlink(app.config['TEST_XML'])
    except:
        pass

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()