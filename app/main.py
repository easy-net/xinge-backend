from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, log_startup_environment

def create_app(settings: Settings = None) -> FastAPI:
    print("create_app.start")
    settings = settings or get_settings()
    print("create_app.settings_loaded")
    settings.validate()
    configure_logging(settings)
    print("create_app.logging_configured")

    from app.api.middleware import register_exception_handlers, register_middleware
    from app.api.routes import register_routers
    from app.db.session import create_engine_and_session_factory
    from app.integrations.wechat_auth import DevBypassWechatAuthClient, NullWechatAuthClient, RealWechatAuthClient
    from app.services.bootstrap_service import BootstrapService

    print("create_app.modules_imported")

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
            verify=settings.wechat_ca_bundle_path or settings.wechat_verify_ssl,
        )
    else:
        app.state.wechat_auth_client = NullWechatAuthClient()
    app.state.wechat_pay_client = None
    log_startup_environment(settings, wechat_auth_client=app.state.wechat_auth_client)
    print("create_app.startup_logged")
    BootstrapService(engine, session_factory).run(
        seed_school_fixtures=settings.seed_school_fixtures_on_startup,
    )
    print("create_app.bootstrap_done")

    register_middleware(app)
    register_exception_handlers(app)
    register_routers(app)
    app.mount("/static", StaticFiles(directory="static"), name="static")
    print("create_app.ready")
    return app


app = create_app()
