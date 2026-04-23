from app.db.base import Base
from app.db.models.product_config import ProductConfig
from app.repositories.product_config_repository import ProductConfigRepository


class BootstrapService:
    def __init__(self, engine, session_factory):
        self.engine = engine
        self.session_factory = session_factory

    def run(self):
        Base.metadata.create_all(self.engine)
        session = self.session_factory()
        try:
            repository = ProductConfigRepository(session)
            if repository.get_current() is None:
                session.add(
                    ProductConfig(
                        current_amount=9900,
                        current_amount_display="99.00",
                        description="完整版学业规划报告",
                        discount_rate=0.5,
                        is_limited_time=True,
                        limited_time_end="2026-05-01T00:00:00Z",
                        original_amount=19900,
                        original_amount_display="199.00",
                        display_count=12345,
                        display_text="已有12345位同学使用",
                    )
                )
                session.commit()
        finally:
            session.close()
