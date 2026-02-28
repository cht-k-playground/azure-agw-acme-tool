"""Azure Functions HTTP trigger for ACME HTTP-01 challenge responses.

Serves the key authorization string for ACME HTTP-01 domain validation.
The challenge response is stored in the ``ACME_CHALLENGE_RESPONSE``
Application Setting and written there by the CLI before triggering
the ACME CA validation.

Route: GET /.well-known/acme-challenge/{token}
"""

from __future__ import annotations

import logging
import os

import azure.functions as func

logger = logging.getLogger(__name__)

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.route(route=".well-known/acme-challenge/{token}", methods=["GET"])
def acme_challenge_responder(req: func.HttpRequest) -> func.HttpResponse:
    """Return the ACME HTTP-01 challenge key authorization.

    Reads the ``ACME_CHALLENGE_RESPONSE`` environment variable and returns
    its value as ``text/plain``.  Returns HTTP 404 when the variable is not
    set or is empty.

    Parameters
    ----------
    req:
        The incoming HTTP request.  The ``{token}`` path parameter is
        present but not used — the single ``ACME_CHALLENGE_RESPONSE``
        setting covers the current active challenge.

    Returns
    -------
    func.HttpResponse
        HTTP 200 with the key authorization body, or HTTP 404.
    """
    challenge_response = os.environ.get("ACME_CHALLENGE_RESPONSE", "")

    if not challenge_response:
        logger.warning("ACME_CHALLENGE_RESPONSE is not set or empty; returning 404.")
        return func.HttpResponse(status_code=404)

    logger.info("Serving ACME challenge response.")
    return func.HttpResponse(
        body=challenge_response,
        status_code=200,
        mimetype="text/plain",
    )
