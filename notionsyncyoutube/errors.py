class ConfigError(RuntimeError):
    """Raised when local configuration is missing or invalid."""


class ApiError(RuntimeError):
    """Raised when an external API request fails."""
