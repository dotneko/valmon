import json
from typing import Any


def load_config_file(file: str) -> dict:
    """Attempts to load a json config file"""
    with open(file) as config:
        try:
            return json.load(config)
        except json.decoder.JSONDecodeError as err:
            raise KeyError(
                f"Error: Couldn't load {config}: it is formatted incorrectly "
                f"on line {err.lineno} column {err.colno}"
            ) from err


def get_config(item: str) -> Any:
    """Retrieves the configuration value specified."""
    file = load_config_file("config.json")

    value = file.get(item)

    if value is None:
        raise KeyError(f"Error: Missing a value for {item}")
    return value
