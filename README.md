# az-acme-tool

Azure Application Gateway ACME automated certificate management tool.

## Overview

`az-acme-tool` is a CLI tool that automates SSL/TLS certificate management on Azure Application Gateway using the ACME protocol (HTTP-01 validation), reducing manual maintenance costs and human error risks.

## Installation

```bash
pip install az-acme-tool
```

Or from source:

```bash
git clone https://github.com/your-org/az-acme-tool.git
cd az-acme-tool
pip install -e .
```

## Quick Start

```bash
# Initialize ACME account
az-acme-tool init --email admin@example.com

# Issue certificates for all configured gateways
az-acme-tool issue --config config.yaml

# Check certificate status
az-acme-tool status --config config.yaml

# Renew expiring certificates (within 30 days)
az-acme-tool renew --config config.yaml
```

## Commands

| Command   | Description                                      |
|-----------|--------------------------------------------------|
| `init`    | Initialize ACME account and generate config template |
| `issue`   | Issue and deploy certificates                    |
| `renew`   | Renew expiring certificates                      |
| `status`  | Query certificate status and expiry information  |
| `cleanup` | Clean up temporary ACME challenge routing rules  |

## Configuration

```yaml
acme:
  email: security@example.com
  ca_url: https://acme-v02.api.letsencrypt.org/directory
  account_key_path: ~/.config/az-acme-tool/account.key

azure:
  subscription_id: "12345678-1234-1234-1234-123456789abc"
  acme_function_fqdn: "acme-responder.azurewebsites.net"

gateways:
  - name: production-agw
    resource_group: production-rg
    domains:
      - domain: www.example.com
        cert_store: agw_direct
```

## Requirements

- Python 3.11+
- Azure credentials (via `az login`, Service Principal, or Managed Identity)
- Azure Application Gateway with public IP
- Azure Function deployed as ACME HTTP-01 challenge responder

## Development

```bash
pip install -e ".[dev]"
pytest
```
