"""Normalize messy glob pattern lists, strictly by default."""

from .formatter import GlobSyntaxError, normalize_pattern

__version__ = "0.1.0"
__all__ = ["GlobSyntaxError", "normalize_pattern", "__version__"]
