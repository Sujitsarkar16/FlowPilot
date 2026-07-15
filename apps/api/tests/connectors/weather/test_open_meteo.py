from uuid import uuid4

import httpx
import pytest

from app.connectors.weather.open_meteo import OpenMeteoConnector


@pytest.mark.asyncio
async def test_forecast_is_normalized_and_cached_by_location_and_date() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if "geocoding" in request.url.host:
            return httpx.Response(200, json={"results": [{"name": "Lisbon", "country": "Portugal", "latitude": 38.7, "longitude": -9.1}]})
        return httpx.Response(200, json={"daily": {"time": ["2030-06-01"], "temperature_2m_min": [14.2], "temperature_2m_max": [24.8], "precipitation_sum": [0.4], "weather_code": [2]}})

    connector = OpenMeteoConnector(transport=httpx.MockTransport(handler))
    input = {"location": " Lisbon ", "date": "2030-06-01"}
    first = await connector.execute(action_id=uuid4(), idempotency_key="one", input=input)
    second = await connector.execute(action_id=uuid4(), idempotency_key="two", input=input)
    assert first.output == second.output
    assert first.output == {"location": "Lisbon, Portugal", "date": "2030-06-01", "available": True, "temperature_min_c": 14.2, "temperature_max_c": 24.8, "precipitation_mm": 0.4, "condition": "partly_cloudy", "reason": None}
    assert len(requests) == 2


@pytest.mark.asyncio
async def test_unknown_location_and_horizon_are_nonfatal() -> None:
    connector = OpenMeteoConnector(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"results": []})))
    result = await connector.execute(action_id=uuid4(), idempotency_key="none", input={"location": "Nowhere", "date": "2030-06-01"})
    assert result.output == {"location": "Nowhere", "date": "2030-06-01", "available": False, "temperature_min_c": None, "temperature_max_c": None, "precipitation_mm": None, "condition": None, "reason": "unknown_location"}
