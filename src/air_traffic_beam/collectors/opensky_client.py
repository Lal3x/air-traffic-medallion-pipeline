"""Cliente HTTP resiliente para a API pública da OpenSky Network."""

from __future__ import annotations

import logging
from typing import Any

import requests
from tenacity import RetryCallState, retry, stop_after_attempt, wait_exponential

from air_traffic_beam.config.settings import Settings
from air_traffic_beam.exceptions import (
    OpenSkyRateLimitError,
    OpenSkyRequestError,
    OpenSkyResponseError,
)

logger = logging.getLogger(__name__)


class OpenSkyClient:
    """Consulta estados de aeronaves para a entrada da camada Bronze.

    O cliente valida a resposta e aplica retries, mas não normaliza os vetores;
    essa responsabilidade pertence à transformação Bronze → Silver.
    """

    def __init__(self, settings: Settings):
        """Inicializa o cliente com URL, limites geográficos e timeout."""
        self.settings = settings
        self.session = requests.Session()

    @property
    def base_url(self) -> str:
        return str(self.settings.opensky_api_base_url).rstrip("/")

    def _build_params(self) -> dict[str, float]:
        """Monta os parâmetros geográficos do endpoint `states/all`."""
        return {
            "lamin": self.settings.opensky_lat_min,
            "lomin": self.settings.opensky_lon_min,
            "lamax": self.settings.opensky_lat_max,
            "lomax": self.settings.opensky_lon_max,
        }

    def _handle_response(self, response: requests.Response) -> dict[str, Any]:
        """Valida HTTP e JSON, levantando erros específicos da OpenSky."""
        if response.status_code == 429:
            retry_after = response.headers.get(
                "X-Rate-Limit-Retry-After-Seconds"
            ) or response.headers.get("Retry-After")
            raise OpenSkyRateLimitError(
                f"OpenSky rate limit exceeded. Retry-After={retry_after or 'unknown'}"
            )

        if response.status_code >= 400:
            raise OpenSkyResponseError(
                f"OpenSky request failed with status {response.status_code}: {response.text[:200]}"
            )

        try:
            payload = response.json()
        except ValueError as exc:  # pragma: no cover - defensive guard
            raise OpenSkyResponseError(
                "OpenSky response did not contain valid JSON"
            ) from exc

        if not isinstance(payload, dict):
            raise OpenSkyResponseError("OpenSky response is not a JSON object")

        if "time" not in payload:
            raise OpenSkyResponseError("OpenSky response is missing the 'time' field")

        states = payload.get("states")
        if states is None:
            payload["states"] = []
        elif not isinstance(states, list):
            raise OpenSkyResponseError(
                "OpenSky response 'states' field must be a list or null"
            )

        return payload

    def get_states(self) -> dict[str, Any]:
        """Consulta a API com retry para timeout, conexão e respostas 5xx."""
        url = f"{self.base_url}/states/all"
        params = self._build_params()

        @retry(
            retry=retry_if_transient,
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=5),
            reraise=True,
        )
        def request() -> dict[str, Any]:
            try:
                response = self.session.get(
                    url,
                    params=params,
                    timeout=self.settings.opensky_request_timeout_seconds,
                )
                logger.info(
                    "OpenSky request status=%s remaining=%s",
                    response.status_code,
                    response.headers.get("X-Rate-Limit-Remaining"),
                )
                return self._handle_response(response)
            except requests.exceptions.Timeout as exc:
                raise OpenSkyRequestError("timeout na requisição da OpenSky") from exc
            except requests.exceptions.ConnectionError as exc:
                raise OpenSkyRequestError("conexão com a OpenSky falhou") from exc

        return request()


def retry_if_transient(retry_state: RetryCallState) -> bool:
    """Informa ao Tenacity quais falhas são temporárias e repetíveis."""
    if retry_state.outcome is None:
        return False
    exc = retry_state.outcome.exception()
    if isinstance(exc, OpenSkyRateLimitError):
        return False
    if isinstance(exc, OpenSkyResponseError):
        return exc.args[0].startswith("OpenSky request failed with status 5")
    return bool(isinstance(exc, OpenSkyRequestError))
