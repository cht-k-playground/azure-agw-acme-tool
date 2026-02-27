"""Logging configuration for az-acme-tool.

Provides :func:`setup_logging` as the single entry point that configures two
handlers on the Python root logger:

- A :class:`JsonLinesFormatter`-backed :class:`logging.FileHandler` writing
  structured records to ``~/.config/az-acme-tool/logs/az-acme-tool.log``.
- A :class:`RichConsoleHandler` that prints human-readable output to stderr
  via :class:`rich.console.Console`.

.. note::
    This module is named ``logging.py`` inside the ``az_acme_tool`` package.
    To avoid shadowing the standard-library ``logging`` module *within this
    file*, the stdlib module is imported as the very first statement (before
    any package-relative code is executed).  At the point of import Python's
    import system resolves ``logging`` to the stdlib module because the package
    itself has not yet been added to the lookup path under that name.
"""

# Import stdlib logging FIRST — before any relative or package imports — so
# that CPython's import machinery resolves it to the standard library and not
# to this file itself.
import json
import logging as _logging
from datetime import UTC, datetime
from pathlib import Path

from rich.console import Console

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOG_DIR: Path = Path("~/.config/az-acme-tool/logs").expanduser()
_LOG_FILE: Path = _LOG_DIR / "az-acme-tool.log"

# ---------------------------------------------------------------------------
# Custom formatter
# ---------------------------------------------------------------------------


class JsonLinesFormatter(_logging.Formatter):
    """Format each log record as a single-line JSON object.

    Output fields:
    - ``timestamp``: ISO 8601 UTC string (e.g. ``"2024-01-01T00:00:00.000000Z"``)
    - ``level``: uppercase level name (e.g. ``"INFO"``)
    - ``message``: the formatted log message string
    """

    def format(self, record: _logging.LogRecord) -> str:
        """Return the record formatted as a JSON Lines string."""
        # Use UTC timestamp
        ts = datetime.fromtimestamp(record.created, tz=UTC).isoformat()
        # Ensure the timestamp ends with 'Z' (replace '+00:00' suffix)
        if ts.endswith("+00:00"):
            ts = ts[:-6] + "Z"
        payload = {
            "timestamp": ts,
            "level": record.levelname,
            "message": record.getMessage(),
        }
        return json.dumps(payload)


# ---------------------------------------------------------------------------
# Rich console handler
# ---------------------------------------------------------------------------


class RichConsoleHandler(_logging.Handler):
    """A :class:`logging.Handler` that emits plain text to stderr via Rich.

    Messages are printed with :meth:`rich.console.Console.print` without any
    JSON wrapping.  Level filtering is delegated to the root logger so this
    handler always emits whatever records reach it.
    """

    def __init__(self) -> None:
        super().__init__(level=_logging.DEBUG)
        self._console: Console = Console(stderr=True)

    def emit(self, record: _logging.LogRecord) -> None:
        """Print the log record as a plain text message to stderr."""
        try:
            msg = self.format(record)
            self._console.print(msg)
        except Exception:
            self.handleError(record)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def setup_logging(verbose: bool) -> None:
    """Configure application-wide logging.

    Creates the log directory if it does not exist, attaches a JSON Lines file
    handler and a Rich console handler to the root logger, and sets the root
    logger level to ``DEBUG`` when *verbose* is ``True`` or ``INFO`` otherwise.

    Parameters
    ----------
    verbose:
        When ``True`` the root logger level is set to ``logging.DEBUG``;
        otherwise it is set to ``logging.INFO``.
    """
    # Ensure the log directory exists
    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = _logging.getLogger()

    # Set root level first so handlers receive the right records
    root.setLevel(_logging.DEBUG if verbose else _logging.INFO)

    # Remove any existing handlers to avoid duplicate output on repeated calls
    # (e.g. during tests)
    root.handlers.clear()

    # File handler with JSON Lines formatting
    file_handler = _logging.FileHandler(_LOG_FILE, encoding="utf-8")
    file_handler.setLevel(_logging.DEBUG)
    file_handler.setFormatter(JsonLinesFormatter())
    root.addHandler(file_handler)

    # Rich console handler (stderr)
    console_handler = RichConsoleHandler()
    root.addHandler(console_handler)
