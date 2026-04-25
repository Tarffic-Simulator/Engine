"""API-facing contract tests for realtime session and SSE boundaries."""

from __future__ import annotations

from typing import Any, Dict, List

from traffic_engine.api.app import app


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


class TestRealtimeApiContracts:
    """Boundary tests for realtime create and reconnect endpoints."""

    def test_create_realtime_session_contract_exposes_session_id_and_status(self) -> None:
        # Arrange
        operation = _get_openapi_operation("/realtime/sessions", "post")

        # Act
        schema = _response_schema_for_status(operation, "201")
        required_fields = set(schema.get("required", []))

        # Assert
        assert {"session_id", "run_id", "status"}.issubset(required_fields)

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
