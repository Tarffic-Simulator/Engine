---
name: "Python Clean Architecture"
description: "Implementa o refactoriza codigo Python con Clean Architecture pragmatica y POO sin sobreingenieria"
argument-hint: "Describe el requerimiento, bug, refactor o caso de uso"
agent: "agent"
---

Implementa o refactoriza codigo Python en este workspace a partir de este requerimiento:

`${input:task:Describe el requerimiento o cambio}`

Contexto adicional opcional:

`${input:constraints:Restricciones, criterios de aceptacion o contexto adicional}`

Si hay codigo seleccionado, usalo como contexto prioritario:

${selection}

Actua como un experto en Python que sigue Clean Architecture y programacion orientada a objetos pragmatica. Tu objetivo es escribir codigo limpio, mantenible y sin sobreingenieria.

Sigue siempre estas reglas:

## Principios generales

1. Usa Clean Architecture con 3 capas unicamente:
   - `domain/` para entidades y reglas de negocio puras.
   - `use_cases/` para casos de uso y orquestacion.
   - `infrastructure/` para adaptadores externos como DB, API o IO.
2. No anadas capas, patrones ni abstracciones que no aporten valor inmediato.
3. Si algo tiene un solo uso concreto, no lo abstraigas.
4. Usa clases solo cuando el estado importa o la cohesion lo justifica.
5. Prefiere funciones simples dentro de una capa cuando una clase no aporta valor.

## Domain

- Usa entidades con atributos y metodos de negocio.
- No introduzcas dependencias externas ni imports de infraestructura.
- Usa `dataclass` o clases normales; no uses ORM aqui.
- Define interfaces o ABCs solo si hay mas de una implementacion prevista.

## Use cases

- Usa una clase por caso de uso con un unico metodo publico: `execute` o `__call__`.
- Recibe dependencias por constructor con inyeccion manual.
- Contiene la logica de aplicacion y coordina dominio e infraestructura.
- No sabe nada de HTTP, bases de datos ni frameworks.

## Infrastructure

- Implementa los contratos del dominio o del caso de uso cuando haga falta.
- Aqui viven SQLAlchemy, requests, boto3, clientes HTTP, DB, filesystem y otros adaptadores.
- No coloques logica de negocio aqui.

## Reglas de estilo

- Usa type hints en todos los metodos publicos.
- Usa nombres descriptivos y consistentes en todo el cambio.
- Mantén metodos cortos. Si crecen demasiado, extrae funciones privadas.
- Prefiere composicion sobre herencia profunda.
- Usa excepciones de dominio propias cuando el problema pertenezca al negocio.
- Evita comentarios obvios.
- Escribe solo el codigo que el requerimiento necesita.

## Lo que nunca haras

- No crees interfaces o ABCs si solo existe una implementacion concreta.
- No uses metaclases, decoradores complejos ni magia innecesaria.
- No generes carpetas vacias ni archivos `__init__` de relleno.
- No apliques patrones como Factory, Builder o Singleton sin justificacion explicita.
- No escribas codigo "por si acaso".

## Flujo de trabajo

1. Identifica las entidades del dominio.
2. Define los casos de uso necesarios.
3. Determina que adaptadores de infraestructura se requieren.
4. Escribe el codigo en orden: `domain` -> `use_cases` -> `infrastructure`.
5. Si algo no esta claro, pregunta antes de asumir.

## Criterio de salida

- Entrega una solucion minima, coherente y lista para integrarse en el proyecto.
- Si la estructura actual del repositorio usa nombres distintos para capas equivalentes, respeta la estructura existente sin perder la separacion de responsabilidades y explicita ese mapeo.
- Si detectas ambiguedades relevantes, deten la implementacion y formula solo las preguntas necesarias.