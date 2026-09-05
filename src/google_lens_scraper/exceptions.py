"""Exceptions hierarchy for google-lens-scraper."""


class LensError(Exception):
    """Base exception for all Google Lens Scraper errors."""

    def __init__(
        self, message: str, status_code: int | None = None, response_body: str | None = None
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body

    def __str__(self) -> str:
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message


class LensRateLimitError(LensError):
    """Raised when Google blocks requests or serves a CAPTCHA / 429 /sorry/index challenge."""


class LensParseError(LensError):
    """Raised when parsing Lens visual matches or response data fails."""


class LensNetworkError(LensError):
    """Raised when an HTTP or browser network request fails."""


class LensImageError(LensError):
    """Raised when an input image cannot be read, decoded, or prepared."""


class LensConfigurationError(LensError):
    """Raised when configuration parameters or credentials are invalid."""
