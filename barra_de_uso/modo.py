"""Decide si la sesión corre contra el plan de Anthropic o contra otro proveedor."""

from __future__ import annotations

from urllib.parse import urlparse

HOST_ANTHROPIC = "api.anthropic.com"


def es_modo_plan(base_url: str | None) -> bool:
    """True si ANTHROPIC_BASE_URL no está definida, está vacía o apunta a api.anthropic.com."""
    if base_url is None or not base_url.strip():
        return True
    return urlparse(base_url.strip()).hostname == HOST_ANTHROPIC
