from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class WeatherQueryType(str, Enum):
    """Supported wttr.in query modes plus the out-of-scope sentinel."""

    current_summary = "current_summary"
    current_detailed = "current_detailed"
    forecast_3day = "forecast_3day"
    forecast_week = "forecast_week"
    forecast_day0 = "forecast_day0"
    forecast_day1 = "forecast_day1"
    forecast_day2 = "forecast_day2"
    json_output = "json_output"
    rain_check = "rain_check"
    out_of_scope = "out_of_scope"


class WeatherIntent(BaseModel):
    """Combined scope gate and intent classification for a weather query (P2 pattern)."""

    query_type: WeatherQueryType = Field(
        description=(
            "Classify the weather query type. Use 'current_summary' for simple 'what's the "
            "weather' questions; 'current_detailed' for detailed current conditions; "
            "'forecast_3day' for multi-day forecasts; 'forecast_week' for weekly views; "
            "'forecast_day0' for today, 'forecast_day1' for tomorrow, 'forecast_day2' for the "
            "day after; 'json_output' when the user requests structured/JSON data; 'rain_check' "
            "for rain or precipitation questions. Use 'out_of_scope' for: historical weather "
            "data, climate analysis or trends, hyper-local microclimate data, severe weather "
            "alerts, or aviation/marine weather."
        )
    )
    location: Optional[str] = Field(
        default=None,
        description=(
            "Extract the city name, region, or IATA airport code if the user stated one in their "
            "query; otherwise null. Do not ask for it."
        ),
    )
    out_of_scope_reason: Optional[str] = Field(
        default=None,
        description=(
            "If query_type is 'out_of_scope', extract the specific reason from the user's message "
            "if it is clear from context; otherwise null. Do not ask for it."
        ),
    )
