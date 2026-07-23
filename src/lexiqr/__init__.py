"""lexiqr — deterministic resolution of tenant jargon to canonical entities.

The public API is deliberately one name: everything an integrating developer
needs goes through `EntityResolver` (ADR 0002).
"""

from lexiqr.resolver import EntityResolver

__all__ = ["EntityResolver"]
