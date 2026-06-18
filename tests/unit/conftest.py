from datetime import datetime, timezone
import pytest
from app.db.models import SensorReadingModel
from app.domain.exceptions import DuplicateReadingError
from app.schemas.sensor_reading import SensorReadingIn
from app.services.ingestion_service import IngestionService


class FakeRepository:
    def __init__(self):
        self.store: list[SensorReadingModel] = []
        self.should_raise: Exception | None = None

    def add(self, reading):
        if self.should_raise:
            raise self.should_raise
        for existing in self.store:               # emulate the unique constraint
            if existing.sensor_id == reading.sensor_id and existing.timestamp == reading.timestamp:
                raise DuplicateReadingError(
                    f"Reading for sensor '{reading.sensor_id}' at {reading.timestamp} already exists."
                )
        model = SensorReadingModel(
            id=len(self.store) + 1,
            sensor_id=reading.sensor_id,
            timestamp=reading.timestamp,
            reading=reading.reading,
            received_at=datetime.now(timezone.utc),
        )
        self.store.append(model)
        return model

    def list_by_sensor(self, sensor_id, limit):
        if self.should_raise:
            raise self.should_raise
        return [r for r in self.store if r.sensor_id == sensor_id][:limit]


@pytest.fixture
def repo():
    return FakeRepository()

@pytest.fixture
def service(repo):
    return IngestionService(repo)

@pytest.fixture
def make_payload():
    def _make(sensor_id="sensor-01", timestamp=None, reading=23.5):
        return SensorReadingIn(
            sensor_id=sensor_id,
            timestamp=timestamp or datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc),
            reading=reading,
        )
    return _make