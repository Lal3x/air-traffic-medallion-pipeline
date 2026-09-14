class OpenSkyRequestError(RuntimeError):
    """Raised when OpenSky request execution fails."""


class OpenSkyRateLimitError(OpenSkyRequestError):
    """Raised when the API responds with HTTP 429."""


class OpenSkyResponseError(OpenSkyRequestError):
    """Raised when the API response is malformed."""


class OpenSkyConfigurationError(ValueError):
    """Raised when required settings are invalid."""
