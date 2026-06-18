import pytest
from app.domain.exceptions import (
    DuplicateReadingError, ReadingPersistenceError, SensorNotFoundError,
)


def test_ingest_duplicate_raises(service, make_payload):
    payload = make_payload()
    service.ingest(payload)
    with pytest.raises(DuplicateReadingError):
        service.ingest(payload)


def test_get_readings_unknown_sensor_raises_not_found(service):
    with pytest.raises(SensorNotFoundError):
        service.get_readings("sensor-unknown", limit=10)


def test_get_readings_limit_over_max_raises(service):
    with pytest.raises(ValueError, match="limit must be between"):
        service.get_readings("sensor-A", limit=1001)


def test_ingest_persistence_failure_propagates(service, repo, make_payload):
    repo.should_raise = ReadingPersistenceError(cause=Exception("disk full"))
    with pytest.raises(ReadingPersistenceError):
        service.ingest(make_payload())