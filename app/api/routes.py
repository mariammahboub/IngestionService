from fastapi import APIRouter, Depends, Query, status
from app.api.dependencies import get_ingestion_service
from app.schemas.sensor_reading import SensorReadingIn, SensorReadingOut
from app.services.ingestion_service import IngestionService

router = APIRouter(prefix="/api/v1", tags=["Sensor Readings"])


@router.post(
    "/readings",
    response_model=SensorReadingOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Reading stored successfully"},
        409: {"description": "Reading already exists for this sensor and timestamp"},
        422: {"description": "Validation error — malformed request body"},
        500: {"description": "Internal server error — storage failure"},
    },
)
def create_reading(
    payload: SensorReadingIn,
    service: IngestionService = Depends(get_ingestion_service),
) -> SensorReadingOut:
    return service.ingest(payload)


@router.get(
    "/readings/{sensor_id}",
    response_model=list[SensorReadingOut],
    responses={
        200: {"description": "Readings ordered by timestamp descending"},
        404: {"description": "No readings found for this sensor"},
        422: {"description": "Invalid limit parameter"},
        500: {"description": "Internal server error — fetch failure"},
    },
)
def list_readings(
    sensor_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    service: IngestionService = Depends(get_ingestion_service),
) -> list[SensorReadingOut]:
    return service.get_readings(sensor_id, limit)