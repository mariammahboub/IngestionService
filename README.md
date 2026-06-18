# Environmental Metrics Ingestion Service

A lightweight FastAPI service that acts as the main entry point for
environmental readings sent by external sensors, validating each reading and
persisting it to a database. Built with a clean, layered architecture so the
storage backend can be swapped without touching the business logic.

---

## Quick Start

### Prerequisites
- Python 3.11+
- pip

### Installation

```bash
git clone https://github.com/<your-username>/ingestion-service.git
cd ingestion-service

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### Run the service

```bash
uvicorn app.main:app --reload
```

The service starts at `http://localhost:8000`.

| URL | Description |
|-----|-------------|
| `http://localhost:8000/docs` | Interactive Swagger UI |
| `http://localhost:8000/redoc` | ReDoc documentation |
| `http://localhost:8000/health` | Health check |

### Configuration (optional)

The service runs out of the box with sane defaults. To override them, copy
`.env.example` to `.env`:

```env
DATABASE_URL=sqlite:///./sensor_data.db
DEBUG=False
APP_NAME=Environmental Metrics Ingestion Service
```

---

## API Reference

### `POST /api/v1/readings`

Ingest a single sensor reading.

**Request body**

```json
{
  "sensor_id": "sensor-cairo-01",
  "timestamp": "2024-01-15T10:30:00Z",
  "reading": 23.5
}
```

| Field | Type | Rules |
|-------|------|-------|
| `sensor_id` | string | 1–128 characters, not blank/whitespace |
| `timestamp` | ISO 8601 datetime | Must include a timezone; cannot be in the future; normalized to UTC |
| `reading` | float | A finite number (no NaN or Infinity) |

**Responses**

`201 Created` — reading stored
```json
{
  "id": 1,
  "sensor_id": "sensor-cairo-01",
  "timestamp": "2024-01-15T10:30:00Z",
  "reading": 23.5,
  "received_at": "2024-01-15T10:30:01.123456Z"
}
```

`409 Conflict` — a reading for this sensor + timestamp already exists (ingestion is idempotent)
```json
{ "detail": "Reading for sensor 'sensor-cairo-01' at 2024-01-15 10:30:00+00:00 already exists." }
```

`422 Unprocessable Entity` — validation failed
```json
{
  "detail": "Request validation failed.",
  "errors": [
    {
      "field": "body -> timestamp",
      "message": "Value error, timestamp cannot be in the future",
      "type": "value_error"
    }
  ]
}
```

`500 Internal Server Error` — storage failure (logged in full server-side; a safe generic message is returned)
```json
{ "detail": "A storage error occurred. The operation could not be completed." }
```

### `GET /api/v1/readings/{sensor_id}`

Return readings for one sensor, newest first.

| Query param | Type | Default | Rules |
|-------------|------|---------|-------|
| `limit` | integer | 100 | 1–1000 |

```bash
curl http://localhost:8000/api/v1/readings/sensor-cairo-01?limit=10
```

**Responses**

`200 OK` — list of readings
```json
[
  {
    "id": 2,
    "sensor_id": "sensor-cairo-01",
    "timestamp": "2024-01-15T11:00:00Z",
    "reading": 24.1,
    "received_at": "2024-01-15T11:00:01.456789Z"
  }
]
```

`404 Not Found` — no readings exist for this sensor
```json
{ "detail": "No readings found for sensor 'sensor-cairo-01'." }
```

`422 Unprocessable Entity` — invalid `limit` (outside 1–1000)

### `GET /health`

```json
{ "status": "ok", "service": "Environmental Metrics Ingestion Service", "version": "1.0.0" }
```

---

## Running Tests

```bash
pytest                                       # full suite
pytest tests/unit/                           # unit tests — no DB, runs in milliseconds
pytest tests/integration/                    # integration tests — in-memory SQLite, full HTTP path
pytest --cov=app --cov-report=term-missing   # with coverage
```

Unit tests exercise the service against an in-memory fake repository (business
rules in isolation). Integration tests use FastAPI's `TestClient` against an
in-memory SQLite database, confirming status codes, validation, and wiring end
to end.

---

## Database Schema

```sql
CREATE TABLE sensor_readings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sensor_id   VARCHAR(128)  NOT NULL,
    timestamp   DATETIME      NOT NULL,   -- client-reported time (normalized to UTC)
    reading     FLOAT         NOT NULL,
    received_at DATETIME      NOT NULL,   -- server-set ingestion time (UTC)

    CONSTRAINT uq_sensor_timestamp UNIQUE (sensor_id, timestamp)
);

CREATE INDEX ix_sensor_id_timestamp ON sensor_readings (sensor_id, timestamp);
```

**`UNIQUE (sensor_id, timestamp)`** makes ingestion idempotent. A sensor retry
or a duplicated network packet is rejected at the database level (returned as
409) instead of creating a duplicate row. Correctness is enforced by the
database, not by application logic that could be bypassed.

**`timestamp` vs `received_at`** — `timestamp` is what the sensor claims;
`received_at` is when the server actually stored it. Sensors with drifted
clocks, delayed networks, or offline buffering can send old timestamps. Storing
both lets that drift be measured later without ever losing the original reading
time. Timestamps are normalized to UTC on ingestion so all readings sit on a
single, comparable clock.

**Composite index on `(sensor_id, timestamp)`** matches the dominant query —
"readings for sensor X over a time range" — and serves it in a single index
scan. An index on `sensor_id` alone would still scan every row for that sensor.

**`VARCHAR(128)`** keeps the identifier bounded: faster to index and compare,
and a guard against a client accidentally sending an oversized value. The cap
matches the API-layer validation.

---

## Architecture

