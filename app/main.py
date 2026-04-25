from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.middleware import register_exception_handlers, register_middleware
from app.api.routes import register_routers
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.db.session import create_engine_and_session_factory
from app.integrations.wechat_auth import DevBypassWechatAuthClient, NullWechatAuthClient, RealWechatAuthClient
from app.integrations.wechat_pay import NullWechatPayClient
from app.services.bootstrap_service import BootstrapService


def create_app(settings: Settings = None) -> FastAPI:
    settings = settings or get_settings()
    settings.validate()
    configure_logging(settings)

    app = FastAPI(title="xinge-backend", version="0.1.0")
    app.state.settings = settings
    engine, session_factory = create_engine_and_session_factory(settings.database_url)
    app.state.engine = engine
    app.state.session_factory = session_factory
    if settings.dev_auth_bypass:
        app.state.wechat_auth_client = DevBypassWechatAuthClient()
    elif settings.wechat_app_id and settings.wechat_app_secret:
        app.state.wechat_auth_client = RealWechatAuthClient(
            app_id=settings.wechat_app_id,
            app_secret=settings.wechat_app_secret,
        )
    else:
        app.state.wechat_auth_client = NullWechatAuthClient()
    app.state.wechat_pay_client = NullWechatPayClient()
    BootstrapService(engine, session_factory).run()

    register_middleware(app)
    register_exception_handlers(app)
    register_routers(app)
    app.mount("/static", StaticFiles(directory="static"), name="static")
    return app


app = create_app()
