import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.api.dependencies import get_ingestion_service
from app.db.session import Base, get_db
from app.main import app
from app.repositories.sensor_reading_repository import SqlAlchemySensorReadingRepository
from app.services.ingestion_service import IngestionService

test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def _override_get_ingestion_service():
    db = TestSessionLocal()
    try:
        yield IngestionService(SqlAlchemySensorReadingRepository(db))
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = lambda: (_ for _ in ()).throw(StopIteration)  # unused directly
    app.dependency_overrides[get_ingestion_service] = _override_get_ingestion_service
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()