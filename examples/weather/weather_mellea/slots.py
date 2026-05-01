from __future__ import annotations

from mellea import generative


# KB6: no forbidden param names (m, context, backend, model_options, strategy,
# precondition_requirements, requirements, f_args, f_kwargs) in @generative slots.


@generative
def extract_location(query: str) -> str:
    """Set `result` to the city name, region, or IATA airport code mentioned in the query.
    If no location is mentioned, set `result` to an empty string."""
    ...
