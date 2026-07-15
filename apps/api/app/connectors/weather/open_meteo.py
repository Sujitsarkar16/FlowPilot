"""Open-Meteo geocoding and forecast connector with in-process result caching."""

from collections.abc import Mapping
from datetime import date
from typing import Any
from uuid import UUID

import httpx
from pydantic import ValidationError

from app.connectors.base import Connector, ConnectorExecutionError
from app.schemas.connector import (
    ConnectorErrorCategory,
    ConnectorExecutionResult,
    ConnectorRollbackResult,
)
from app.schemas.weather import WeatherForecast, WeatherLookup

_WEATHER_CODES = {
    0: "clear",
    1: "mainly_clear",
    2: "partly_cloudy",
    3: "overcast",
    45: "fog",
    48: "fog",
    51: "drizzle",
    53: "drizzle",
    55: "drizzle",
    61: "rain",
    63: "rain",
    65: "rain",
    71: "snow",
    73: "snow",
    75: "snow",
    80: "rain_showers",
    81: "rain_showers",
    82: "rain_showers",
    95: "thunderstorm",
    96: "thunderstorm",
    99: "thunderstorm",
}


class OpenMeteoConnector(Connector):
    name = "weather"
    _geocoding_url = "https://geocoding-api.open-meteo.com/v1/search"
    _forecast_url = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport
        self._cache: dict[tuple[str, date], WeatherForecast] = {}

    async def execute(
        self, *, action_id: UUID, idempotency_key: str, input: Mapping[str, Any]
    ) -> ConnectorExecutionResult:
        lookup = self._lookup(input)
        key = (" ".join(lookup.location.casefold().split()), lookup.date)
        forecast = self._cache.get(key)
        if forecast is None:
            forecast = await self._forecast(lookup)
            self._cache[key] = forecast
        return ConnectorExecutionResult(output=forecast.model_dump(mode="json"))

    async def verify(
        self, *, action_id: UUID, idempotency_key: str, result: ConnectorExecutionResult
    ) -> bool:
        return isinstance(result.output.get("available"), bool) and bool(result.output.get("date"))

    async def rollback(
        self, *, action_id: UUID, rollback_payload: Mapping[str, Any] | None
    ) -> ConnectorRollbackResult:
        return ConnectorRollbackResult(output={"rolled_back": False, "reason": "weather_read_only"})

    @staticmethod
    def _lookup(input: Mapping[str, Any]) -> WeatherLookup:
        try:
            return WeatherLookup.model_validate(dict(input))
        except ValidationError as error:
            raise ConnectorExecutionError(
                ConnectorErrorCategory.VALIDATION, "Invalid weather lookup input"
            ) from error

    async def _forecast(self, lookup: WeatherLookup) -> WeatherForecast:
        geocoding = await self._request(
            self._geocoding_url, params={"name": lookup.location, "count": "1", "language": "en"}
        )
        results = geocoding.get("results")
        if not isinstance(results, list) or not results or not isinstance(results[0], dict):
            return self._unavailable(lookup, "unknown_location")
        location = results[0]
        latitude, longitude = location.get("latitude"), location.get("longitude")
        if not isinstance(latitude, int | float) or not isinstance(longitude, int | float):
            return self._unavailable(lookup, "unknown_location")
        forecast = await self._request(
            self._forecast_url,
            params={
                "latitude": str(latitude),
                "longitude": str(longitude),
                "daily": "temperature_2m_min,temperature_2m_max,precipitation_sum,weather_code",
                "timezone": "auto",
            },
        )
        daily = forecast.get("daily")
        if not isinstance(daily, dict):
            return self._unavailable(lookup, "forecast_unavailable")
        dates = daily.get("time")
        target = lookup.date.isoformat()
        if not isinstance(dates, list) or target not in dates:
            return self._unavailable(lookup, "outside_forecast_horizon")
        index = dates.index(target)
        weather_code = self._integer(daily.get("weather_code"), index)
        return WeatherForecast(
            location=self._location_name(location, lookup.location),
            date=lookup.date,
            available=True,
            temperature_min_c=self._number(daily.get("temperature_2m_min"), index),
            temperature_max_c=self._number(daily.get("temperature_2m_max"), index),
            precipitation_mm=self._number(daily.get("precipitation_sum"), index),
            condition=_WEATHER_CODES.get(weather_code, "unknown")
            if weather_code is not None
            else "unknown",
        )

    @staticmethod
    def _unavailable(lookup: WeatherLookup, reason: str) -> WeatherForecast:
        return WeatherForecast(location=lookup.location, date=lookup.date, available=False, reason=reason)

    @staticmethod
    def _location_name(result: Mapping[str, Any], fallback: str) -> str:
        name = result.get("name")
        country = result.get("country")
        return ", ".join(part for part in (name, country) if isinstance(part, str) and part) or fallback

    @staticmethod
    def _number(values: object, index: int) -> float | None:
        value = values[index] if isinstance(values, list) and len(values) > index else None
        return float(value) if isinstance(value, int | float) else None

    @staticmethod
    def _integer(values: object, index: int) -> int | None:
        value = values[index] if isinstance(values, list) and len(values) > index else None
        return int(value) if isinstance(value, int | float) else None


    async def _request(self, url: str, *, params: dict[str, str]) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=10.0, transport=self._transport) as client:
                response = await client.get(url, params=params)
                payload = response.json()
        except (httpx.HTTPError, ValueError):
            raise ConnectorExecutionError(
                ConnectorErrorCategory.RETRYABLE, "Weather service request failed"
            ) from None
        if not response.is_success:
            category = ConnectorErrorCategory.PERMANENT if 400 <= response.status_code < 500 else ConnectorErrorCategory.RETRYABLE
            raise ConnectorExecutionError(category, "Weather service request failed")
        if not isinstance(payload, dict):
            raise ConnectorExecutionError(
                ConnectorErrorCategory.RETRYABLE, "Weather service returned an invalid response"
            )
        return payload


OpenMeteoWeatherConnector = OpenMeteoConnector
