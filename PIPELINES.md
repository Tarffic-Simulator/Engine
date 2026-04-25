<!-- markdownlint-disable -->

# Pipeline Registry

## PIPELINE-001: New feature
- **Type:** FEATURE
- **Trigger:** Add new functionality or public behavior.
- **Version:** 1.0
- **Last updated:** 2026-04-24

### Steps
| # | Agent | Action | Input | Expected output |
|---|---|---|---|---|
| 1 | `@python-software-architect` | Analyze impact, define structure and contracts | Requirement | `WORK_PLAN.md`, file structure, interfaces |
| 2 | `@python-tdd` | Generate test cases for each new component | `WORK_PLAN.md` + contracts | Failing `test_*.py` files |
| 3 | `@python-architect` | Implement until all tests pass | Tests + `WORK_PLAN.md` | Green code + `CHANGELOG.md` |
| 4 | `@python-software-architect` | Validate architectural coherence | Implemented code | Approval or correction list |
| 5 | `@python-software-architect` | Update `ARCHITECTURE.md` and `REUSABLE_COMPONENTS.md` | Final state | Updated documentation |

### Notes
- Use when the dominant request is new user-facing or API-facing capability.

## PIPELINE-002: Modify existing functionality
- **Type:** MODIFY
- **Trigger:** Change behavior in an existing component while preserving its role.
- **Version:** 1.0
- **Last updated:** 2026-04-24

### Steps
| # | Agent | Action | Input | Expected output |
|---|---|---|---|---|
| 1 | `@python-software-architect` | Identify affected components and risks | Requirement | `WORK_PLAN.md` with change delta |
| 2 | `@python-tdd` | Update or add tests affected by the change | `WORK_PLAN.md` | Updated tests, regressions marked |
| 3 | `@python-architect` | Implement changes without breaking existing tests | Tests + plan | Green code + `CHANGELOG.md` |
| 4 | `@python-software-architect` | Verify existing contracts were preserved | Modified code | Approval or corrections |

### Notes
- Use for local behavioral changes to existing code.

## PIPELINE-003: Refactor / Optimization
- **Type:** REFACTOR
- **Trigger:** Clean, restructure, optimize, or migrate code without changing logic.
- **Version:** 1.0
- **Last updated:** 2026-04-24

### Steps
| # | Agent | Action | Input | Expected output |
|---|---|---|---|---|
| 1 | `@python-tdd` | Generate or verify test coverage before refactoring | Module to refactor | Test suite as safety net |
| 2 | `@python-software-architect` | Define refactor goal and constraints | Requirement + tests | Refactor plan with clear bounds |
| 3 | `@python-architect` | Refactor keeping all tests green | Plan + tests | Improved code, no regressions |
| 4 | `@python-software-architect` | Validate real improvement and update architecture docs | Result | Updated documentation |

### Notes
- Use when preserving existing simulation behavior is central.

## PIPELINE-004: Delete component
- **Type:** DELETE
- **Trigger:** Remove, deprecate, or delete code or modules.
- **Version:** 1.0
- **Last updated:** 2026-04-24

### Steps
| # | Agent | Action | Input | Expected output |
|---|---|---|---|---|
| 1 | `@python-software-architect` | Map dependencies of the component to delete | Target component | Impact list and safe deletion plan |
| 2 | `@python-tdd` | Identify tests to delete or update | Deletion plan | Obsolete tests identified |
| 3 | `@python-architect` | Delete component and clean dependencies | Plan + tests | Clean code, no orphan references |
| 4 | `@python-software-architect` | Verify no broken references remain | Result | `ARCHITECTURE.md` and `CHANGELOG.md` updated |

### Notes
- Use only when removal is explicitly requested.

## PIPELINE-005: Bug fix
- **Type:** FIX
- **Trigger:** Fix a failure, defect, regression, or error.
- **Version:** 1.0
- **Last updated:** 2026-04-24

### Steps
| # | Agent | Action | Input | Expected output |
|---|---|---|---|---|
| 1 | `@python-tdd` | Write test that reproduces the bug | Bug description | Red test that reproduces the problem |
| 2 | `@python-architect` | Fix until the test passes without breaking others | Failing test | Fixed code, all tests green |
| 3 | `@python-software-architect` | Evaluate if the bug reveals a structural problem | Applied fix | Note in `DECISIONS.md` if applicable |

### Notes
- Use when an existing behavior is known broken.

## PIPELINE-006: Review and audit
- **Type:** REVIEW
- **Trigger:** Review, audit, analyze, or evaluate code quality or architecture.
- **Version:** 1.0
- **Last updated:** 2026-04-24

### Steps
| # | Agent | Action | Input | Expected output |
|---|---|---|---|---|
| 1 | `@python-software-architect` | Audit coherence between code and defined architecture | Module or project | Deviations and technical debt list |
| 2 | `@python-tdd` | Evaluate coverage and quality of existing tests | Audited module | Coverage gap report |
| 3 | Orchestrator | Generate prioritized list of pipelines to run | Previous reports | Improvement backlog ordered by impact |

### Notes
- Use when no implementation is requested.

## PIPELINE-007: Architectural change
- **Type:** ARCHITECTURE
- **Trigger:** Redesign structure, migrate layers, expose an engine boundary, or introduce long-lived architectural contracts.
- **Version:** 1.0
- **Last updated:** 2026-04-24

