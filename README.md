# Motor de Simulación de Tráfico CDMX

Simulador de tráfico urbano basado en autómatas celulares (modelo Nagel-Schreckenberg) para la Ciudad de México.

## Estado del Proyecto

### Implementado

- Motor NaSch con topologías OSM y semáforos configurables en `src/traffic_engine/`
- API HTTP de simulación síncrona con FastAPI
- Sesiones realtime con ejecución en segundo plano, persistencia MongoDB y replay/follow por SSE
- Docker Compose local para MongoDB con colecciones e índices de `simulation_sessions`, `simulation_runs` y `simulation_ticks`
- Suite de pruebas para dominio, API, contratos realtime y persistencia

### Trabajo Futuro

1. Sustituir el ejecutor local en proceso por un adaptador worker-backed sin cambiar el contrato `RunExecutor`.
2. Definir reconciliación de runs activos ante reinicios de proceso o despliegues distribuidos.
3. Reducir deuda de compatibilidad Pydantic v2 en esquemas realtime.

## Estructura del Proyecto

### Código Prototipo (preservado)

```text
core/
├── grafo_vial_cdmx.ipynb          # Carga datos OSMnx topología CDMX
├── 02_automata_celular.ipynb      # Modelo NaSch + discretización
├── 03_semaforos.ipynb             # Sistema semáforos por centralidad
├── 06_sim_mejorada.py             # Tipos vehículos heterogéneos
├── 07_flujo_entrada_salida.py     # Flujo boundary + timeout
└── dashboard.py                   # Dashboard Streamlit interactivo
```

### Arquitectura Actual

```text
src/traffic_engine/                # Motor limpio para producción
├── domain/                        # Lógica NaSch + entidades
├── application/                   # Casos de uso + orquestación
├── infrastructure/                # Adaptadores OSMnx, MongoDB, runtime y streaming
└── api/                           # API FastAPI síncrona + realtime
```

## Funcionalidades Clave

### Simulación NaSch

- **4 reglas sincrónicas**: aceleración, frenado, ruido estocástico, movimiento
- **Discretización realista**: celdas 5.0m, velocidades hasta 60 km/h
- **Tipos vehículos**: carro/bus/moto con comportamientos diferenciados
- **Flujo dinámico**: vehículos entran/salen por nodos frontera

### Red Vial CDMX

- **Datos reales**: OpenStreetMap vía OSMnx
- **Topología**: MultiDiGraph dirigido con velocidades por arista
- **Escalabilidad**: desde colonias (~2k nodos) hasta ciudad completa (~150k)

### Sistema de Semáforos

- **Ubicación inteligente**: por betweenness centrality de intersecciones
- **Fases NS/EW**: según orientación geográfica de calles
- **Olas verdes**: offset configurable entre semáforos adyacentes

### API REST y Realtime

- **Simulaciones múltiples**: gestión concurrente por UUID con `SimulationManager`
- **Métricas en tiempo real**: velocidad, densidad, throughput y congestión
- **Snapshots detallados**: posiciones de vehículos y estado de semáforos
- **Sesiones realtime**: creación de sesión, ejecución en background y stream SSE con recuperación

## Documentación Arquitectónica

- **[DECISIONS.md](DECISIONS.md)**: Decisiones de diseño y justificaciones técnicas
- **[WORK_PLAN.md](WORK_PLAN.md)**: Plan detallado de migración y estructura de archivos
- **[ARCHITECTURE.md](ARCHITECTURE.md)**: Visión general y patrones arquitectónicos
- **[PIPELINES.md](PIPELINES.md)**: Workflows de desarrollo y pipeline actual
- **[docs/CONSUME_SERVICE.md](docs/CONSUME_SERVICE.md)**: Guía detallada para consumir la API desde clientes Python, incluyendo SSE realtime

## Desarrollo

### Código Prototipo (actual)

```bash
cd core/
source .venv/bin/activate

# Simulación básica
python 06_sim_mejorada.py

# Con flujo entrada/salida  
python 07_flujo_entrada_salida.py

# Dashboard interactivo
streamlit run dashboard.py
```

### API REST y realtime

```bash
cd /home/erick/Desktop/github/Engine
uvicorn traffic_engine.api.app:app --reload
# → http://localhost:8000/docs
```

Endpoints principales:

| Método | Ruta | Propósito |
| --- | --- | --- |
| `POST` | `/simulations` | Crear simulación síncrona |
| `POST` | `/simulations/{simulation_id}/step` | Avanzar ticks |
| `GET` | `/simulations/{simulation_id}/metrics` | Leer métricas agregadas |
| `GET` | `/simulations/{simulation_id}/snapshot` | Leer snapshot detallado |
| `POST` | `/realtime/sessions` | Crear sesión realtime persistida |
| `GET` | `/realtime/sessions/{session_id}/stream` | Replay y follow SSE por `run_id` |

Para ejecutar la ruta realtime localmente también necesitas MongoDB:

```bash
cp .env.example .env
docker compose up -d mongodb
```

## Stack Tecnológico

### Preservado del prototipo

- **Python 3.8+**
- **NumPy**: arrays para celdas y cálculos vectorizados
- **NetworkX**: representación grafo vial MultiDiGraph
- **OSMnx**: descarga y procesamiento OpenStreetMap
- **Matplotlib**: visualización estática simulaciones

### Nuevo para arquitectura limpia

- **FastAPI**: framework web async con tipado
- **Pydantic**: validación y serialización datos API
- **PyMongo**: persistencia de sesiones realtime y ticks
- **setuptools**: packaging definido en `pyproject.toml`
- **pytest**: testing framework con fixtures

## Contribución

Proyecto sigue pipeline estructurado con agentes especializados:

1. **Python Software Architect**: Decisiones arquitectónicas y planificación
2. **Python TDD**: Generación test suite comprehensive
3. **Python Architect**: Implementación siguiendo TDD

Ver [PIPELINES.md](PIPELINES.md) para detalles del workflow y [docs/INDEX.md](docs/INDEX.md) para la documentación operativa actual.
