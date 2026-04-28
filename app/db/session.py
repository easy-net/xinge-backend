from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def create_engine_and_session_factory(database_url: str):
    connect_args = {}
    engine_kwargs = {"future": True, "connect_args": connect_args}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    else:
        engine_kwargs["pool_pre_ping"] = True
        engine_kwargs["pool_recycle"] = 1800

    engine = create_engine(database_url, **engine_kwargs)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return engine, session_factory