### Steps
| # | Agent | Action | Input | Expected output |
|---|---|---|---|---|
| 1 | `@python-software-architect` | Design new architecture and record ADR | Requirement | `DECISIONS.md` + phased migration plan |
| 2 | `@python-tdd` | Ensure full coverage before migrating | Migration plan | Test suite as safety net |
| 3 | `@python-software-architect` | Define migration order by module | Tests ready | `WORK_PLAN.md` with phases and milestones |
| 4 | `@python-architect` | Migrate phase by phase, keeping tests green | Phase plan | Code migrated progressively |
| 5 | `@python-software-architect` | Validate each phase and update `ARCHITECTURE.md` | Phase result | Final documentation updated |

### Notes
- Use for this repository when moving notebook/prototype logic into a clean `src/` engine intended for API consumers.

## PIPELINE-008: Customization asset creation
- **Type:** FEATURE
- **Trigger:** Create or update repository-scoped Copilot customizations such as `SKILL.md`, prompt files, agent files, or instruction files.
- **Version:** 1.0
- **Last updated:** 2026-04-24

### Steps
| # | Agent | Action | Input | Expected output |
|---|---|---|---|---|
| 1 | Orchestrator | Identify scope, target primitive, and destination path | Customization request | Chosen primitive, scope, and artifact path |
| 2 | `Explore` | Read repository conventions, commands, and supporting docs to encode | Repo context + target workflow | Canonical commands, references, and constraints |
| 3 | Orchestrator | Create or update the customization artifact | Prior outputs | Valid customization file under `.github/` |
| 4 | Orchestrator | Validate frontmatter, naming, and discovery keywords | Created artifact | Ready-to-use customization plus follow-up questions if needed |

### Notes
- Use when the request is about Copilot customization assets rather than production code.

## PIPELINE-009: Workspace tooling configuration
- **Type:** MODIFY
- **Trigger:** Configure editor, interpreter, debugging, testing, or workspace automation assets such as `.vscode/settings.json` for an existing repository.
- **Version:** 1.0
- **Last updated:** 2026-04-24

### Steps
| # | Agent | Action | Input | Expected output |
|---|---|---|---|---|
| 1 | Orchestrator | Identify the active environment, workspace constraints, and minimum tooling scope | User request + repo metadata | Selected interpreter path and config artifacts to manage |
| 2 | `Explore` | Confirm environment presence and infer repo commands or import roots from local files | Workspace paths + `pyproject.toml`/repo layout | Verified `.venv` path, test command, and source roots |
| 3 | Orchestrator | Create or update workspace configuration artifacts under `.vscode/` | Prior outputs | Ready-to-use workspace settings and recommendations |
| 4 | Orchestrator | Validate config syntax and record any manual follow-up needed | Created artifacts | Logged execution and validation result |

### Notes
- Use when the user asks to prepare VS Code for this repository instead of changing runtime application code.

## PIPELINE-010: Project documentation
- **Type:** FEATURE
- **Trigger:** Create or update project documentation, module documentation, README content, architecture overviews, API docs, onboarding docs, or documentation indexes.
- **Version:** 1.0
- **Last updated:** 2026-04-24

### Steps
| # | Agent | Action | Input | Expected output |
|---|---|---|---|---|
| 1 | Orchestrator | Classify documentation scope and target audience | Documentation request | Documentation scope, target audience, and agent instructions |
| 2 | `@python-docs-architect` | Read relevant source, existing docs, and repository structure | Documentation scope + source context | Markdown documentation files saved to disk |
| 3 | `@python-docs-architect` | Update or create documentation index | Created/modified docs | `docs/INDEX.md` reflecting all docs changed |
| 4 | Orchestrator | Validate files exist and summarize outputs | Documentation artifacts | Completion summary with paths and any remaining gaps |

### Notes
- Use for documentation-only requests. The docs agent may edit Markdown files but must not change implementation code or tests.

## PIPELINE-011: Realtime persisted simulation service
- **Type:** ARCHITECTURE
- **Trigger:** Add realtime/background simulation execution, session history, event streaming, persistent simulation metadata, or MongoDB-backed execution storage.
- **Version:** 1.0
- **Last updated:** 2026-04-24

### Steps
| # | Agent | Action | Input | Expected output |
|---|---|---|---|---|
| 1 | `MongoDB Docker Architect` | Provision local MongoDB infrastructure, schema, indexes, and environment configuration | Persistence and local development requirements | Docker Compose assets, MongoDB init/config files, `.env` template, schema/index plan |
| 2 | `@python-software-architect` | Design realtime execution architecture and persistence contracts | Requirement + MongoDB artifacts | `WORK_PLAN.md`, `DECISIONS.md`, interfaces, module boundaries |
| 3 | `@python-tdd` | Create tests for persistence, session lifecycle, background execution, and reconnect/history recovery | Architecture plan + contracts | Failing or updated pytest files covering new behavior |
| 4 | `@python-architect` | Implement MongoDB connection, repositories, background runner, realtime endpoints, and environment integration | Tests + work plan + Mongo artifacts | Green implementation, updated `CHANGELOG.md`, `REUSABLE_COMPONENTS.md` |
| 5 | `@python-software-architect` | Validate architecture and update architecture documentation | Implemented code | Approval or corrections plus updated architecture docs |
| 6 | Orchestrator | Validate outputs and summarize status | All prior outputs | Completion summary with commands run and remaining risks |

### Notes
- Use local Docker MongoDB for development unless the user provides an external MongoDB target.
- Store high-frequency simulation steps outside the simulation metadata document to avoid unbounded arrays and the 16MB document limit.
- Use environment variables for MongoDB connection settings and keep secrets out of versioned files.