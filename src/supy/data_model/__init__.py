"""
SUEWS Data Model

This module provides Pydantic-based data models for the SUEWS urban climate model.

All physical parameters use RefValue wrappers with explicit units:
- Physical quantities have appropriate SI-based units (m, kg, W, degC, etc.)
- Dimensionless ratios are marked with unit="dimensionless"
- Configuration parameters (methods, flags, paths) appropriately have no units

See README.md for detailed unit conventions and usage examples.
"""

from .core import SUEWSConfig, init_config_from_yaml
from .model import Model
from .site import Site, SiteProperties
from .state import InitialStates
from .human_activity import AnthropogenicEmissions, AnthropogenicHeat, CO2Params
from .type import RefValue, Reference

