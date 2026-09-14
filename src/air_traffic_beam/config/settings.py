"""Configuração tipada da API, caminhos das camadas e execução local."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

from air_traffic_beam.exceptions import OpenSkyConfigurationError


def _load_yaml_defaults() -> dict:
    config_path = Path(__file__).resolve().parents[2] / "config" / "settings.yaml"
    if not config_path.exists():
        return {}
    with config_path.open("r", encoding="utf-8") as file:
        loaded = yaml.safe_load(file) or {}
    return loaded if isinstance(loaded, dict) else {}


class Settings(BaseSettings):
    """Carrega defaults YAML/.env e valida a configuração da OpenSky."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    opensky_api_base_url: str = "https://opensky-network.org/api"
    opensky_lat_min: float = -24.2
    opensky_lon_min: float = -47.2
    opensky_lat_max: float = -22.7
    opensky_lon_max: float = -45.5
    opensky_request_timeout_seconds: int = 30
    opensky_interval_seconds: int = 60
    opensky_max_collections: int = 5
    bronze_base_path: Path = Path("data/bronze")
    silver_base_path: Path = Path("data/silver")
    gold_base_path: Path = Path("data/gold")
    rejected_base_path: Path = Path("data/rejected")
    observability_base_path: Path = Path("data/observability")
    log_level: str = "INFO"

    def __init__(self, **data):
        yaml_defaults = _load_yaml_defaults()
        data = {**yaml_defaults, **data}
        super().__init__(**data)
        self._validate_bounds()

    def _validate_bounds(self) -> None:
        """Rejeita coordenadas inválidas e parâmetros de execução impossíveis."""
        if not -90.0 <= self.opensky_lat_min <= 90.0:
            raise OpenSkyConfigurationError(
                f"latitude fora do intervalo válido: {self.opensky_lat_min}"
            )
        if not -90.0 <= self.opensky_lat_max <= 90.0:
            raise OpenSkyConfigurationError(
                f"latitude fora do intervalo válido: {self.opensky_lat_max}"
            )
        if self.opensky_lat_min >= self.opensky_lat_max:
            raise OpenSkyConfigurationError(
                "opensky_lat_min deve ser menor que opensky_lat_max"
            )

        if not -180.0 <= self.opensky_lon_min <= 180.0:
            raise OpenSkyConfigurationError(
                f"longitude fora do intervalo válido: {self.opensky_lon_min}"
            )
        if not -180.0 <= self.opensky_lon_max <= 180.0:
            raise OpenSkyConfigurationError(
                f"longitude fora do intervalo válido: {self.opensky_lon_max}"
            )
        if self.opensky_lon_min >= self.opensky_lon_max:
            raise OpenSkyConfigurationError(
                "opensky_lon_min deve ser menor que opensky_lon_max"
            )

        if self.opensky_request_timeout_seconds <= 0:
            raise OpenSkyConfigurationError(
                "opensky_request_timeout_seconds deve ser maior que zero"
            )
        if self.opensky_interval_seconds <= 0:
            raise OpenSkyConfigurationError(
                "opensky_interval_seconds deve ser maior que zero"
            )
        if self.opensky_max_collections <= 0:
            raise OpenSkyConfigurationError(
                "opensky_max_collections deve ser maior que zero"
            )

    @property
    def bounding_box(self) -> dict[str, float]:
        """Retorna a região em formato gravado nos metadados Bronze."""
        return {
            "lat_min": self.opensky_lat_min,
            "lon_min": self.opensky_lon_min,
            "lat_max": self.opensky_lat_max,
            "lon_max": self.opensky_lon_max,
        }


def get_settings() -> Settings:
    """Cria uma instância usando defaults YAML e variáveis de ambiente."""
    return Settings()
