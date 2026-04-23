from app.core.errors import NotFoundError
from app.repositories.product_config_repository import ProductConfigRepository


class ProductConfigService:
    def __init__(self, db):
        self.repository = ProductConfigRepository(db)

    def get_current_config(self):
        config = self.repository.get_current()
        if config is None:
            raise NotFoundError(message="product config not found")
        return {
            "price": {
                "currency": config.currency,
                "current_amount": config.current_amount,
                "current_amount_display": config.current_amount_display,
                "description": config.description,
                "discount_rate": config.discount_rate,
                "is_limited_time": config.is_limited_time,
                "limited_time_end": config.limited_time_end,
                "original_amount": config.original_amount,
                "original_amount_display": config.original_amount_display,
            },
            "user_stats": {
                "display_count": config.display_count,
                "display_text": config.display_text,
            },
        }

