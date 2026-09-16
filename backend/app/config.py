"""FlyCast Backend Configuration."""

from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Storage paths
    DATA_DIR: str = "./data"
    EXPERIMENT_TTL_HOURS: int = 24

    # Connectome configuration
    CONNECTOME_VERSION: str = "male-cns:v1.0"
    CONNECTOME_SIGN_MODE: str = "unsigned"  # 'unsigned' or 'heuristic'
    CONNECTOME_SEED: int = 42
    INPUT_NEURONS: int = 512
    READOUT_NEURONS: int = 4096

    # Reservoir dynamics defaults
    RESERVOIR_LEAK: float = 0.25
    RESERVOIR_GAIN: float = 0.95
    INPUT_GAIN: float = 0.50

    # Dataset & simulation limits
    MAX_SIMULATION_STEPS: int = 1000
    MAX_UPLOAD_MB: int = 5
    MAX_ROWS_UPLOAD: int = 50000
    MIN_ROWS_REQUIRED: int = 100
    DEFAULT_FORECAST_HORIZON: int = 5
    MAX_FORECAST_HORIZON: int = 20

    # Job concurrency & security
    MAX_CONCURRENT_JOBS: int = 1
    RATE_LIMIT_PER_HOUR: int = 20  # per IP

    # Networking & CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    LOG_LEVEL: str = "INFO"

    # Testing / Development toggle
    USE_FIXTURE_BRAIN: bool = False

    @property
    def brain_dir(self) -> Path:
        return Path(self.DATA_DIR) / "brain"

    @property
    def experiments_dir(self) -> Path:
        return Path(self.DATA_DIR) / "experiments"


settings = Settings()
