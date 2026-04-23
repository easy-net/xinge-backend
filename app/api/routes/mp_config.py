from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.core.response import public_response
from app.services.product_config_service import ProductConfigService

router = APIRouter(tags=["mp/config"])


@router.post("/mp/config/product")
def product_config(
    _: dict = Body(default_factory=dict),
    db: Session = Depends(get_db_session),
):
    data = ProductConfigService(db).get_current_config()
    return public_response(data=data)

