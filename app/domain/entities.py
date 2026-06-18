from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SensorReading:
    sensor_id: str
    timestamp: datetime
    reading: float