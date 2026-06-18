from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.domain.exceptions import (
    DuplicateReadingError, ReadingPersistenceError, SensorNotFoundError,
)
import logging

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        logger.warning("Validation error | path=%s | errors=%s",
                       request.url.path, exc.errors())
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Request validation failed.",
                "errors": [
                    {
                        "field": " -> ".join(str(loc) for loc in err["loc"]),
                        "message": err["msg"],
                        "type": err["type"],
                    }
                    for err in exc.errors()
                ],
            },
        )

    @app.exception_handler(DuplicateReadingError)
    async def duplicate_handler(request: Request, exc: DuplicateReadingError):
        logger.warning("Duplicate blocked | path=%s | detail=%s",
                       request.url.path, str(exc))
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": str(exc)},
        )

    @app.exception_handler(SensorNotFoundError)
    async def not_found_handler(request: Request, exc: SensorNotFoundError):
        logger.info("Sensor not found | path=%s | sensor_id=%s",
                    request.url.path, exc.sensor_id)
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)},
        )

    @app.exception_handler(ReadingPersistenceError)
    async def persistence_handler(request: Request, exc: ReadingPersistenceError):
        logger.error("Persistence failure | path=%s | cause=%s",
                     request.url.path, exc.cause, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "A storage error occurred. The operation could not be completed."},
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):
        logger.critical("Unhandled exception | path=%s | error=%s",
                        request.url.path, str(exc), exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected error occurred. Please try again later."},
        )