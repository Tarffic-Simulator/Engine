---
name: traffic-engine-tests
description: 'Run and inspect this project\'s pytest suite. Use when: execute tests, run pytest, collect test information, list tests, inspect failures, run coverage, run markers, run a specific test file, or summarize test results for the Engine traffic simulation project.'
argument-hint: 'Qué quieres ejecutar: suite completa, marker, archivo, filtro -k, collect-only o cobertura'
---

# Traffic Engine Tests

Usa esta skill cuando necesites ejecutar los tests de este repositorio y devolver un resumen útil de los resultados, no solo la salida cruda de `pytest`.

## Objetivo

- Ejecutar la suite completa o una porción acotada de los tests del proyecto.
- Obtener información accionable: tests recolectados, aprobados, fallidos, omitidos, errores, duración y cobertura cuando aplique.
- Elegir el comando correcto según el tipo de consulta: suite, marker, archivo, filtro `-k`, `collect-only` o cobertura.

## Contexto del proyecto

- La configuración base de `pytest` está en `pytest.ini`.
- La suite vive en `tests/`.
- Los markers válidos incluyen `unit`, `integration`, `api`, `domain`, `providers`, `simulation` y `slow`.
- Hay comandos documentados en `TEST_COVERAGE.md` para suite completa, markers, archivos y filtros `-k`.

## Procedimiento

1. Ubícate en la raíz del repositorio.
2. Determina el alcance pedido por el usuario:
   - Suite completa
   - Un marker
   - Un archivo de test
   - Un filtro `-k`
   - Solo recolección de tests
   - Cobertura
3. Elige el ejecutor:
   - Si existe `.venv/`, prefiere `.venv/bin/python -m pytest`.
   - Si no, usa `python -m pytest`.
4. Ejecuta el comando más pequeño que responda la petición.
5. Resume el resultado con información estructurada, no con un volcado completo del terminal.
6. Si hubo fallos o errores de colección, identifica el punto exacto y el motivo corto.

## Comandos canónicos

### Suite completa

```bash
.venv/bin/python -m pytest tests/ -v
```

### Cobertura

```bash
.venv/bin/python -m pytest tests/ --cov=src/traffic_engine --cov-report=html
```

### Markers

```bash
.venv/bin/python -m pytest -m "domain" tests/
.venv/bin/python -m pytest -m "api" tests/
.venv/bin/python -m pytest -m "simulation" tests/
```

### Por archivo

```bash
.venv/bin/python -m pytest tests/test_physical_config.py
.venv/bin/python -m pytest tests/test_domain_models.py
.venv/bin/python -m pytest tests/test_nasch_simulation.py
.venv/bin/python -m pytest tests/test_providers.py
.venv/bin/python -m pytest tests/test_use_cases.py
.venv/bin/python -m pytest tests/test_api_layer.py
```

### Por filtro `-k`

```bash
.venv/bin/python -m pytest -k "speed_conversion" tests/
.venv/bin/python -m pytest -k "traffic_light" tests/
.venv/bin/python -m pytest -k "nasch_rules" tests/
.venv/bin/python -m pytest -k "api_validation" tests/
```

### Solo información de recolección

```bash
.venv/bin/python -m pytest tests/ --collect-only -q
```

## Formato de respuesta

Siempre devuelve un resumen compacto con estos campos cuando existan:

- Alcance ejecutado
- Comando utilizado
- Total de tests recolectados
- `passed`, `failed`, `skipped`, `errors`, `xfailed`, `xpassed`
- Duración total
- Archivos o markers implicados
- Si hubo fallos: nombre de cada test fallido y motivo corto
- Si hubo errores de colección o importación: archivo afectado y excepción corta
- Si hubo cobertura: porcentaje global y ubicación del reporte HTML

## Reglas de decisión

- Si el usuario pide "qué tests existen" o "qué cubre la suite", usa `--collect-only -q` antes de ejecutar la suite completa.
- Si el usuario menciona un dominio funcional como API, simulación o providers, prioriza `-m` o el archivo de test más cercano.
- Si el usuario menciona una función, regla o comportamiento puntual, prioriza `-k`.
- Si el usuario reporta un fallo en un archivo concreto, ejecuta primero ese archivo.
- Si el usuario pide cobertura, no sustituyas la ejecución normal por `collect-only`.

## Criterio de cierre

La tarea queda completa cuando:

- Se ejecutó el comando mínimo suficiente para responder la petición.
- El resumen permite entender rápidamente el estado de la suite.
- Los fallos, si existen, quedan localizados por test o por archivo.
- No se devuelve salida cruda innecesaria si una síntesis basta.