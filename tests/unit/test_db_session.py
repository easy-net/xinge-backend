from app.db.session import create_engine_and_session_factory


def test_session_factory_can_be_constructed():
    engine, session_factory = create_engine_and_session_factory("sqlite+pysqlite:///:memory:")
    session = session_factory()
    try:
        assert session is not None
    finally:
        session.close()
        engine.dispose()

