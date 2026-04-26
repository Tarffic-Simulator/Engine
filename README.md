# Motor de Simulación de Tráfico CDMX

Simulador de tráfico urbano basado en autómatas celulares (modelo Nagel-Schreckenberg) para la Ciudad de México.

## Estado del Proyecto

### Implementado

- Motor NaSch con topologías OSM y semáforos configurables en `src/traffic_engine/`
- API HTTP de simulación síncrona con FastAPI
- Sesiones realtime persistidas con ejecución en segundo plano, replay/follow por WebSocket canónico y compatibilidad SSE
- Persistencia MongoDB para `simulation_sessions`, `simulation_runs` y `simulation_ticks`
- Docker Compose local para el stack de desarrollo
- Suite de pruebas para dominio, API, contratos realtime, persistencia y payloads lane-aware

### Alcance Activo del Repositorio

| Superficie | Estado | Nota |
| --- | --- | --- |
| Core de simulación | Activo | Dominio NaSch, topología, reglas multicarril y semáforos |
| API FastAPI | Activa | Endpoints síncronos y realtime sobre el mismo núcleo de dominio |
| Persistencia realtime | Activa | MongoDB y repositorios para sesiones, runs y ticks |
| Cliente visual integrado | Fuera de alcance | Los consumidores externos deben usar la API pública documentada en `docs/CONSUME_SERVICE.md` |

### Trabajo Futuro

1. Sustituir el ejecutor local en proceso por un adaptador worker-backed sin cambiar el contrato `RunExecutor`.
2. Definir reconciliación de runs activos ante reinicios de proceso o despliegues distribuidos.
3. Reducir deuda de compatibilidad Pydantic v2 en esquemas realtime.

## Estructura del Proyecto

```text
src/traffic_engine/                # Motor limpio para producción
├── domain/                        # Lógica NaSch + entidades
├── application/                   # Casos de uso + contratos
├── infrastructure/                # Adaptadores OSMnx, MongoDB, runtime y streaming
└── api/                           # API FastAPI síncrona + realtime

docs/                              # Guías operativas y de consumo
tests/                             # Suite de regresión para core, API y realtime
docker/mongo/                      # Soporte local para MongoDB
```

## Funcionalidades Clave

### Simulación NaSch

- **4 reglas sincrónicas**: aceleración, frenado, ruido estocástico, movimiento
- **Discretización realista**: celdas de 5.0 m y velocidades hasta 60 km/h
- **Tipos de vehículo**: carro, bus y moto con comportamientos diferenciados
- **Flujo dinámico**: vehículos entran y salen por nodos frontera

### Red Vial CDMX

- **Datos reales**: OpenStreetMap vía OSMnx
- **Topología**: `MultiDiGraph` dirigido con velocidades por arista
- **Escalabilidad**: desde colonias hasta áreas urbanas extensas

### Sistema de Semáforos

- **Ubicación configurable**: proveedores fijos o por centralidad
- **Fases NS/EW**: definidas por orientación geográfica de las calles
- **Olas verdes**: offset configurable entre semáforos adyacentes

### API REST y Realtime

- **Simulaciones múltiples**: gestión concurrente por UUID con `SimulationManager`
- **Métricas en tiempo real**: velocidad, densidad, throughput y congestión
- **Snapshots detallados**: posiciones de vehículos, estado de semáforos y payload lane-aware
- **Sesiones realtime**: creación, ejecución en background, persistencia, replay y follow
- **Consumo externo**: clientes HTTP/WebSocket sobre contratos públicos, sin frontend activo dentro del repositorio

## Documentación Arquitectónica

- **[DECISIONS.md](DECISIONS.md)**: decisiones de diseño activas para core y API
- **[WORK_PLAN.md](WORK_PLAN.md)**: backlog operativo actual y slices de validación
- **[ARCHITECTURE.md](ARCHITECTURE.md)**: arquitectura fuente de verdad del repositorio
- **[PIPELINES.md](PIPELINES.md)**: workflows de desarrollo y pipeline actual
- **[docs/CONSUME_SERVICE.md](docs/CONSUME_SERVICE.md)**: ejemplos Python para consumir la API HTTP/WebSocket

## Desarrollo Local

### API REST y runtime realtime

```bash
cd /home/erick/Desktop/github/Engine
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
cp .env.example .env
docker compose up -d mongodb
uvicorn traffic_engine.api.app:app --reload
# -> http://localhost:8000/docs
```

Endpoints principales:

| Método | Ruta | Propósito |
| --- | --- | --- |
| `POST` | `/simulations` | Crear simulación síncrona |
| `POST` | `/simulations/{simulation_id}/step` | Avanzar ticks |
| `GET` | `/simulations/{simulation_id}/metrics` | Leer métricas agregadas |
| `GET` | `/simulations/{simulation_id}/snapshot` | Leer snapshot detallado |
| `POST` | `/realtime/sessions` | Crear sesión realtime persistida |
| `POST` | `/realtime/sessions/{session_id}/runs` | Extender una sesión finalizada con un nuevo run |
| `GET` | `/realtime/sessions/{session_id}/ticks` | Leer historial persistido de ticks |
| `GET` | `/realtime/sessions/{session_id}/ws` | Replay y follow WebSocket canónico por `run_id` |
| `GET` | `/realtime/sessions/{session_id}/stream` | Compatibilidad SSE para clientes heredados |

Para ejemplos de consumo por clientes externos, ver `docs/CONSUME_SERVICE.md` y `docs/API.md`.

## Stack Tecnológico

### Núcleo y runtime

- **Python 3.8+**
- **NumPy**: arrays para celdas y cálculos vectorizados
- **NetworkX**: representación del grafo vial `MultiDiGraph`
- **OSMnx**: descarga y procesamiento OpenStreetMap
- **PyMongo**: persistencia de sesiones realtime y ticks

### Servicio y calidad

- **FastAPI**: framework web async con tipado
- **Pydantic**: validación y serialización de contratos API
- **uvicorn**: servidor ASGI para desarrollo local
- **pytest**: test suite para dominio, API y realtime
- **setuptools**: packaging definido en `pyproject.toml`

## Contribución

El proyecto sigue un pipeline estructurado con agentes especializados para decisiones, TDD e implementación.

Ver [PIPELINES.md](PIPELINES.md) para el workflow y [docs/INDEX.md](docs/INDEX.md) para la documentación operativa actual.
