from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.services.bootstrap_service import BootstrapService


def test_bootstrap_service_patches_legacy_sqlite_distributor_application_columns(tmp_path):
    database_url = "sqlite+pysqlite:///{}".format(tmp_path / "legacy.db")
    engine = create_engine(database_url, future=True, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE distributor_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id VARCHAR(64) NOT NULL,
                user_id INTEGER NOT NULL,
                status VARCHAR(32) NOT NULL DEFAULT 'pending',
                target_level VARCHAR(32) NOT NULL,
                reject_reason VARCHAR(255) NOT NULL DEFAULT '',
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            )
            """
        )

    Base.metadata.create_all(engine)
    BootstrapService(engine, SessionLocal).run()

    columns = {column["name"] for column in inspect(engine).get_columns("distributor_applications")}
    assert {"real_name", "phone", "reason"}.issubset(columns)

    engine.dispose()
