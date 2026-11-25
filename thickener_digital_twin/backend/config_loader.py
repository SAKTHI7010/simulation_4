"""Configuration loader for Thickener Digital Twin model parameters."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import yaml

CONFIG_PATH = Path(__file__).resolve().parent / "config" / "model_parameters.yaml"


@lru_cache(maxsize=1)
def load_raw_config() -> Dict[str, Any]:
    """Load the full YAML parameter register with metadata and units."""
    with CONFIG_PATH.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def get_default_values() -> Dict[str, Any]:
    """Return a flattened dictionary of scalar default values from the parameter register."""
    cfg = load_raw_config()
    defaults: Dict[str, Any] = {}
    for section_name, section in cfg.items():
        if section_name in ("metadata", "reference_ranges") or not isinstance(section, dict):
            continue
        for key, item in section.items():
            if isinstance(item, dict) and "value" in item:
                defaults[key] = item["value"]
    return defaults
