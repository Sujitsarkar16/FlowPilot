"""Runtime connector lookup and catalog-backed input validation."""

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from app.connectors.base import Connector, MockConnector
from app.services.action_registry import ACTION_REGISTRY, ActionRegistry


class ConnectorRegistryError(ValueError):
    """Raised when a connector is missing or receives an invalid action input."""


class ConnectorRegistry:
    def __init__(
        self,
        connectors: tuple[Connector, ...] = (),
        action_registry: ActionRegistry = ACTION_REGISTRY,
    ) -> None:
        self._connectors: dict[str, Connector] = {}
        self._actions = action_registry
        for connector in connectors:
            self.register(connector)

    @property
    def connectors(self) -> Mapping[str, Connector]:
        return MappingProxyType(dict(self._connectors))

    def register(self, connector: Connector) -> None:
        if connector.name in self._connectors:
            raise ConnectorRegistryError(f"duplicate connector registration: {connector.name}")
        self._connectors[connector.name] = connector

    def get(self, connector_name: str) -> Connector:
        try:
            return self._connectors[connector_name]
        except KeyError as error:
            raise ConnectorRegistryError(f"unknown connector: {connector_name}") from error

    def validate_input(
        self, action_type: str, connector_name: str, payload: Mapping[str, Any]
    ) -> dict[str, Any]:
        definition = self._actions.get(action_type)
        if connector_name != definition.connector:
            raise ConnectorRegistryError(
                f"{action_type} requires connector {definition.connector}, not {connector_name}"
            )
        unexpected = sorted(set(payload) - set(definition.input_schema))
        if unexpected:
            raise ConnectorRegistryError(f"unsupported input fields: {', '.join(unexpected)}")
        missing = [
            name
            for name, field in definition.input_schema.items()
            if field.required and name not in payload
        ]
        if missing:
            raise ConnectorRegistryError(f"missing required input fields: {', '.join(missing)}")
        for name, value in payload.items():
            expected = definition.input_schema[name].value_type
            if not _is_expected_type(value, expected):
                raise ConnectorRegistryError(f"{name} must be a {expected}")
        return dict(payload)


def _is_expected_type(value: object, expected: str) -> bool:
    if expected == "string":
        return isinstance(value, str)
    if expected == "number":
        return isinstance(value, int | float) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "object":
        return isinstance(value, Mapping)
    if expected == "array":
        return isinstance(value, list | tuple)
    return False


DEFAULT_CONNECTOR_REGISTRY = ConnectorRegistry(
    tuple(
        MockConnector(name)
        for name in sorted({definition.connector for definition in ACTION_REGISTRY})
    )
)
