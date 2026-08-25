# Twemp backend

FastAPI service that owns the hierarchical multi-agent incident-response workflow: 1 Incident
Commander, 4 sub-orchestrators, and 12 specialists, with a mandatory human approval gate before
any remediation.

Deterministic application code controls phase transitions, parallel fan-out, event ordering, and
approval. Agent providers supply bounded reasoning only.

## Requirements

- Python 3.11 or newer (developed against 3.13)

## Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

On macOS or Linux use `.venv/bin/python` instead of `.\.venv\Scripts\python.exe`.

## Run

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

- API: `http://127.0.0.1:8000`
- Interactive docs: `http://127.0.0.1:8000/docs`
- Health probe: `http://127.0.0.1:8000/health`

The service starts in deterministic demo mode and needs no credentials.

## Quality gates

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m pytest
```

The `tests/` suite covers schema constraints, the agent hierarchy, orchestration ordering, the
human approval gate, fail-closed paths, the secret guard, the run store, settings, providers, and
the HTTP contract.

`tests/test_contract_fixtures.py` validates the shared `contract-fixtures/` payloads that the
frontend test suite also parses, so a contract change cannot silently break the UI. Regenerate
them after an intentional contract change:

```powershell
.\.venv\Scripts\python.exe scripts\export_contract_fixtures.py
```

## Configuration

Copy `.env.example` to `.env` to override defaults.

| Variable | Default | Purpose |
| --- | --- | --- |
| `AGENT_PROVIDER` | `demo` | `demo` for deterministic fixtures, `openai` for live reasoning |
| `OPENAI_API_KEY` | empty | Required only when `AGENT_PROVIDER=openai` |
| `OPENAI_MODEL` | `gpt-5.4` | Model used by the OpenAI provider |
| `OPENAI_AGENTS_TRACING` | `false` | Opt in to trace export |
| `CORS_ALLOW_ORIGINS` | localhost:3000 | Comma-separated frontend origins |

Live model reasoning needs the optional dependency:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-openai.txt
```

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/workflows` | Start a run and execute to the approval boundary (`201`) |
| `GET` | `/api/workflows/{run_id}` | Fetch a stored run |
| `POST` | `/api/workflows/{run_id}/decision` | Record the one human decision |
| `GET` | `/health` | Liveness and provider mode |

Responses are camelCase and errors use `{"error": string, "details"?: string[]}`.
A repeated decision on a settled approval returns `409`.

## Layout

```text
app/
  main.py                  App factory, CORS, contract-preserving error handlers
  config.py                Environment-driven settings
  api/
    routes.py              Workflow endpoints
    dependencies.py        Injected provider and repository
  workflow/
    schemas.py             Pydantic contract (source of truth)
    catalog.py             17-agent hierarchy
    engine.py              Orchestration, concurrency, approval gate
    provider.py            Reasoning protocol
    demo_provider.py       Deterministic fixtures
    openai_provider.py     Opt-in OpenAI Agents SDK provider
    provider_factory.py    Provider selection
    repository.py          Bounded in-memory run store
    security.py            Secret-like content guardscripts/                   Contract fixture export and manual smoke checktests/                     pytest suite (engine + HTTP contract)
```

## Reference-app boundaries

- Run storage is in-memory and process-local.
- Authentication and approver authorization are not included.
- Remediation events are simulations, not infrastructure actions.
- Production needs durable state, transactional decisions, idempotency, audited tool adapters,
  real evidence connectors, provider timeouts, and evals.
