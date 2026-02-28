"""Tests for the Azure Function ACME HTTP-01 challenge responder.

The Azure Functions SDK is mocked so no real Azure Functions runtime is
required.  Tests verify the HTTP trigger logic in isolation.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from typing import Any
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FUNCTION_APP_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "azure-function",
    "function_app.py",
)


def _load_function_app(mock_af: Any) -> Any:
    """Load azure-function/function_app.py with a custom azure.functions mock."""
    # Remove cached module to force fresh import
    for key in list(sys.modules.keys()):
        if "function_app" in key:
            del sys.modules[key]

    with patch.dict(sys.modules, {"azure.functions": mock_af, "azure": MagicMock()}):
        spec = importlib.util.spec_from_file_location("function_app", _FUNCTION_APP_PATH)
        assert spec is not None
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        return module


def _make_mock_af(response_cls: type[Any]) -> MagicMock:
    """Build a minimal azure.functions mock with a custom HttpResponse class."""
    mock_af = MagicMock()
    mock_af.AuthLevel.ANONYMOUS = "ANONYMOUS"
    mock_af.FunctionApp.return_value = MagicMock()
    mock_af.HttpRequest = MagicMock
    mock_af.HttpResponse = response_cls
    return mock_af


def _make_mock_request(token: str = "test-token") -> MagicMock:
    req = MagicMock()
    req.route_params = {"token": token}
    return req


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAcmeChallengeResponder:
    def test_returns_200_with_correct_body_and_mimetype(self) -> None:
        """HTTP 200 with key authorization body and text/plain when ACME_CHALLENGE_RESPONSE is set."""
        key_auth = "TOKEN.KEY_AUTH_VALUE"
        req = _make_mock_request(token="TOKEN")
        captured: dict[str, Any] = {}

        class FakeHttpResponse:
            def __init__(
                self,
                body: str = "",
                status_code: int = 200,
                mimetype: str = "text/plain",
            ) -> None:
                captured["body"] = body
                captured["status_code"] = status_code
                captured["mimetype"] = mimetype

        mock_af = _make_mock_af(FakeHttpResponse)

        with (
            patch.dict(sys.modules, {"azure.functions": mock_af, "azure": MagicMock()}),
            patch.dict("os.environ", {"ACME_CHALLENGE_RESPONSE": key_auth}),
        ):
            module = _load_function_app(mock_af)
            module.acme_challenge_responder(req)

        assert captured["body"] == key_auth
        assert captured["status_code"] == 200
        assert captured["mimetype"] == "text/plain"

    def test_returns_404_when_env_var_not_set(self) -> None:
        """HTTP 404 when ACME_CHALLENGE_RESPONSE is not set in the environment."""
        req = _make_mock_request()
        captured: dict[str, Any] = {}

        class FakeHttpResponse:
            def __init__(self, status_code: int = 200, **kwargs: Any) -> None:
                captured["status_code"] = status_code

        mock_af = _make_mock_af(FakeHttpResponse)

        # Build an environment dict without ACME_CHALLENGE_RESPONSE
        clean_env = {k: v for k, v in os.environ.items() if k != "ACME_CHALLENGE_RESPONSE"}

        with (
            patch.dict(sys.modules, {"azure.functions": mock_af, "azure": MagicMock()}),
            patch.dict("os.environ", clean_env, clear=True),
        ):
            module = _load_function_app(mock_af)
            module.acme_challenge_responder(req)

        assert captured["status_code"] == 404

    def test_returns_404_when_env_var_is_empty_string(self) -> None:
        """HTTP 404 when ACME_CHALLENGE_RESPONSE is set to an empty string."""
        req = _make_mock_request()
        captured: dict[str, Any] = {}

        class FakeHttpResponse:
            def __init__(self, status_code: int = 200, **kwargs: Any) -> None:
                captured["status_code"] = status_code

        mock_af = _make_mock_af(FakeHttpResponse)

        with (
            patch.dict(sys.modules, {"azure.functions": mock_af, "azure": MagicMock()}),
            patch.dict("os.environ", {"ACME_CHALLENGE_RESPONSE": ""}),
        ):
            module = _load_function_app(mock_af)
            module.acme_challenge_responder(req)

        assert captured["status_code"] == 404
