from fastapi import FastAPI
from app.api.routes import router
from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import setup_logging
from app.db import models  # noqa: F401  (imported so models register on Base)
from app.db.session import Base, engine

setup_logging()
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)
register_exception_handlers(app)
app.include_router(router)


@app.get("/health", tags=["Health"])
def health_check() -> dict:
    return {"status": "ok", "service": settings.APP_NAME, "version": settings.APP_VERSION}