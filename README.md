# Ubuntu Agent Node

A small HTTP service that runs an agent profile and persistent conversation history on an Ubuntu host. It exposes an OpenAPI-described endpoint that another platform can call if that platform supports registering custom HTTP tools.

## iLands connection status

This service provides the Ubuntu side of the connection. It does **not** make a native iLands agent call the service by itself. iLands' public BYOA documentation describes connecting a local Codex or Claude Code runtime into iLands; I could not find public documentation for registering an arbitrary Ubuntu HTTP endpoint as a tool for a native iLander. The iLands side will need an official custom-tool/API registration path before direct calls can work.

The service is therefore ready for an iLands integration, but the iLands registration step remains unverified. Do not treat an undocumented private endpoint as a supported integration.

This is a local recreation with a new profile and local memory. It does not copy an iLands agent's private instructions, model, memories, relationships, or account state. Populate `data/agent_profile.md` only with information you can access and are allowed to use.

## What it exposes

- `GET /health` — unauthenticated health check for a reverse proxy.
- `POST /v1/agent/run` — run the local agent; requires `Authorization: Bearer <NODE_API_TOKEN>`.
- `GET /v1/agent/sessions/{session_id}` — read one local conversation; requires the same bearer token.
- `GET /openapi.json` — OpenAPI schema for tool registration.

Example request:

```http
POST /v1/agent/run
Authorization: Bearer <NODE_API_TOKEN>
Content-Type: application/json

{
  "message": "Summarize the latest project update"
}
```

The first call creates a session and returns its `session_id`. Send that ID on later turns to continue the same local conversation:

```json
{
  "session_id": "00000000-0000-0000-0000-000000000000",
  "message": "What should I do next?"
}
```

## Ubuntu deployment outline

1. Install Python 3.11+ and an inference service that exposes an OpenAI-compatible Chat Completions endpoint. The endpoint and model name are configured in `/etc/ilands-agent-node.env`.
2. Copy this project to `/opt/ilands-agent-node`; create a virtual environment and install `requirements.txt`.
3. Create the `agentnode` Linux user and writable data directory `/var/lib/ilands-agent-node`.
4. Copy `.env.example` to `/etc/ilands-agent-node.env`. Set a new random `NODE_API_TOKEN`, `MODEL_BASE_URL`, and `MODEL_NAME`.
5. Copy `data/agent_profile.md` to `/etc/ilands-agent-node/agent_profile.md` and edit the profile. Ensure the `agentnode` user can read it.
6. Install `deploy/ilands-agent-node.service` as `/etc/systemd/system/ilands-agent-node.service`, then enable and start the service.
7. Set a DNS name for the Ubuntu host, replace `agent.example.com` in `deploy/Caddyfile`, and configure Caddy to proxy HTTPS traffic to `127.0.0.1:8080`.
8. Allow inbound HTTPS (and HTTP if needed for certificate issuance) in the host firewall. Keep port `8080` private; only the reverse proxy should reach it.
9. Register `https://<your-domain>/openapi.json` and the bearer token through an official iLands custom-tool integration if iLands provides one for your agent.

The service listens on loopback through the included systemd unit. The reverse proxy is the public entry point. Keep the API token secret and rotate it if it is exposed.

## Local development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set the variables in `.env`, then start the service:

```bash
set -a
. ./.env
set +a
uvicorn app.main:app --host 127.0.0.1 --port 8080
```

API documentation is available at `http://127.0.0.1:8080/docs` while the service is running.
