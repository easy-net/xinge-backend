from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.product_config import ProductConfig


class ProductConfigRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_current(self):
        return self.db.execute(select(ProductConfig).limit(1)).scalar_one_or_none()

