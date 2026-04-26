"""API-facing contract tests for realtime session and SSE boundaries."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List

import pytest
from fastapi import HTTPException

from traffic_engine.api.app import app
from traffic_engine.api import realtime_router


def _get_openapi_operation(path: str, method: str) -> Dict[str, Any]:
    schema = app.openapi()
    return schema.get("paths", {}).get(path, {}).get(method, {})


def _operation_parameter_names(operation: Dict[str, Any]) -> List[str]:
    parameters = operation.get("parameters", [])
    return [parameter.get("name", "") for parameter in parameters]


def _resolve_schema_ref(schema: Dict[str, Any], openapi: Dict[str, Any]) -> Dict[str, Any]:
    ref = schema.get("$ref", "")
    if not ref.startswith("#/components/schemas/"):
        return schema

    schema_name = ref.split("/")[-1]
    return openapi.get("components", {}).get("schemas", {}).get(schema_name, {})


def _response_schema_for_status(operation: Dict[str, Any], status_code: str) -> Dict[str, Any]:
    openapi = app.openapi()
    response_block = operation.get("responses", {}).get(status_code, {})
    json_schema = response_block.get("content", {}).get("application/json", {}).get("schema", {})
    return _resolve_schema_ref(json_schema, openapi)


def _response_content_types(operation: Dict[str, Any], status_code: str) -> List[str]:
    response_block = operation.get("responses", {}).get(status_code, {})
    return list(response_block.get("content", {}).keys())


def _request_schema(operation: Dict[str, Any]) -> Dict[str, Any]:
    openapi = app.openapi()
    request_body = operation.get("requestBody", {})
    json_schema = request_body.get("content", {}).get("application/json", {}).get("schema", {})
    return _resolve_schema_ref(json_schema, openapi)


def _property_enum_values(schema: Dict[str, Any], field_name: str) -> List[str]:
    return schema.get("properties", {}).get(field_name, {}).get("enum", [])


class TestRealtimeApiContracts:
    """Boundary tests for realtime create and reconnect endpoints."""

    def test_extend_realtime_session_contract_exposes_extension_endpoint(self) -> None:
        # Arrange
        operation = _get_openapi_operation("/realtime/sessions/{session_id}/runs", "post")

        # Act
        parameter_names = _operation_parameter_names(operation)
        request_schema = _request_schema(operation)

        # Assert
        assert (
            bool(operation),
            "session_id" in set(parameter_names),
            {"n_steps"}.issubset(set(request_schema.get("required", []))),
        ) == (True, True, True)

    def test_realtime_status_contract_exposes_public_availability_shape(self) -> None:
        # Arrange
        operation = _get_openapi_operation("/realtime/status", "get")

        # Act
        schema = _response_schema_for_status(operation, "200")
        required_fields = set(schema.get("required", []))

        # Assert
        assert {"available", "status", "message"}.issubset(required_fields)

    def test_realtime_dependency_error_hides_environment_variable_names(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Arrange
        def _raise_configuration_error() -> None:
            raise RuntimeError("Required environment variable MONGODB_URI is not set.")

        monkeypatch.setattr(
            realtime_router,
            "get_realtime_services",
            _raise_configuration_error,
        )

        # Act
        with pytest.raises(HTTPException) as exc_info:
            realtime_router._resolve_services()

        # Assert
        assert exc_info.value.status_code == 503
        assert "MONGODB_URI" not in str(exc_info.value.detail)
        assert "Realtime persistence is not configured" in str(exc_info.value.detail)

    def test_create_realtime_session_contract_exposes_session_id_and_status(self) -> None:
        # Arrange
        operation = _get_openapi_operation("/realtime/sessions", "post")

        # Act
        schema = _response_schema_for_status(operation, "201")
        required_fields = set(schema.get("required", []))

        # Assert
        assert {"session_id", "run_id", "status"}.issubset(required_fields)

    def test_create_realtime_session_contract_exposes_websocket_url_and_public_status_fields(self) -> None:
        # Arrange
        operation = _get_openapi_operation("/realtime/sessions", "post")

        # Act
        schema = _response_schema_for_status(operation, "201")
        required_fields = set(schema.get("required", []))

        # Assert
        assert {"websocket_url", "session_status", "run_status"}.issubset(required_fields)

    def test_realtime_response_status_enum_uses_public_lifecycle_vocabulary(self) -> None:
        # Arrange
        operation = _get_openapi_operation("/realtime/sessions", "post")
        schema = _response_schema_for_status(operation, "201")

        # Act
        status_enum = set(_property_enum_values(schema, "status"))

        # Assert
        assert status_enum == {"pending", "running", "finished", "failed", "cancelled"}

    def test_list_sessions_response_normalizes_internal_status_values(self) -> None:
        # Arrange
        now = datetime.now(timezone.utc)

        class _FakeListSessionsUseCase:
            def execute(self, status: str | None = None, limit: int = 50) -> Dict[str, Any]:
                return {
                    "sessions": [
                        {
                            "session_id": "session-queued",
                            "created_at": now,
                            "updated_at": now,
                            "status": "queued",
                            "simulation_parameters": {},
                        },
                        {
                            "session_id": "session-completed",
                            "created_at": now,
                            "updated_at": now,
                            "status": "completed",
                            "simulation_parameters": {},
                        },
                    ],
                    "count": 2,
                }

        class _FakeServices:
            list_sessions_use_case = _FakeListSessionsUseCase()

        # Act
        response = asyncio.run(
            realtime_router.list_realtime_sessions(
                status=None,
                limit=50,
                services=_FakeServices(),
            )
        )

        # Assert
        assert [item.status for item in response.sessions] == ["pending", "finished"]

    def test_list_runs_response_normalizes_internal_status_values(self) -> None:
        # Arrange
        now = datetime.now(timezone.utc)

        class _FakeListRunsUseCase:
            def execute(self, session_id: str, limit: int = 50) -> Dict[str, Any]:
                return {
                    "runs": [
                        {
                            "run_id": "run-queued",
                            "session_id": session_id,
                            "created_at": now,
                            "status": "queued",
                            "runtime": {"mode": "realtime"},
                        },
                        {
                            "run_id": "run-completed",
                            "session_id": session_id,
                            "created_at": now,
                            "status": "completed",
                            "runtime": {"mode": "realtime"},
                        },
                    ],
                    "count": 2,
                }

        class _FakeServices:
            list_runs_use_case = _FakeListRunsUseCase()

        # Act
        response = asyncio.run(
            realtime_router.list_realtime_runs(
                session_id="session-replay-001",
                limit=50,
                services=_FakeServices(),
            )
        )

        # Assert
        assert [item.status for item in response.runs] == ["pending", "finished"]

    def test_list_realtime_sessions_contract_exposes_status_and_limit_filters(self) -> None:
        # Arrange
        operation = _get_openapi_operation("/realtime/sessions", "get")

        # Act
        parameter_names = _operation_parameter_names(operation)

        # Assert
        assert {"status", "limit"}.issubset(set(parameter_names))

    def test_list_realtime_runs_contract_exposes_session_and_limit_filters(self) -> None:
        # Arrange
        operation = _get_openapi_operation("/realtime/sessions/{session_id}/runs", "get")

        # Act
        parameter_names = _operation_parameter_names(operation)

        # Assert
        assert {"session_id", "limit"}.issubset(set(parameter_names))

    def test_list_realtime_ticks_contract_exposes_run_and_pagination_filters(self) -> None:
        # Arrange
        operation = _get_openapi_operation("/realtime/sessions/{session_id}/ticks", "get")

        # Act
        parameter_names = _operation_parameter_names(operation)

        # Assert
        assert {"session_id", "run_id", "from_tick", "limit"}.issubset(
            set(parameter_names)
        )

    def test_stream_openapi_contract_exposes_recovery_inputs(self) -> None:
        # Arrange
        operation = _get_openapi_operation(
            "/realtime/sessions/{session_id}/stream",
            "get",
        )

        # Act
        parameter_names = _operation_parameter_names(operation)

        # Assert
        assert {"run_id", "from_tick", "follow", "Last-Event-ID"}.issubset(
            set(parameter_names)
        )

    def test_stream_endpoint_contract_exposes_sse_content_type_for_reconnect(self) -> None:
        # Arrange
        operation = _get_openapi_operation(
            "/realtime/sessions/{session_id}/stream",
            "get",
        )

        # Act
        content_types = _response_content_types(operation, "200")

        # Assert
        assert "text/event-stream" in content_types
