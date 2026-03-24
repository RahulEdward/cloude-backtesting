"""
Indicator registry - auto-discovers all BaseIndicator subclasses in this package.
Supports parameter variants: if a class has get_variants(), all variants are registered.
"""

import importlib
import logging
import pkgutil
from pathlib import Path

from indicators.base import BaseIndicator

logger = logging.getLogger(__name__)

_registry: dict[str, BaseIndicator] = {}


def _discover():
    """Import all modules in this package to trigger subclass registration."""
    package_dir = Path(__file__).parent
    for _, module_name, _ in pkgutil.iter_modules([str(package_dir)]):
        if module_name == "base":
            continue
        importlib.import_module(f"indicators.{module_name}")
        logger.debug(f"Discovered indicator module: indicators.{module_name}")


def register(cls):
    """
    Register an indicator class (decorator).
    If the class defines get_variants(), registers all variant instances.
    Otherwise registers a single default instance.
    """
    if hasattr(cls, "get_variants") and callable(cls.get_variants):
        for instance in cls.get_variants():
            _registry[instance.name] = instance
            logger.debug(f"Registered indicator variant: {instance.name}")
    else:
        instance = cls()
        _registry[instance.name] = instance
        logger.debug(f"Registered indicator: {instance.name}")
    return cls


def get_indicator(name: str) -> BaseIndicator:
    """Get an indicator instance by name."""
    if name not in _registry:
        raise KeyError(f"Indicator '{name}' not found. Available: {list(_registry.keys())}")
    return _registry[name]


def get_all_indicators() -> list[BaseIndicator]:
    """Get all registered indicator instances."""
    return list(_registry.values())


def list_indicators() -> list[str]:
    """List all registered indicator names."""
    return list(_registry.keys())


# Auto-discover on import
_discover()