```
app/
├── domain/          Pure Python — entities and exceptions. No frameworks.
├── schemas/         Pydantic DTOs — the wire contract (validation + serialization).
├── db/              SQLAlchemy model and session/engine setup.
├── repositories/    All database access, hidden behind a Protocol interface.
├── services/        Business logic. No HTTP, no SQL — just use-case orchestration.
├── api/             FastAPI routes + dependency injection.
└── core/            Config, logging, and global exception handlers.
```

Each layer only depends on the one beneath it: the API depends on the Service,
the Service depends on the Repository *interface*, and only the repository
implementation touches SQLAlchemy. Swapping SQLite for Postgres means rewriting
one file.

### How errors are handled

Every error type becomes an HTTP response in exactly one place (the global
handlers in `app/core/exception_handlers.py`), so routes stay thin and behavior
is consistent across the whole API.

| Situation | Status | Response |
|-----------|--------|----------|
| Invalid / malformed input | 422 | Flattened list of which field failed and why |
| Sensor has no readings | 404 | "No readings found for sensor X" |
| Duplicate submission | 409 | "Reading already exists…" |
| Database failure | 500 | Safe generic message (cause logged server-side) |
| Anything unexpected | 500 | Safe generic message, full stack trace logged |

The repository rolls back the transaction on every failure path, so a failed
write never leaves the session in a broken state. Internal error details are
logged for operators but never returned to the client.

---

## Scaling: 10 → 10,000 Sensors @ 1 reading/sec

10 sensors ≈ 10 writes/sec — trivial for this design. 10,000 sensors ≈ 10,000
writes/sec sustained, which a single FastAPI process writing synchronously to
SQLite cannot handle (SQLite serializes writes — one at a time). Changes in
order of impact:

1. **Decouple ingestion from storage with a message queue** (Kafka, Kinesis,
   RabbitMQ). The API validates and publishes, then returns `202 Accepted`
   immediately; separate consumer workers write to the database. A slow database
   creates backpressure in the queue instead of dropping API requests, and
   traffic spikes are absorbed naturally.
2. **Replace SQLite with a write-optimized store** — a time-series database such
   as TimescaleDB, InfluxDB, or managed Amazon Timestream, built for many small
   timestamped writes and fast range queries, with concurrent writers.
3. **Batch writes in the consumers** — buffer for a short window (e.g. 100 ms or
   500 rows) and issue one bulk `INSERT`, dropping per-row overhead by an order
   of magnitude.
4. **Scale the API horizontally** — once its only job is "validate + publish" it
   is stateless, so run many instances behind a load balancer.
5. **Use async I/O** (`asyncpg`, async SQLAlchemy) so one process can hold
   thousands of in-flight requests without blocking on I/O.
6. **Batch at the edge** — if sensors or gateways can send one request every few
   seconds carrying several readings, request volume drops proportionally with
   no backend change.
7. **Add observability** — request rate, error rate, queue depth, and consumer
   lag with alerting, so backpressure is caught before it becomes data loss.

The current layering makes steps 1 and 2 localized: swap the repository
implementation and the `DATABASE_URL`; the service, schemas, and routes are
untouched.

---

## Assumptions

- **Timestamp meaning** — `timestamp` is when the sensor *took* the reading, not
  when it arrived. Both it and the server-set `received_at` are stored.
- **UTC normalization** — timestamps are converted to UTC on ingestion and
  always returned as ISO 8601 with a `Z` suffix, so readings from different
  offsets are directly comparable.
- **Duplicates** — the same `sensor_id` + `timestamp` is treated as a duplicate
  regardless of the `reading` value; the first write wins. This keeps retries
  safe and unambiguous.
- **Timezone required** — naive timestamps are rejected, because storing them in
  a multi-region system causes silent, hard-to-debug query errors.
- **Not-found behavior** — querying a sensor with no stored readings returns a
  404 with a clear message, rather than an empty body, so the caller knows the
  sensor is unknown.
- **Float precision** — `reading` is a standard IEEE 754 float. A use case
  needing exact precision would switch to `DECIMAL`/`NUMERIC`.
- **No authentication** — the service is assumed to sit inside a trusted network
  behind a gateway. API keys / JWT would be the first addition before public
  exposure.
- **SQLite for this exercise** — single-writer by design. The architecture is
  built so swapping it for Postgres/TimescaleDB changes only `db/session.py` and
  the `DATABASE_URL`.

---

## Project Structure

```
ingestion-service/
├── app/
│   ├── domain/
│   │   ├── entities.py                     # SensorReading dataclass (frozen)
│   │   └── exceptions.py                   # Duplicate / NotFound / Persistence errors
│   ├── schemas/
│   │   └── sensor_reading.py               # SensorReadingIn / SensorReadingOut
│   ├── db/
│   │   ├── models.py                       # ORM model + constraints/index
│   │   └── session.py                      # engine, SessionLocal, get_db, Base
│   ├── repositories/
│   │   └── sensor_reading_repository.py    # Protocol + SQLAlchemy implementation
│   ├── services/
│   │   └── ingestion_service.py            # business logic + logging
│   ├── api/
│   │   ├── routes.py                       # endpoints (thin)
│   │   └── dependencies.py                 # dependency injection
│   ├── core/
│   │   ├── config.py                       # pydantic-settings
│   │   ├── logging.py                      # structured logging to stdout
│   │   └── exception_handlers.py           # global error → HTTP mapping
│   └── main.py                             # app factory, startup wiring
├── tests/
│   ├── unit/                               # service logic, no database
│   └── integration/                        # full HTTP path, in-memory DB
├── requirements.txt
├── pytest.ini
├── .env.example
├── .gitignore
└── README.md
```
