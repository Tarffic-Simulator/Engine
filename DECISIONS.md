<!-- markdownlint-disable -->

# Decisiones Arquitectónicas — Motor de Simulación de Tráfico CDMX

## ADR-001: Estructura de capas en hexagonal (Arquitectura de Puertos y Adaptadores)

### Contexto
El código prototipo tiene lógica de simulación NaSch, carga de datos OSMnx, semáforos y visualización mezclados en notebooks y scripts. Necesitamos exponer esta funcionalidad como servicio web para ser consumida por otras aplicaciones.

### Decisión
Adoptar **arquitectura hexagonal (Ports & Adapters)** con capas claramente definidas:

```
src/traffic_engine/
├── domain/                    # Núcleo de negocio — sin dependencias externas
├── application/               # Casos de uso y orquestación
├── infrastructure/            # Adaptadores hacia servicios externos
└── api/                      # Controladores web (FastAPI)
```

### Razones
- **Testabilidad**: núcleo de dominio independiente de frameworks
- **Flexibilidad**: reemplazar proveedores de datos sin afectar simulación  
- **Extensibilidad**: futuras funciones (ML, optimización) sin romper contratos
- **Separación clara**: lógica de negocio vs. detalles técnicos

### Consecuencias
- Requiere definir interfaces/protocolos entre capas
- Más archivos iniciales, pero mayor mantenibilidad a largo plazo

---

## ADR-002: Dominio NaSch como máquina de estados con interfaz Gymnasium-like

### Contexto
El modelo NaSch actual está fuertemente acoplado con NetworkX y datos geográficos. Necesitamos abstraerlo para facilitar futuros reemplazos del modelo de simulación (ML, microsimulación avanzada, etc).

### Decisión
Crear abstracción **SimulationModel** con interfaz inspirada en Gymnasium:

```python
class SimulationModel(Protocol):
    def reset(self, topology: TopologyData) -> SimulationState
    def step(self, actions: Optional[Dict]) -> Tuple[SimulationState, Metrics, bool]
    def get_observation(self) -> ObservationData
```

La implementación concreta `NaSchSimulationModel` mantendrá la lógica actual pero será intercambiable.

### Razones
- **Desacoplamiento**: la simulación no depende de detalles de carga de datos
- **Futuro ML**: interfaz compatible con agentes de aprendizaje reforzado
- **Testabilidad**: simulaciones pueden usar datos sintéticos
- **Flexibilidad**: diferentes modelos (NaSch, microsimulación, híbridos)

### Consecuencias
- Requiere definir estructuras de datos claras (TopologyData, SimulationState)
- Abstracción adicional puede ser overkill inicialmente, pero facilita evolución

---

## ADR-003: FastAPI como web service framework

### Contexto
Necesitamos exponer el motor de simulación vía API REST para consumo por otras aplicaciones (dashboard, optimización, análisis).

### Decisión
Usar **FastAPI** para la capa API web:

```python
# Endpoints principales:
POST   /simulations/                    # Crear nueva simulación
GET    /simulations/{id}/               # Estado actual
PUT    /simulations/{id}/step           # Avanzar N ticks
PUT    /simulations/{id}/reset          # Reiniciar con nuevos parámetros
GET    /simulations/{id}/metrics        # Métricas agregadas
GET    /simulations/{id}/snapshot       # Estado detallado para visualización
DELETE /simulations/{id}/               # Limpiar recursos
```

### Razones
- **Performance**: FastAPI + uvicorn para concurrencia async
- **Tipado**: validación automática con Pydantic models
- **Documentación**: OpenAPI/Swagger generado automáticamente
- **Ecosistema**: compatible con deployment moderno (Docker, Kubernetes)

### Consecuencias
- Dependencia en asyncio (compatible con simulaciones grandes)
- Requiere manejo de estado por simulación (UUID-based)

---

## ADR-004: Providers desacoplados para datos geográficos y semáforos

### Contexto
La fuente de datos topológicos (OSMnx) y ubicación/configuración de semáforos (inferida por centralidad) son puntos de acoplamiento que pueden cambiar.

