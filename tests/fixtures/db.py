import pytest


@pytest.fixture
def db_session(app):
    session = app.state.session_factory()
    try:
        yield session
    finally:
        session.close()

