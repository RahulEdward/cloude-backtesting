"""
Rule registry - auto-discovers all BaseRule subclasses in this package.
Supports parameter variants: if a class has get_variants(), all variants are registered.
"""

import importlib
import logging
import pkgutil
from pathlib import Path

from rules.base import BaseRule

logger = logging.getLogger(__name__)

_registry: dict[str, BaseRule] = {}


def _discover():
    """Import all modules in this package to trigger subclass registration."""
    package_dir = Path(__file__).parent
    for _, module_name, _ in pkgutil.iter_modules([str(package_dir)]):
        if module_name == "base":
            continue
        importlib.import_module(f"rules.{module_name}")
        logger.debug(f"Discovered rule module: rules.{module_name}")


def register(cls):
    """
    Register a rule class (decorator).
    If the class defines get_variants(), registers all variant instances.
    Otherwise registers a single default instance.
    """
    if hasattr(cls, "get_variants") and callable(cls.get_variants):
        for instance in cls.get_variants():
            _registry[instance.name] = instance
            logger.debug(f"Registered rule variant: {instance.name}")
    else:
        instance = cls()
        _registry[instance.name] = instance
        logger.debug(f"Registered rule: {instance.name}")
    return cls


def get_rule(name: str) -> BaseRule:
    """Get a rule instance by name."""
    if name not in _registry:
        raise KeyError(f"Rule '{name}' not found. Available: {list(_registry.keys())}")
    return _registry[name]


def get_all_rules() -> list[BaseRule]:
    """Get all registered rule instances."""
    return list(_registry.values())


def list_rules() -> list[str]:
    """List all registered rule names."""
    return list(_registry.keys())


# Auto-discover on import
_discover()