### Decisión
Abstraer fuentes de datos detrás de interfaces:

```python
class TopologyProvider(Protocol):
    def load_area(self, area: str) -> TopologyData
    def load_bbox(self, bbox: BoundingBox) -> TopologyData

class TrafficLightProvider(Protocol):
    def get_lights(self, topology: TopologyData) -> List[TrafficLight]
    def update_config(self, light_id: str, config: LightConfig) -> None
```

Implementaciones iniciales:
- `OSMnxTopologyProvider`: usa current logic  
- `CentralityTrafficLightProvider`: inferencia por betweenness centrality
- Futuras: `RealDataTrafficLightProvider`, `DatabaseTopologyProvider`

### Razones
- **Flexibilidad**: cambiar fuente de datos sin tocar simulación
- **Testing**: providers mock para pruebas rápidas
- **Evolución**: integrar datos reales cuando estén disponibles
- **Cacheable**: topologías grandes se pueden persistir

### Consecuencias  
- Más interfaces a definir y mantener
- Conversión de datos entre formatos (NetworkX ↔ estructuras internas)

---

## ADR-005: Gestión de estado por simulación con UUID

### Contexto
El servicio web debe manejar múltiples simulaciones concurrentes, cada una con su propio estado.

### Decisión
**Simulation Manager** con simulaciones identificadas por UUID:

```python
@dataclass
class SimulationSession:
    id: UUID
    model: SimulationModel
    topology: TopologyData
    lights: List[TrafficLight]
    created_at: datetime
    last_accessed: datetime
    tick: int = 0

class SimulationManager:
    def create_simulation(self, config: SimulationConfig) -> UUID
    def get_session(self, sim_id: UUID) -> SimulationSession
    def step_simulation(self, sim_id: UUID, n_ticks: int) -> StepResult
    def cleanup_expired(self, ttl_minutes: int) -> None
```

### Razones
- **Concurrencia**: múltiples clientes pueden tener simulaciones activas
- **Aislamiento**: errores en una simulación no afectan otras
- **Recursos**: limpieza automática de simulaciones inactivas
- **Escalabilidad**: patrón compatible con distribución futura

### Consecuencias
- Consumo de memoria proporcional al número de simulaciones activas
- Requiere estrategia de limpieza (TTL, LRU)

---

## ADR-006: Métricas y observaciones separadas por propósito

### Contexto
Los consumidores del API tienen diferentes necesidades: dashboards (visualización), optimizadores (métricas agregadas), análisis (datos brutos).

### Decisión
Separar tipos de output por caso de uso:

```python
@dataclass
class SimulationMetrics:
    """Métricas agregadas — optimizado para análisis/optimización"""
    tick: int
    total_vehicles: int
    avg_speed_kmh: float
    density: float
    throughput_veh_per_min: float
    congestion_ratio: float

@dataclass  
class SimulationSnapshot:
    """Estado detallado — optimizado para visualización"""
    tick: int
    vehicles: List[VehicleState]
    traffic_lights: List[LightState]
    edge_densities: Dict[EdgeId, float]
    edge_flows: Dict[EdgeId, int]
```

### Razones
- **Performance**: endpoints especializados evitan transferir datos innecesarios
- **Evolución**: métricas pueden añadirse sin romper visualizadores
- **Tipado**: estructuras claras facilitan integración
- **Cacheable**: diferentes TTLs según volatilidad

### Consecuencias
- Duplicación de cálculos si ambos endpoints se usan simultáneamente
- Más estructuras de datos a mantener sincronizadas

---

## ADR-007: Preservar lógica NaSch original sin modificaciones

### Contexto
El código prototipo implementa correctamente NaSch sincrónico, discretización, tipos de vehículos heterogéneos y semáforos por centralidad. Esta lógica no debe cambiar durante la migración.

