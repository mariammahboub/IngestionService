from fastapi import Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.repositories.sensor_reading_repository import SqlAlchemySensorReadingRepository
from app.services.ingestion_service import IngestionService


def get_ingestion_service(db: Session = Depends(get_db)) -> IngestionService:
    repository = SqlAlchemySensorReadingRepository(db)
    return IngestionService(repository)