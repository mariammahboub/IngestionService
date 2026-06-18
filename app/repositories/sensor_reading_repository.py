from typing import Protocol
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import SensorReadingModel
from app.domain.entities import SensorReading
from app.domain.exceptions import DuplicateReadingError, ReadingPersistenceError


class SensorReadingRepository(Protocol):
    def add(self, reading: SensorReading) -> SensorReadingModel: ...
    def list_by_sensor(self, sensor_id: str, limit: int) -> list[SensorReadingModel]: ...


class SqlAlchemySensorReadingRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, reading: SensorReading) -> SensorReadingModel:
        model = SensorReadingModel(
            sensor_id=reading.sensor_id,
            timestamp=reading.timestamp,
            reading=reading.reading,
        )
        try:
            self.db.add(model)
            self.db.commit()
            self.db.refresh(model)
            return model
        except IntegrityError:
            self.db.rollback()
            raise DuplicateReadingError(
                f"Reading for sensor '{reading.sensor_id}' at {reading.timestamp} already exists."
            )
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise ReadingPersistenceError(cause=exc)

    def list_by_sensor(self, sensor_id: str, limit: int) -> list[SensorReadingModel]:
        try:
            return (
                self.db.query(SensorReadingModel)
                .filter(SensorReadingModel.sensor_id == sensor_id)
                .order_by(SensorReadingModel.timestamp.desc())
                .limit(limit)
                .all()
            )
        except SQLAlchemyError as exc:
            raise ReadingPersistenceError(cause=exc)