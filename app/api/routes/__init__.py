from fastapi import APIRouter, FastAPI

from app.api.routes.admin_finance import router as admin_finance_router
from app.api.routes.admin_distributor import router as admin_distributor_router
from app.api.routes.health import router as health_router
from app.api.routes.mp_auth import router as mp_auth_router
from app.api.routes.mp_config import router as mp_config_router
from app.api.routes.mp_distributor import router as mp_distributor_router
from app.api.routes.mp_messages import router as mp_messages_router
from app.api.routes.mp_orders import router as mp_orders_router
from app.api.routes.mp_reports import router as mp_reports_router
from app.api.routes.mp_schools import router as mp_schools_router
from app.api.routes.mp_users import router as mp_users_router


def register_routers(app: FastAPI) -> None:
    root = APIRouter()
    root.include_router(health_router)
    root.include_router(admin_finance_router, prefix="/api/v1")
    root.include_router(admin_distributor_router, prefix="/api/v1")
    root.include_router(mp_auth_router, prefix="/api/v1")
    root.include_router(mp_users_router, prefix="/api/v1")
    root.include_router(mp_schools_router, prefix="/api/v1")
    root.include_router(mp_config_router, prefix="/api/v1")
    root.include_router(mp_distributor_router, prefix="/api/v1")
    root.include_router(mp_reports_router, prefix="/api/v1")
    root.include_router(mp_orders_router, prefix="/api/v1")
    root.include_router(mp_messages_router, prefix="/api/v1")
    app.include_router(root)
