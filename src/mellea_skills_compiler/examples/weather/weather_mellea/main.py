from __future__ import annotations

import argparse
import sys

from weather_mellea.pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="weather-mellea",
        description="Get current weather conditions and forecasts via wttr.in.",
    )
    parser.add_argument(
        "query",
        type=str,
        help=(
            "Natural-language weather request "
            "(e.g. \"What is the weather in London?\" or \"Will it rain in Tokyo tomorrow?\")"
        ),
    )
    args = parser.parse_args()

    try:
        result = run_pipeline(query=args.query)
        print(result)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