### Decisión
**Refactor conservativo**:
- Extraer clases y funciones existentes sin modificar algoritmos
- Mantener parámetros de configuración idénticos (CELL_SIZE_M=5.0, V_MAX_CELLS, etc)
- Preservar comportamiento de bordes, timeout de vehículos y flujo entrada/salida
- Conservar lógica de semáforos NS/EW con offset para olas verdes

### Razones
- **Riesgo mínimo**: comportamiento verificado en prototipos
- **Validación**: comparar salidas entre versión original y migrada
- **Confianza**: stakeholders conocen comportamiento actual
- **Incremental**: refactor de arquitectura primero, optimizaciones después

### Consecuencias
- Algunas decisiones de diseño del prototipo se mantienen (eg. arrays numpy para celdas)
- Oportunidades de optimización se posponen a iteraciones futuras

---

## ADR-008: Transporte realtime con SSE y contrato de replay

### Contexto

El nuevo requisito exige transmitir ticks en tiempo real a clientes y permitir reconexion con recuperacion de historial persistido en MongoDB. Para esta iteracion la necesidad es principalmente servidor -> cliente, no un canal full-duplex.

### Decisión

Adoptar **Server-Sent Events (SSE)** como transporte realtime inicial.

Contrato de stream:

- `GET /realtime/sessions/{session_id}/stream?run_id={run_id}&from_tick={n}&follow={true|false}`
- Replay inicial con ticks persistidos donde `tick_number > from_tick`.
- Si `follow=true` y el run sigue activo, continuar con ticks en vivo.
- En estado terminal, emitir evento `run_status` y cerrar stream.

Semantica de recuperacion:

- `from_tick` por defecto `-1`.
- Si existe `Last-Event-ID` parseable, tiene prioridad sobre `from_tick`.

Regla de cursor SSE:

- El `id` de eventos usados como cursor de reconexion debe ser numerico y representar el `tick_number`.
- No usar valores textuales como cursor (`completed`, `failed`) porque rompen la precedencia de `Last-Event-ID`.

### Razones

- Ajuste directo a un flujo unidireccional de ticks.
- Menor complejidad operativa y de cliente que WebSocket para este alcance.
- Semantica natural de `event id` para reconexion y replay incremental.

### Consecuencias

- Mensajeria cliente -> servidor en tiempo real queda fuera de alcance en esta iteracion.
- Si en futuras iteraciones se requiere control bidireccional, se puede agregar WebSocket sin romper el contrato de persistencia.

---

## ADR-009: Persistencia realtime con repositorios por sesiones, ejecuciones y ticks

### Contexto

MongoDB local ya fue aprovisionado con colecciones `simulation_sessions`, `simulation_runs` y `simulation_ticks`, validadores e indices. El sistema debe soportar historial de ticks recuperable tras desconexiones.

### Decisión

Definir contratos de repositorio en la capa Application y usar adaptadores Mongo en Infrastructure.

Repositorios requeridos:

- `SimulationSessionRepository` para metadatos y estado de sesion.
- `SimulationRunRepository` para intentos de ejecucion y estados terminales.
- `SimulationTickRepository` para historial inmutable por tick.

Forma de almacenamiento de ticks:

- Un documento por tick en `simulation_ticks`.
- Prohibido almacenar historial en arrays crecientes dentro de `simulation_sessions`.
- Idempotencia de escritura por indice unico `run_id + tick_number`.

Orden de escritura y publicacion:

1. Persistir tick en MongoDB.
2. Actualizar `latest_tick` y `latest_metrics` en sesion.
3. Publicar tick a suscriptores realtime.

### Razones

- Evita anti-patron de arrays no acotados y riesgo del limite de 16MB por documento.
- Favorece replay ordenado y reintentos idempotentes por run.
- Se alinea con el esquema e indices ya provisionados.

### Consecuencias

- Mayor numero de documentos de alta frecuencia en `simulation_ticks`.
- Necesidad de politicas futuras de archivado o retencion si el volumen crece.

---

## ADR-010: Ejecucion en background in-process con puerto compatible con workers

### Contexto

En local/dev el despliegue actual es un proceso FastAPI unico. El requisito pide ejecucion en background y una ruta de evolucion a workers dedicados en el futuro.

