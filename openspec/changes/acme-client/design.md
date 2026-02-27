## Context

The project currently has `config.py`, `logging.py`, `azure_gateway.py`, and `cli.py` implemented and archived. The next layer required by the `issue` and `renew` flows is an ACME protocol client. The `acme` library (from the Certbot project) provides a low-level Python implementation of RFC 8555 client-side operations. `josepy` provides the JOSE/JWK primitives needed for ACME account keys.

The ACME HTTP-01 challenge works as follows:
1. Client creates an order with the CA specifying the target domains.
2. CA returns a challenge token for each domain.
3. Client must make `http://<domain>/.well-known/acme-challenge/<token>` respond with `<token>.<key_thumbprint>` (key_authorization).
4. This project serves this response via an Azure Function (`azure-function-responder`). The token is stored in Azure Function App Settings via `AzureGatewayClient.update_function_app_settings()`.
5. Client notifies CA, CA verifies, and if successful, client finalizes with a CSR and downloads the certificate chain.

## Goals / Non-Goals

**Goals:**
- Wrap the `acme` + `josepy` libraries in a clean `AcmeClient` class with typed public methods
- Support account registration with RSA-2048 key generation and key reuse
- Implement the full HTTP-01 challenge lifecycle including polling
- Define `AcmeError` for structured exception handling
- Achieve ≥80% line coverage with no real CA calls
- Pass `mypy --strict` and `ruff` checks

**Non-Goals:**
- DNS-01 or TLS-ALPN-01 challenge types (out of scope for Phase 1)
- Multi-domain wildcard certificates
- Key rotation for existing ACME accounts
- Direct integration with `AzureGatewayClient` (that wiring lives in `cli-issue`)

## Decisions

### D1: Use `acme.client.ClientV2` directly

**Decision**: Use the official `acme` library (`acme>=2.7.0`) from the Certbot project rather than implementing RFC 8555 from scratch or using an alternative like `josepy` alone.

**Rationale**: The `acme` library is battle-tested, actively maintained, handles nonce management, JOSE signing, and retry semantics. Writing raw HTTP ACME client code would duplicate effort and risk spec compliance bugs.

**Alternative considered**: `httpx` + manual RFC 8555 implementation — rejected as high-risk and high-maintenance.

### D2: RSA-2048 account key stored on disk as PEM

**Decision**: Generate RSA-2048 account private keys and write them to `account_key_path` with mode `0o600`. Reuse the key if the file already exists.

**Rationale**: ACME account keys are long-lived credentials that must survive CLI invocations. Storing them on disk (with restricted permissions) is the standard approach used by Certbot.

**Alternative considered**: Ephemeral keys per run — rejected because the CA would create a new account on every run, which is wasteful and may trigger rate limits.

### D3: Polling via sleep loop (not async)

**Decision**: Implement `poll_until_valid()` as a synchronous sleep loop (`time.sleep(interval_seconds)`) rather than using `asyncio`.

**Rationale**: The CLI is currently synchronous (`cli.py` uses Click without async). Introducing `asyncio` at this layer would require propagating it to all callers. The `issue-flow-batch` change will address concurrency at a higher layer using `ThreadPoolExecutor`.

**Alternative considered**: `asyncio.sleep` — deferred to `issue-flow-batch`.

### D4: Exponential back-off for transient ACME errors

**Decision**: Wrap network calls in a retry decorator using exponential back-off (base 10 s, max 3 attempts) for `acme.errors.Error` subclasses that indicate transient server-side issues.

**Rationale**: Let's Encrypt enforces rate limits and occasionally returns 429/503. A simple retry avoids surfacing these as permanent failures.

### D5: `AcmeClient` does not call `AzureGatewayClient`

**Decision**: `AcmeClient` returns `(token, key_authorization)` from `get_http01_challenge()` and does not interact with Azure. The caller (`cli-issue`) is responsible for writing to Function App Settings before calling `answer_challenge()`.

**Rationale**: Keeping `AcmeClient` free of Azure dependencies enables isolated unit testing and maintains clean separation of concerns.

## Risks / Trade-offs

- **[Risk] `acme` library API changes** → Pin `acme>=2.7.0,<3.0` to avoid breaking API shifts. Monitor Certbot changelogs.
- **[Risk] Polling timeout (60 s) may be too short for slow CA propagation** → The timeout is configurable in `poll_until_valid(timeout_seconds=60)`. Callers can pass a larger value. ROADMAP acceptance criteria specifies 60 s as the default.
- **[Risk] Key file permissions are filesystem-dependent** → Use `Path.chmod(0o600)` after writing. Document that this may not be enforced on Windows (not a target platform).
- **[Trade-off] Synchronous polling blocks the thread** → Accepted for Phase 1; `issue-flow-batch` will use `ThreadPoolExecutor` to run multiple domain flows concurrently.

## Migration Plan

No migration required — this is a new module with no breaking changes to existing modules. The `cli-issue` change will wire it in.

## Open Questions

None — all decisions are resolved.
