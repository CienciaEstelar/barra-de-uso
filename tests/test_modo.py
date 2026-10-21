import pytest

from barra_de_uso.modo import es_modo_plan


@pytest.mark.parametrize("base_url", [None, "", "   ", "https://api.anthropic.com", "https://api.anthropic.com/"])
def test_modo_plan(base_url):
    assert es_modo_plan(base_url) is True


@pytest.mark.parametrize("base_url", [
    "https://api.deepseek.com/anthropic",
    "https://api.moonshot.ai/anthropic",
    "https://api.z.ai/api/anthropic",
    "http://localhost:4000",
    "api.anthropic.com",  # sin esquema no se puede confirmar el host: se trata como otro proveedor
])
def test_otro_proveedor(base_url):
    assert es_modo_plan(base_url) is False
