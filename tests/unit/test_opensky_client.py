import pytest
import requests

from air_traffic_beam.collectors.opensky_client import OpenSkyClient
from air_traffic_beam.config.settings import Settings
from air_traffic_beam.exceptions import (
    OpenSkyConfigurationError,
    OpenSkyRateLimitError,
    OpenSkyRequestError,
    OpenSkyResponseError,
)


@pytest.fixture
def settings():
    return Settings(
        opensky_api_base_url="https://opensky-network.org/api",
        opensky_lat_min=-24.2,
        opensky_lon_min=-47.2,
        opensky_lat_max=-22.7,
        opensky_lon_max=-45.5,
        opensky_request_timeout_seconds=30,
        opensky_interval_seconds=60,
        opensky_max_collections=5,
        bronze_base_path="data/bronze",
    )


def test_get_states_uses_expected_query_and_returns_payload(settings, requests_mock):
    requests_mock.get(
        "https://opensky-network.org/api/states/all",
        json={
            "time": 123,
            "states": [
                [
                    "icao",
                    "ABC123",
                    "BR",
                    1,
                    2,
                    -46.0,
                    -23.0,
                    1000.0,
                    False,
                    0,
                    0,
                    0,
                    None,
                    1100.0,
                    "1234",
                    False,
                    0,
                    1,
                ]
            ],
        },
        headers={"X-Rate-Limit-Remaining": "10"},
    )

    client = OpenSkyClient(settings)
    response = client.get_states()

    assert response["time"] == 123
    assert response["states"][0][0] == "icao"
    assert requests_mock.request_history[0].qs == {
        "lamin": ["-24.2"],
        "lomin": ["-47.2"],
        "lamax": ["-22.7"],
        "lomax": ["-45.5"],
    }


def test_timeout_is_handled(settings, requests_mock):
    requests_mock.get(
        "https://opensky-network.org/api/states/all",
        exc=requests.exceptions.Timeout,
    )

    with pytest.raises(OpenSkyRequestError, match="timeout"):
        OpenSkyClient(settings).get_states()


def test_connection_error_is_handled(settings, requests_mock):
    requests_mock.get(
        "https://opensky-network.org/api/states/all",
        exc=requests.exceptions.ConnectionError,
    )

    with pytest.raises(OpenSkyRequestError, match="conexão"):
        OpenSkyClient(settings).get_states()


def test_http_500_is_retried(settings, requests_mock):
    requests_mock.get(
        "https://opensky-network.org/api/states/all",
        [
            {"status_code": 500, "text": "server error"},
            {"status_code": 200, "json": {"time": 1, "states": []}},
        ],
    )

    response = OpenSkyClient(settings).get_states()
    assert response == {"time": 1, "states": []}
    assert len(requests_mock.request_history) == 2


def test_http_400_is_not_retried(settings, requests_mock):
    requests_mock.get(
        "https://opensky-network.org/api/states/all",
        status_code=400,
        text="bad request",
    )

    with pytest.raises(OpenSkyResponseError):
        OpenSkyClient(settings).get_states()

    assert len(requests_mock.request_history) == 1


def test_http_429_raises_rate_limit_without_immediate_retry(settings, requests_mock):
    requests_mock.get(
        "https://opensky-network.org/api/states/all",
        status_code=429,
        text="rate limited",
        headers={"Retry-After": "60"},
    )

    with pytest.raises(OpenSkyRateLimitError):
        OpenSkyClient(settings).get_states()


def test_null_states_is_converted_to_empty_list(settings, requests_mock):
    requests_mock.get(
        "https://opensky-network.org/api/states/all",
        json={"time": 42, "states": None},
    )

    response = OpenSkyClient(settings).get_states()
    assert response == {"time": 42, "states": []}


def test_invalid_configuration_raises(settings):
    with pytest.raises(OpenSkyConfigurationError):
        Settings(
            opensky_api_base_url="https://opensky-network.org/api",
            opensky_lat_min=-22.7,
            opensky_lon_min=-47.2,
            opensky_lat_max=-24.2,
            opensky_lon_max=-45.5,
            opensky_request_timeout_seconds=30,
            opensky_interval_seconds=60,
            opensky_max_collections=5,
            bronze_base_path="data/bronze",
        )
