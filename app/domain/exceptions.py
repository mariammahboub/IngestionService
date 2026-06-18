class DuplicateReadingError(Exception):
    pass

class SensorNotFoundError(Exception):
    def __init__(self, sensor_id: str):
        self.sensor_id = sensor_id
        super().__init__(f"No readings found for sensor '{sensor_id}'.")


class ReadingPersistenceError(Exception):
    def __init__(self, cause: Exception):
        self.cause = cause
        super().__init__(f"Failed to persist reading: {cause}")