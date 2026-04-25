# Traffic Engine Development Guide

## Audience

This guide is for developers onboarding to the repository and maintainers making changes to the API, simulation model, or providers.

## Quick Start

```bash
cd /home/erick/Desktop/github/Engine
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Run the API

```bash
uvicorn traffic_engine.api.app:app --reload
```

Open `http://127.0.0.1:8000/docs` for the generated OpenAPI UI.

## Run Local MongoDB

```bash
cp .env.example .env
docker compose up -d mongodb
```

See `docs/MONGODB_LOCAL.md` for the collection design, connection variables, and validation details.

## Run Realtime Locally

```bash
cp .env.example .env
docker compose up -d mongodb
uvicorn traffic_engine.api.app:app --reload
```

Use `POST /realtime/sessions` to create a session and the returned `stream_url` to consume SSE recovery or follow mode.

## Run Tests

| Goal | Command |
| --- | --- |
| Full suite | `pytest tests/ -v` |
| Coverage | `pytest tests/ --cov=src/traffic_engine --cov-report=html` |
| API slice | `pytest tests/test_api_layer.py -v` |
| Simulation slice | `pytest tests/test_nasch_simulation.py -v` |
| Use-case slice | `pytest tests/test_use_cases.py -v` |

## Repository Shape

| Path | What Lives There |
| --- | --- |
| `src/traffic_engine/api/` | FastAPI app, public schemas, sync manager, and realtime router |
| `src/traffic_engine/application/` | Contracts and use-case orchestration |
| `src/traffic_engine/domain/` | Domain models and NaSch simulation engine |
| `src/traffic_engine/infrastructure/` | OSMnx graph loading, Mongo persistence, runtime, realtime broker, and traffic-light providers |
| `tests/` | Contract and behavior tests |
| `core/` | Prototype notebooks and scripts kept for reference |
| Root `*.md` files | Earlier planning, ADRs, coverage, and migration notes |

## Development Conventions

| Convention | Current Practice |
| --- | --- |
| Architecture | Keep business logic in `domain`, orchestration in `application`, adapters in `infrastructure`, HTTP in `api` |
| Public API contracts | Use Pydantic request/response models in `api/models` |
| Internal use-case contracts | Use dataclass DTOs and protocols in `application/contracts` |
| Simulation abstractions | Program against `SimulationModel` and provider protocols when possible |
| Physical constants | Keep defaults centralized in `src/traffic_engine/config/constants.py` |
| Optional heavy libs | Guard OSMnx and NetworkX imports inside infrastructure modules |

## Tooling and Config

| Tool | Source |
| --- | --- |
| Packaging | `pyproject.toml` with setuptools backend |
| Python baseline | `>=3.8` |
| Formatting | `black` and `isort` settings in `pyproject.toml` |
| Typing | strict `mypy` settings in `pyproject.toml` |
| Test discovery | `pytest.ini` and `[tool.pytest.ini_options]` in `pyproject.toml` |

## Useful Markers

| Marker | Meaning |
| --- | --- |
| `unit` | Small isolated tests |
| `integration` | Cross-component tests |
| `api` | API layer tests |
| `domain` | Domain model and logic tests |
| `providers` | Provider and adapter tests |
| `simulation` | NaSch simulation tests |
| `slow` | Longer-running tests |

## Practical Notes

| Topic | Note |
| --- | --- |
| OSM-backed simulation creation | Requires OSMnx dependencies and network access |
| Synchronous session lifecycle | `SimulationManager` keeps in-memory instances for `/simulations` routes only |
| Realtime session lifecycle | `/realtime` persists session, run, and tick state in MongoDB and replays ticks over SSE |
| Local realtime runtime | The default local/dev adapter is `InProcessRunExecutor`; it is intentionally replaceable |
| Prototype parity | Root planning docs aim to preserve prototype behavior while moving code into `src/traffic_engine` |

## Reading Order

1. `README.md`
2. `docs/ARCHITECTURE.md`
3. `docs/API.md`
4. `docs/SIMULATION.md`
5. `DECISIONS.md`
