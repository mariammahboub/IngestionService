VALID = {"sensor_id": "sensor-cairo-01", "timestamp": "2024-01-15T10:30:00Z", "reading": 23.5}

def post(client, payload=None):
    return client.post("/api/v1/readings", json=payload or VALID)


def test_create_returns_201(client):
    assert post(client).status_code == 201

def test_duplicate_returns_409(client):
    post(client)
    assert post(client).status_code == 409

def test_unknown_sensor_returns_404(client):
    assert client.get("/api/v1/readings/sensor-unknown").status_code == 404

def test_future_timestamp_returns_422(client):
    assert post(client, {**VALID, "timestamp": "2099-01-01T00:00:00Z"}).status_code == 422