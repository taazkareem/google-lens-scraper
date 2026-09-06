"""Unit tests for exceptions hierarchy."""

from google_lens_pro.exceptions import (
    LensConfigurationError,
    LensError,
    LensImageError,
    LensNetworkError,
    LensParseError,
    LensRateLimitError,
)


def test_exception_inheritance():
    assert issubclass(LensRateLimitError, LensError)
    assert issubclass(LensParseError, LensError)
    assert issubclass(LensNetworkError, LensError)
    assert issubclass(LensImageError, LensError)
    assert issubclass(LensConfigurationError, LensError)


def test_exception_formatting():
    err = LensError("General failure", status_code=500)
    assert str(err) == "[500] General failure"

    err_no_code = LensError("General failure")
    assert str(err_no_code) == "General failure"
