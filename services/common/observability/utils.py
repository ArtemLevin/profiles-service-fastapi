"""Utility helpers used by observability components."""

from __future__ import annotations


def parse_csv(value: str) -> list[str]:
    """Split a comma separated string into a list of unique values."""

    if not value:
        return []
    items = [item.strip() for item in value.split(",")]
    return [item for item in items if item]


__all__ = ["parse_csv"]