### Decisión

Usar un **RunExecutor** como puerto de Application.

- Implementacion inicial: `InProcessRunExecutor` basado en tareas `asyncio` dentro del proceso FastAPI.
- API crea sesion/run y despacha ejecucion sin bloquear request.
- `RunRealtimeSessionUseCase` maneja loop de ticks, persistencia, publicacion y transiciones de estado.

Coordinacion de capa API:

1. Endpoint de creacion valida parametros y llama `StartRealtimeSessionUseCase`.
2. Use case persiste sesion y run en estado inicial.
3. Use case delega al `RunExecutor` el inicio del run en background.
4. Endpoint SSE llama `ReplayAndStreamTicksUseCase` para replay + follow.

Ubicacion de conexion MongoDB por entorno:

- Se mantiene en `src/traffic_engine/infrastructure/persistence/mongodb.py`.
- API y Application no leen variables de entorno de Mongo directamente.

### Razones

- Cumple alcance local/dev sin introducir infraestructura de colas en esta iteracion.
- Mantiene desacople para migrar a workers sin cambiar contratos de API ni use cases.
- Conserva ownership de configuracion Mongo en Infrastructure.

### Consecuencias

- En reinicio del proceso, tareas activas in-process se pierden y deben reconciliarse en arranque.
- Para produccion multi-proceso sera necesario reemplazar el adaptador por uno distribuido.

### Estado de cierre PIPELINE-011 (2026-04-24)

- `InProcessRunExecutor` se mantiene como adaptador por defecto para local/dev.
- La ruta de reemplazo worker-backed queda movida a backlog explicito de una iteracion futura.
- Este diferido no bloquea el cierre del alcance realtime actual porque el puerto `RunExecutor` ya preserva el desacople entre capas.

---

## ADR-011: Excepcion transitoria por reutilizacion de SimulationManager legacy

### Estado actual (2026-04-24)

Esta ADR queda resuelta como deuda historica: `manager_backed_simulation_model.py` ya no depende de `api/simulation_manager.py` y ahora usa el contrato `SimulationRuntimeGateway` en Application.

### Contexto

La implementacion actual del adaptador realtime `manager_backed_simulation_model.py` reutiliza `api/simulation_manager.py` para no duplicar logica de creacion y step de simulaciones legacy.

### Opciones consideradas

1. Mover inmediatamente `SimulationManager` fuera de API hacia Application/Infrastructure y actualizar todos los consumidores.
2. Mantener la dependencia actual como puente temporal mientras se define un puerto de runtime en Application.

### Decision

Aceptar temporalmente la opcion 2 como deuda arquitectonica registrada, con refactor obligatorio posterior para restaurar la regla de capas (Infrastructure no depende de API).

### Razones

- Minimiza riesgo funcional durante la entrega inicial realtime.
- Evita bloqueo inmediato sobre endpoints legacy sincronos.
- Permite planificar una extraccion de puerto de runtime con pruebas de regresion dedicadas.

### Consecuencias

- Existe una violacion temporal de direccion de dependencias entre capas.
- El reemplazo futuro del runtime por workers requiere resolver primero esta deuda.
- Debe priorizarse un plan corto de refactor para eliminar el acoplamiento antes de ampliar funcionalidad realtime.

---

## Decisiones Tecnológicas

### Stack elegido

- **Lenguaje**: Python 3.11+
- **Web Framework**: FastAPI + Uvicorn
- **Simulación**: NumPy + NetworkX (preservar stack actual)
- **Validación**: Pydantic v2  
- **Geografía**: OSMnx + Shapely (mantener compatibilidad)
- **Testing**: pytest + fixtures para topologías sintéticas
- **Packaging**: Poetry para gestión de dependencias

### No elegido y por qué

- **Flask**: FastAPI superior para APIs tipadas y async
- **Django**: overkill para un servicio de simulación especializado
- **Go/Rust**: requiere reescribir lógica numérica ya validada
- **GraphQL**: REST más simple para casos de uso actuales
