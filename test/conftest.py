import pytest
from app import app as flask_app # Importa tu instancia de Flask/FastAPI

@pytest.fixture
def client():
    flask_app.config.update({"TESTING": True})
    with flask_app.test_client() as client:
        yield client