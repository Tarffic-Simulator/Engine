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
# Decisiones Arquitectónicas — Motor de Simulación de Tráfico CDMX

Este documento conserva solo las decisiones activas del core y la API. La cronología de superficies retiradas y limpiezas históricas permanece en `CHANGELOG.md`.

## ADR-001: Arquitectura hexagonal en capas

| Aspecto | Detalle |
| --- | --- |
| Contexto | El motor combina dominio NaSch, ingestión de topología, persistencia y transporte HTTP/WebSocket. |
| Decisión | Mantener `domain`, `application`, `infrastructure` y `api` como capas separadas. |
| Consecuencias | La lógica de simulación sigue aislada de FastAPI y MongoDB; nuevas integraciones deben entrar por contratos. |

## ADR-002: Abstracción de modelo de simulación con preservación conservadora del comportamiento NaSch

| Aspecto | Detalle |
| --- | --- |
| Contexto | El comportamiento del prototipo NaSch ya está validado y no debe cambiar por una refactorización arquitectónica. |
| Decisión | Mantener una frontera de `SimulationModel`/casos de uso y preservar reglas, discretización y parámetros del motor existente. |
| Consecuencias | La evolución futura del modelo sigue siendo posible, pero cualquier cambio funcional requiere un pipeline dedicado y validación explícita. |

## ADR-003: FastAPI como frontera pública del servicio

| Aspecto | Detalle |
| --- | --- |
| Contexto | El repositorio debe exponer el motor a consumidores externos, automatización y análisis sin acoplarlos al dominio interno. |
| Decisión | Usar FastAPI como capa pública para endpoints síncronos y realtime. |
| Consecuencias | Los contratos HTTP/OpenAPI pasan a ser la superficie soportada; el manejo de estado por simulación se mantiene en el lado servidor. |

## ADR-004: Providers desacoplados para topología y semáforos

| Aspecto | Detalle |
| --- | --- |
| Contexto | La carga de topología OSM y la colocación/configuración de semáforos pueden cambiar sin que cambie el dominio. |
| Decisión | Mantener `TopologyProvider` y `TrafficLightProvider` como contratos de application con implementaciones en infrastructure. |
| Consecuencias | Se facilita testing con dobles y la sustitución de fuentes de datos o estrategias de señalización. |

## ADR-005: Gestión de simulaciones síncronas por UUID mediante `SimulationManager`

| Aspecto | Detalle |
| --- | --- |
| Contexto | La API debe manejar múltiples simulaciones activas sin mezclar su estado. |
| Decisión | Mantener un `SimulationManager` que crea, lista, avanza y elimina simulaciones identificadas por UUID. |
| Consecuencias | El aislamiento entre simulaciones queda del lado servidor y el consumo externo sigue siendo stateless salvo por el identificador público. |

## ADR-006: Separación entre métricas agregadas y snapshots detallados

| Aspecto | Detalle |
| --- | --- |
| Contexto | Los consumidores externos no siempre necesitan el mismo nivel de detalle. |
| Decisión | Mantener payloads distintos para métricas (`/metrics`) y snapshots (`/snapshot`). |
| Consecuencias | Se reduce transferencia innecesaria y la evolución de campos visuales puede seguir siendo aditiva sin romper métricas agregadas. |

## ADR-007: Persistencia realtime en tres colecciones MongoDB

| Aspecto | Detalle |
| --- | --- |
| Contexto | El historial realtime crece con rapidez y no debe terminar en documentos no acotados. |
| Decisión | Mantener `simulation_sessions`, `simulation_runs` y `simulation_ticks` como separación canónica de metadata, ejecuciones e historial por tick. |
| Consecuencias | El replay queda paginable y ordenado; la consistencia entre colecciones se vuelve una responsabilidad explícita del write path realtime. |

## ADR-008: WebSocket canónico para realtime con compatibilidad SSE

| Aspecto | Detalle |
| --- | --- |
| Contexto | El flujo realtime necesita replay más follow y un contrato público único para clientes vivos. |
| Decisión | WebSocket es el transporte canónico; SSE se mantiene solo como compatibilidad transitoria. |
| Consecuencias | La semántica de recuperación se centra en `tick_number`; los payloads públicos deben seguir usando estados normalizados y envelopes consistentes. |

## ADR-009: Ejecución en background detrás del contrato `RunExecutor`

| Aspecto | Detalle |
| --- | --- |
| Contexto | El API no debe bloquear peticiones mientras corre una sesión realtime prolongada. |
| Decisión | Mantener `RunExecutor` como puerto de application y `InProcessRunExecutor` como implementación local/dev. |
| Consecuencias | La sustitución por workers externos sigue abierta sin romper use cases ni contratos API. |

## ADR-010: Core multilane con payload lane-aware aditivo

| Aspecto | Detalle |
| --- | --- |
| Contexto | El dominio ya evolucionó a una representación multilane con cambios de carril y transporte público. |
| Decisión | Mantener ocupación 2D por arista, `lane_index` explícito, dwell de transporte público y payloads lane-aware aditivos. |
| Consecuencias | Aumenta complejidad y uso de memoria, pero la evolución visual y de replay no depende de heurísticas externas. |

## ADR-011: El alcance activo del repositorio es motor + API

| Aspecto | Detalle |
| --- | --- |
| Contexto | El repositorio ya no mantiene una superficie de UI integrada y debe evitar volver a describirla como parte activa de la arquitectura. |
| Decisión | Limitar la documentación, planificación y cobertura activas al core de simulación, FastAPI, MongoDB y contratos públicos para consumidores externos. |
| Consecuencias | Cualquier cliente visual o herramienta externa debe integrarse desde fuera del árbol del engine y apoyarse solo en `docs/API.md` y `docs/CONSUME_SERVICE.md`. |

## Decisiones Tecnológicas Activas

| Área | Stack |
| --- | --- |
| Lenguaje | Python 3.8+ |
| Web framework | FastAPI + Uvicorn |
| Simulación | NumPy + NetworkX |
| Geografía | OSMnx |
| Persistencia | PyMongo |
| Testing | pytest |
| Packaging | setuptools vía `pyproject.toml` |
- **GraphQL**: REST más simple para casos de uso actuales
