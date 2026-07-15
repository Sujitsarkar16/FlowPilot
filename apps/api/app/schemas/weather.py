"""Validated normalized weather forecast contracts."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class WeatherLookup(BaseModel):
    """A location/date lookup accepted by the Open-Meteo connector."""

    model_config = ConfigDict(extra="forbid")

    location: str = Field(min_length=1, max_length=200)
    date: date


class WeatherForecast(BaseModel):
    """Provider-neutral daily forecast or a graceful unavailable result."""

    model_config = ConfigDict(extra="forbid")

    location: str
    date: date
    available: bool
    temperature_min_c: float | None = None
    temperature_max_c: float | None = None
    precipitation_mm: float | None = None
    condition: str | None = None
    reason: str | None = None
