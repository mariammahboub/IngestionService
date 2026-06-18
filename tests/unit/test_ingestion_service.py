import pytest
from datetime import datetime, timezone

from app.domain.exceptions import DuplicateReadingError, ReadingPersistenceError
from app.domain.exceptions import SensorNotFoundError


# ── Ingest: happy path ─────────────────────────────────────────────────────────

def test_ingest_returns_stored_model(service, make_payload):
    result = service.ingest(make_payload())
    assert result.sensor_id == "sensor-01"
    assert result.reading == 23.5
    assert result.id == 1


def test_ingest_stores_correct_entity(service, repo, make_payload):
    service.ingest(make_payload(sensor_id="sensor-cairo-01", reading=99.9))
    assert len(repo.store) == 1
    assert repo.store[0].sensor_id == "sensor-cairo-01"
    assert repo.store[0].reading == 99.9


def test_ingest_multiple_sensors_independently(service, repo, make_payload):
    service.ingest(make_payload(sensor_id="sensor-A"))
    service.ingest(make_payload(sensor_id="sensor-B"))
    assert len(repo.store) == 2


def test_ingest_same_sensor_different_timestamps(service, repo, make_payload):
    service.ingest(make_payload(timestamp=datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc)))
    service.ingest(make_payload(timestamp=datetime(2024, 1, 15, 11, 0, tzinfo=timezone.utc)))
    assert len(repo.store) == 2


# ── Ingest: duplicates ─────────────────────────────────────────────────────────

def test_ingest_duplicate_raises_duplicate_error(service, make_payload):
    payload = make_payload()
    service.ingest(payload)
    with pytest.raises(DuplicateReadingError):
        service.ingest(payload)


def test_ingest_duplicate_does_not_store_second_entry(service, repo, make_payload):
    payload = make_payload()
    service.ingest(payload)
    with pytest.raises(DuplicateReadingError):
        service.ingest(payload)
    assert len(repo.store) == 1


# ── Ingest: persistence failure ────────────────────────────────────────────────

def test_ingest_persistence_failure_raises_persistence_error(service, repo, make_payload):
    repo.should_raise = ReadingPersistenceError(cause=Exception("disk full"))
    with pytest.raises(ReadingPersistenceError):
        service.ingest(make_payload())


# ── Get readings: happy path ───────────────────────────────────────────────────

def test_get_readings_returns_correct_sensor_results(service, make_payload):
    service.ingest(make_payload(sensor_id="sensor-A"))
    service.ingest(make_payload(sensor_id="sensor-B"))
    results = service.get_readings("sensor-A", limit=10)
    assert len(results) == 1
    assert results[0].sensor_id == "sensor-A"


def test_get_readings_returns_empty_list_for_unknown_sensor(service):
    with pytest.raises(SensorNotFoundError):
        service.get_readings("sensor-unknown", limit=10)


def test_get_readings_respects_limit(service, make_payload):
    for i in range(10):
        service.ingest(make_payload(
            sensor_id="sensor-A",
            timestamp=datetime(2024, 1, 15, i, 0, tzinfo=timezone.utc),
        ))
    results = service.get_readings("sensor-A", limit=3)
    assert len(results) == 3


# ── Get readings: invalid limit ────────────────────────────────────────────────

def test_get_readings_limit_zero_raises_value_error(service):
    with pytest.raises(ValueError, match="limit must be between"):
        service.get_readings("sensor-A", limit=0)


def test_get_readings_limit_over_max_raises_value_error(service):
    with pytest.raises(ValueError, match="limit must be between"):
        service.get_readings("sensor-A", limit=1001)


# ── Get readings: persistence failure ─────────────────────────────────────────

def test_get_readings_persistence_failure_raises_error(service, repo):
    repo.should_raise = ReadingPersistenceError(cause=Exception("connection lost"))
    with pytest.raises(ReadingPersistenceError):
        service.get_readings("sensor-A", limit=10)