# barra-de-uso Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Status line en Python para Claude Code que muestra el uso del plan Anthropic (5 h y semanal, reset en hora de Chile) o, en modos de otros proveedores, los tokens de la sesión por modelo (in / cr / cw / out).

**Architecture:** `barra.py` lee el JSON que Claude Code entrega por stdin. Según `ANTHROPIC_BASE_URL` decide el modo: en modo plan formatea `rate_limits` del payload; en otro proveedor lee incrementalmente el transcript principal y los de subagentes, deduplica por `message.id` y suma por modelo, guardando el avance en `~/.cache/barra-de-uso/<session_id>.json`. Cero red, cero credenciales.

**Tech Stack:** Python 3.12 solo stdlib (`json`, `zoneinfo`, `pathlib`, `tempfile`); pytest 7.4 para tests.

**Spec:** `docs/superpowers/specs/2026-10-21-barra-de-uso-design.md`. Leerlo completo antes de empezar.

---

## Reglas para quien implementa

- Raíz del repo: `/home/juan-galaz/Escritorio/Proyectos/barra-de-uso`. Todos los comandos se corren desde ahí.
- Convenciones de `~/Escritorio/Proyectos/CLAUDE.md`: nombres y comentarios en español, sin `except:` desnudo, sin em dashes (el carácter U+2014) en ningún archivo, tests con pytest.
- Repo **público**: no copiar transcripts, payloads ni rutas reales de Juan dentro del repo. Los tests arman datos sintéticos con `tests/conftest.py`.
- El código de este plan ya fue escrito y probado (65 tests pasando, validado contra transcripts reales). **Copiarlo tal cual.** Si algo no calza, detenerse y reportar en vez de improvisar.
- No modificar `~/.claude/settings.json`. La instalación (Task 10) la confirma Juan.
- No hacer `git push`. Solo commits locales; el push lo decide Juan.
- Comunicación con Juan: español chileno casual.

## Mapa de archivos

| Archivo | Responsabilidad |
|---|---|
| `pyproject.toml` | metadatos y config de pytest (`pythonpath = ["."]`) |
| `.gitignore` | cachés de Python y pytest |
| `barra.py` | lanzador que ejecuta Claude Code |
| `barra_de_uso/entrada.py` | JSON de stdin a `Payload` / `Ventana`, tolerante a faltantes |
| `barra_de_uso/modo.py` | `es_modo_plan(base_url)` |
| `barra_de_uso/plan.py` | línea del modo plan, reset en `America/Santiago` |
| `barra_de_uso/transcripts.py` | archivos de la sesión, lectura incremental, dedupe, totales por modelo |
| `barra_de_uso/cache.py` | ruta, carga validada y guardado atómico del estado |
| `barra_de_uso/formato.py` | `abreviar(n)` y `tabla_tokens(totales)` |
| `barra_de_uso/principal.py` | orquestación y red de seguridad |
| `tests/conftest.py` | ayudantes de transcripts sintéticos y fixture `cache_temporal` |
| `tests/test_*.py` | un archivo por módulo, más `test_principal.py` end to end |

---

### Task 0: Capturar un payload real (gate, requiere a Juan)

Objetivo: confirmar que Claude Code 2.1.296 entrega `rate_limits`, `transcript_path` y `session_id` como asume el spec. **Las capturas quedan fuera del repo** (`~/.cache/barra-de-uso/capturas/`).

- [ ] **Step 1: Pedirle a Juan que configure temporalmente el status line**

Mensaje para Juan: "Para validar el formato necesito capturar el JSON real que Claude Code le pasa al status line. ¿Me autorizas a poner temporalmente esto en `~/.claude/settings.json`? Lo saco al terminar."

```json
"statusLine": {
  "type": "command",
  "command": "mkdir -p ~/.cache/barra-de-uso/capturas && cat > ~/.cache/barra-de-uso/capturas/payload-$(date +%s%N).json && echo capturando"
}
```

Sin autorización explícita, no tocar el archivo. Si Juan prefiere hacerlo él, darle el bloque.

- [ ] **Step 2: Juan abre una sesión `claude` (modo plan) y una `ds_mode`, manda un mensaje en cada una y las cierra**

- [ ] **Step 3: Revisar las capturas**

Run:
```bash
for f in ~/.cache/barra-de-uso/capturas/*.json; do jq -c '{modelo: .model, sid: (.session_id != null), tp: .transcript_path, rl: .rate_limits}' "$f"; done | sort -u
```
Expected: en la sesión `claude`, `rl` con `five_hour` y `seven_day`, cada uno con `used_percentage` numérico y `resets_at` en segundos epoch (10 dígitos). En `ds_mode`, `tp` apunta a un `.jsonl` existente. Para validar la zona horaria: `jq '.rate_limits.seven_day.resets_at' <captura> | xargs -I{} python3 -c "from datetime import datetime; from zoneinfo import ZoneInfo; print(datetime.fromtimestamp({}, ZoneInfo('America/Santiago')))"` debe dar un martes a las 04:00.

**Si la forma difiere del spec: DETENERSE y reportar a Juan con la diferencia exacta.** No adaptar el código por cuenta propia.

- [ ] **Step 4: Restaurar `~/.claude/settings.json`**

Quitar el bloque `statusLine` temporal (o dejar el que había antes). Confirmar con `grep -n statusLine ~/.claude/settings.json`.

---

### Task 1: Esqueleto del proyecto

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `barra_de_uso/__init__.py` (vacío), `tests/__init__.py` (vacío), `tests/conftest.py`

- [ ] **Step 1: Crear `pyproject.toml`**

```toml
[project]
name = "barra-de-uso"
version = "0.1.0"
description = "Status line para Claude Code: uso del plan y tokens por modelo"
requires-python = ">=3.12"
dependencies = []

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 2: Crear `.gitignore`**

```
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 3: Crear los `__init__.py` vacíos**

Run: `mkdir -p barra_de_uso tests && touch barra_de_uso/__init__.py tests/__init__.py`

- [ ] **Step 4: Crear `tests/conftest.py`**

```python
"""Ayudantes para armar transcripts SINTÉTICOS. Nunca usar datos reales: el repo es público."""

import json
from pathlib import Path

import pytest


def respuesta(id_mensaje, modelo, entrada=0, cache_lectura=0, cache_escritura=0, salida=0, **extra):
    """Una línea 'assistant' con la misma forma que escribe Claude Code."""
    linea = {
        "type": "assistant",
        "message": {
            "id": id_mensaje,
            "model": modelo,
            "usage": {
                "input_tokens": entrada,
                "cache_read_input_tokens": cache_lectura,
                "cache_creation_input_tokens": cache_escritura,
                "output_tokens": salida,
            },
        },
    }
    linea.update(extra)
    return linea


def escribir_jsonl(ruta: Path, lineas, final_incompleto: str = "") -> Path:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    texto = "".join(json.dumps(linea) + "\n" for linea in lineas) + final_incompleto
    ruta.write_text(texto, encoding="utf-8")
    return ruta


def agregar_jsonl(ruta: Path, lineas) -> None:
    with ruta.open("a", encoding="utf-8") as archivo:
        for linea in lineas:
            archivo.write(json.dumps(linea) + "\n")


@pytest.fixture
def cache_temporal(tmp_path, monkeypatch):
    carpeta = tmp_path / "cache"
    monkeypatch.setenv("BARRA_DE_USO_CACHE_DIR", str(carpeta))
    return carpeta
```

- [ ] **Step 5: Verificar que pytest arranca**

Run: `python3 -m pytest -q`
Expected: `no tests ran` (exit code 5). Es correcto: todavía no hay tests.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .gitignore barra_de_uso/__init__.py tests/__init__.py tests/conftest.py
git commit -m "chore: esqueleto del proyecto y ayudantes de test"
```

---

### Task 2: Parseo del payload (`entrada.py`)

**Files:**
- Create: `barra_de_uso/entrada.py`
- Test: `tests/test_entrada.py`

- [ ] **Step 1: Escribir los tests**

```python
import json

import pytest

from barra_de_uso.entrada import NOMBRE_RESPALDO, Ventana, parsear_payload


def test_payload_completo():
    texto = json.dumps({
        "model": {"id": "claude-opus-5-5", "display_name": "Opus 5.5"},
        "session_id": "abc-123",
        "transcript_path": "/tmp/x.jsonl",
        "rate_limits": {
            "five_hour": {"used_percentage": 42, "resets_at": 1774020000},
            "seven_day": {"used_percentage": 15.5, "resets_at": "1774540000"},
        },
    })
    payload = parsear_payload(texto)
    assert payload.modelo == "Opus 5.5"
    assert payload.session_id == "abc-123"
    assert payload.transcript_path == "/tmp/x.jsonl"
    assert payload.cinco_horas == Ventana(42.0, 1774020000.0)
    assert payload.semanal == Ventana(15.5, 1774540000.0)


def test_usa_id_si_falta_display_name():
    assert parsear_payload('{"model": {"id": "deepseek-flash"}}').modelo == "deepseek-flash"


def test_objeto_vacio_usa_nombre_de_respaldo():
    payload = parsear_payload("{}")
    assert payload.modelo == NOMBRE_RESPALDO
    assert payload.session_id is None
    assert payload.transcript_path is None
    assert payload.cinco_horas is None
    assert payload.semanal is None


def test_rate_limits_null():
    payload = parsear_payload('{"rate_limits": null}')
    assert payload.cinco_horas is None
    assert payload.semanal is None


def test_valores_invalidos_quedan_en_none():
    texto = json.dumps({"rate_limits": {"five_hour": {"used_percentage": "nada", "resets_at": True}}})
    assert parsear_payload(texto).cinco_horas == Ventana(None, None)


def test_nan_queda_en_none():
    texto = json.dumps({"rate_limits": {"five_hour": {"used_percentage": "nan"}}})
    assert parsear_payload(texto).cinco_horas == Ventana(None, None)


def test_json_invalido_lanza_value_error():
    with pytest.raises(ValueError):
        parsear_payload("esto no es json")


def test_json_que_no_es_objeto_lanza_value_error():
    with pytest.raises(ValueError):
        parsear_payload("[1, 2]")
```

- [ ] **Step 2: Verificar que fallan**

Run: `python3 -m pytest tests/test_entrada.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'barra_de_uso.entrada'`

- [ ] **Step 3: Implementar**

```python
"""Parseo tolerante del JSON que Claude Code entrega por stdin al status line."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass

NOMBRE_RESPALDO = "barra-de-uso"


@dataclass(frozen=True)
class Ventana:
    """Una ventana de rate limit: porcentaje usado y momento del reset (epoch en segundos)."""

    porcentaje: float | None
    reset_epoch: float | None


@dataclass(frozen=True)
class Payload:
    modelo: str
    session_id: str | None
    transcript_path: str | None
    cinco_horas: Ventana | None
    semanal: Ventana | None


def _numero(valor: object) -> float | None:
    # resets_at y used_percentage pueden llegar como número o como string.
    if isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        numero = float(valor)
    elif isinstance(valor, str):
        try:
            numero = float(valor)
        except ValueError:
            return None
    else:
        return None
    return numero if math.isfinite(numero) else None


def _texto(valor: object) -> str | None:
    return valor if isinstance(valor, str) and valor else None


def _diccionario(valor: object) -> dict:
    return valor if isinstance(valor, dict) else {}


def _ventana(valor: object) -> Ventana | None:
    if not isinstance(valor, dict):
        return None
    return Ventana(_numero(valor.get("used_percentage")), _numero(valor.get("resets_at")))


def parsear_payload(texto: str) -> Payload:
    """Convierte el JSON de stdin en un Payload. Lanza ValueError si no es un objeto JSON."""
    datos = json.loads(texto)
    if not isinstance(datos, dict):
        raise ValueError("el payload no es un objeto JSON")
    info_modelo = _diccionario(datos.get("model"))
    modelo = _texto(info_modelo.get("display_name")) or _texto(info_modelo.get("id")) or NOMBRE_RESPALDO
    limites = _diccionario(datos.get("rate_limits"))
    return Payload(
        modelo=modelo,
        session_id=_texto(datos.get("session_id")),
        transcript_path=_texto(datos.get("transcript_path")),
        cinco_horas=_ventana(limites.get("five_hour")),
        semanal=_ventana(limites.get("seven_day")),
    )
```

- [ ] **Step 4: Verificar que pasan**

Run: `python3 -m pytest tests/test_entrada.py -q`
Expected: `8 passed`

- [ ] **Step 5: Commit**

```bash
git add barra_de_uso/entrada.py tests/test_entrada.py
git commit -m "feat: parseo tolerante del payload de Claude Code"
```

---

### Task 3: Detección de modo (`modo.py`)

**Files:**
- Create: `barra_de_uso/modo.py`
- Test: `tests/test_modo.py`

- [ ] **Step 1: Escribir los tests**

```python
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
```

- [ ] **Step 2: Verificar que fallan**

Run: `python3 -m pytest tests/test_modo.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'barra_de_uso.modo'`

- [ ] **Step 3: Implementar**

```python
"""Decide si la sesión corre contra el plan de Anthropic o contra otro proveedor."""

from __future__ import annotations

from urllib.parse import urlparse

HOST_ANTHROPIC = "api.anthropic.com"


def es_modo_plan(base_url: str | None) -> bool:
    """True si ANTHROPIC_BASE_URL no está definida, está vacía o apunta a api.anthropic.com."""
    if base_url is None or not base_url.strip():
        return True
    return urlparse(base_url.strip()).hostname == HOST_ANTHROPIC
```

- [ ] **Step 4: Verificar que pasan**

Run: `python3 -m pytest tests/test_modo.py -q`
Expected: `10 passed`

- [ ] **Step 5: Commit**

```bash
git add barra_de_uso/modo.py tests/test_modo.py
git commit -m "feat: detectar modo plan o proveedor externo por ANTHROPIC_BASE_URL"
```

---

### Task 4: Línea del modo plan (`plan.py`)

**Files:**
- Create: `barra_de_uso/plan.py`
- Test: `tests/test_plan.py`

Nota: Chile continental usa UTC-3 en verano (de septiembre a abril) y UTC-4 en invierno. Los tests fijan epochs en UTC para cubrir ambos. Usar siempre `zoneinfo`, nunca un offset fijo.

- [ ] **Step 1: Escribir los tests**

```python
from datetime import datetime, timezone

from barra_de_uso.entrada import Payload, Ventana
from barra_de_uso.plan import formatear_reset, formatear_ventana, linea_plan


def epoch_utc(*partes):
    return datetime(*partes, tzinfo=timezone.utc).timestamp()


# Miércoles 21-oct-2026 12:00 hora de Chile (UTC-3 en horario de verano).
AHORA = datetime(2026, 10, 21, 15, 0, tzinfo=timezone.utc)


def test_reset_hoy_muestra_solo_hora():
    # 21-oct 19:30 UTC = 16:30 en Chile, mismo día.
    assert formatear_reset(epoch_utc(2026, 10, 21, 19, 30), AHORA) == "16:30"


def test_reset_martes_04_00_horario_de_verano():
    # 27-oct-2026 es martes; Chile en UTC-3, así que 04:00 local = 07:00 UTC.
    assert formatear_reset(epoch_utc(2026, 10, 27, 7, 0), AHORA) == "mar 04:00"


def test_reset_martes_04_00_horario_de_invierno():
    # 16-jun-2026 es martes; Chile en UTC-4, así que 04:00 local = 08:00 UTC.
    ahora = datetime(2026, 6, 12, 15, 0, tzinfo=timezone.utc)
    assert formatear_reset(epoch_utc(2026, 6, 16, 8, 0), ahora) == "mar 04:00"


def test_dia_con_tilde():
    # 24-oct-2026 es sábado.
    assert formatear_reset(epoch_utc(2026, 10, 24, 15, 0), AHORA) == "sáb 12:00"


def test_fecha_se_compara_en_hora_de_chile_no_utc():
    # 22-oct 02:00 UTC todavía es 21-oct 23:00 en Chile: cuenta como hoy.
    assert formatear_reset(epoch_utc(2026, 10, 22, 2, 0), AHORA) == "23:00"


def test_ventana_con_porcentaje_fraccional():
    assert formatear_ventana("5h", Ventana(23.6, None), AHORA) == "5h 24%"


def test_ventana_sin_porcentaje():
    assert formatear_ventana("sem", Ventana(None, epoch_utc(2026, 10, 27, 7, 0)), AHORA) == "sem --"


def test_ventana_ausente():
    assert formatear_ventana("5h", None, AHORA) == "5h --"


def test_linea_plan_completa():
    payload = Payload(
        modelo="Opus 5.5",
        session_id=None,
        transcript_path=None,
        cinco_horas=Ventana(42, epoch_utc(2026, 10, 21, 19, 30)),
        semanal=Ventana(18, epoch_utc(2026, 10, 27, 7, 0)),
    )
    assert linea_plan(payload, AHORA) == "Opus 5.5 · 5h 42% ↻ 16:30 · sem 18% ↻ mar 04:00"


def test_linea_plan_sin_rate_limits():
    payload = Payload("Opus 5.5", None, None, None, None)
    assert linea_plan(payload, AHORA) == "Opus 5.5 · 5h -- · sem --"
```

- [ ] **Step 2: Verificar que fallan**

Run: `python3 -m pytest tests/test_plan.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'barra_de_uso.plan'`

- [ ] **Step 3: Implementar**

```python
"""Línea del modo plan: uso de la ventana de 5 h y de la semanal, con reset en hora de Chile."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from barra_de_uso.entrada import Payload, Ventana

# Se resuelve dentro de la función para que un tzdata faltante caiga en la red de seguridad.
ZONA_CHILE = "America/Santiago"
DIAS = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")
SEPARADOR = " · "


def formatear_reset(reset_epoch: float, ahora: datetime) -> str:
    """Solo HH:MM si el reset cae hoy (hora de Chile); si no, día abreviado y HH:MM."""
    zona = ZoneInfo(ZONA_CHILE)
    reset = datetime.fromtimestamp(reset_epoch, zona)
    hora = reset.strftime("%H:%M")
    if reset.date() == ahora.astimezone(zona).date():
        return hora
    return f"{DIAS[reset.weekday()]} {hora}"


def formatear_ventana(etiqueta: str, ventana: Ventana | None, ahora: datetime) -> str:
    if ventana is None or ventana.porcentaje is None:
        return f"{etiqueta} --"
    texto = f"{etiqueta} {round(ventana.porcentaje)}%"
    if ventana.reset_epoch is not None:
        texto += f" ↻ {formatear_reset(ventana.reset_epoch, ahora)}"
    return texto


def linea_plan(payload: Payload, ahora: datetime) -> str:
    """`ahora` debe ser un datetime con zona horaria."""
    return SEPARADOR.join([
        payload.modelo,
        formatear_ventana("5h", payload.cinco_horas, ahora),
        formatear_ventana("sem", payload.semanal, ahora),
    ])
```

- [ ] **Step 4: Verificar que pasan**

Run: `python3 -m pytest tests/test_plan.py -q`
Expected: `10 passed`

- [ ] **Step 5: Commit**

```bash
git add barra_de_uso/plan.py tests/test_plan.py
git commit -m "feat: linea del modo plan con reset en hora de Chile"
```

---

### Task 5: Transcripts y totales por modelo (`transcripts.py`)

**Files:**
- Create: `barra_de_uso/transcripts.py`
- Test: `tests/test_transcripts.py`

Contexto verificado en transcripts reales:
- Cada respuesta aparece repetida con el mismo `message.id`; algunas repeticiones traen usage en cero. Se conserva la de mayor suma.
- Los subagentes viven en `<transcript sin .jsonl>/subagents/**/agent-*.jsonl` con carpetas anidadas (`subagents/workflows/wf_xxx/`). Por eso `rglob`.

- [ ] **Step 1: Escribir los tests**

```python
from barra_de_uso.transcripts import (
    actualizar_estado,
    archivos_de_sesion,
    leer_desde,
    totales_por_modelo,
    uso_de_entrada,
)
from tests.conftest import agregar_jsonl, escribir_jsonl, respuesta


def estado_vacio():
    return {"version": 1, "archivos": {}, "mensajes": {}}


def totales_de(archivos):
    estado = estado_vacio()
    actualizar_estado(estado, archivos)
    return totales_por_modelo(estado["mensajes"])


def test_uso_de_entrada_valida():
    id_mensaje, uso = uso_de_entrada(respuesta("m1", "kimi-k3", 1, 2, 3, 4))
    assert id_mensaje == "m1"
    assert uso == {"modelo": "kimi-k3", "in": 1, "cr": 2, "cw": 3, "out": 4}


def test_descarta_sintetico_error_y_no_assistant():
    assert uso_de_entrada(respuesta("m1", "<synthetic>", 1)) is None
    assert uso_de_entrada(respuesta("m2", "kimi-k3", 1, isApiErrorMessage=True)) is None
    assert uso_de_entrada({"type": "user", "message": {"id": "m3"}}) is None
    assert uso_de_entrada({"type": "assistant", "message": {"id": "m4", "model": "x"}}) is None


def test_usage_con_nulos_cuenta_cero():
    linea = respuesta("m1", "kimi-k3", 5)
    linea["message"]["usage"]["cache_read_input_tokens"] = None
    _, uso = uso_de_entrada(linea)
    assert uso["cr"] == 0


def test_duplicados_se_cuentan_una_vez(tmp_path):
    principal = escribir_jsonl(tmp_path / "s.jsonl", [respuesta("m1", "deepseek-flash", 781, 67_456, 0, 299)] * 3)
    assert totales_de([principal]) == {"deepseek-flash": {"in": 781, "cr": 67_456, "cw": 0, "out": 299}}


def test_duplicado_con_usage_distinto_gana_el_mayor(tmp_path):
    principal = escribir_jsonl(tmp_path / "s.jsonl", [
        respuesta("m1", "kimi-k3", 2, 900, 100, 50),
        respuesta("m1", "kimi-k3"),
    ])
    assert totales_de([principal])["kimi-k3"] == {"in": 2, "cr": 900, "cw": 100, "out": 50}


def test_linea_rota_se_ignora(tmp_path):
    ruta = tmp_path / "s.jsonl"
    ruta.write_text('{"roto": \n' + '{"type": "assistant"}\n', encoding="utf-8")
    agregar_jsonl(ruta, [respuesta("m1", "kimi-k3", 10)])
    assert totales_de([ruta])["kimi-k3"]["in"] == 10


def test_linea_final_incompleta_no_avanza_offset(tmp_path):
    ruta = escribir_jsonl(tmp_path / "s.jsonl", [respuesta("m1", "kimi-k3", 10)], final_incompleto='{"type": "assis')
    entradas, offset = leer_desde(ruta, 0)
    assert len(entradas) == 1
    assert offset == ruta.read_bytes().rfind(b"\n") + 1


def test_subagentes_anidados_por_modelo(tmp_path):
    principal = escribir_jsonl(tmp_path / "sesion.jsonl", [respuesta("m1", "kimi-k3", 100, 0, 0, 10)])
    escribir_jsonl(
        tmp_path / "sesion" / "subagents" / "workflows" / "wf_x" / "agent-abc.jsonl",
        [respuesta("s1", "glm-fast", 40, 0, 0, 4)],
    )
    escribir_jsonl(tmp_path / "sesion" / "subagents" / "agent-def.jsonl", [respuesta("s2", "glm-fast", 2, 0, 0, 1)])
    archivos = archivos_de_sesion(principal)
    assert len(archivos) == 3
    assert totales_de(archivos) == {
        "kimi-k3": {"in": 100, "cr": 0, "cw": 0, "out": 10},
        "glm-fast": {"in": 42, "cr": 0, "cw": 0, "out": 5},
    }


def test_sin_transcript_no_hay_archivos(tmp_path):
    assert archivos_de_sesion(tmp_path / "no-existe.jsonl") == []


def test_lectura_incremental_solo_procesa_lo_nuevo(tmp_path):
    ruta = escribir_jsonl(tmp_path / "s.jsonl", [respuesta("m1", "kimi-k3", 10)])
    estado = estado_vacio()
    actualizar_estado(estado, [ruta])
    offset_inicial = estado["archivos"][str(ruta)]["offset"]
    assert offset_inicial == ruta.stat().st_size
    agregar_jsonl(ruta, [respuesta("m2", "kimi-k3", 5)])
    actualizar_estado(estado, [ruta])
    assert estado["archivos"][str(ruta)]["offset"] == ruta.stat().st_size
    assert totales_por_modelo(estado["mensajes"])["kimi-k3"]["in"] == 15


def test_archivo_truncado_se_relee_desde_cero(tmp_path):
    ruta = escribir_jsonl(tmp_path / "s.jsonl", [respuesta(f"m{i}", "kimi-k3", 10) for i in range(5)])
    estado = estado_vacio()
    actualizar_estado(estado, [ruta])
    escribir_jsonl(ruta, [respuesta("n1", "kimi-k3", 1)])  # mismo inodo, más corto
    actualizar_estado(estado, [ruta])
    assert estado["archivos"][str(ruta)]["offset"] == ruta.stat().st_size
    assert "n1" in estado["mensajes"]
```

- [ ] **Step 2: Verificar que fallan**

Run: `python3 -m pytest tests/test_transcripts.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'barra_de_uso.transcripts'`

- [ ] **Step 3: Implementar**

```python
"""Lectura incremental de los transcripts de una sesión y suma de tokens por modelo."""

from __future__ import annotations

import json
from pathlib import Path

# Claves cortas usadas en el caché y en la tabla: entrada, caché lectura, caché escritura, salida.
CAMPOS = ("in", "cr", "cw", "out")
CAMPOS_USAGE = {
    "in": "input_tokens",
    "cr": "cache_read_input_tokens",
    "cw": "cache_creation_input_tokens",
    "out": "output_tokens",
}
MODELO_SINTETICO = "<synthetic>"


def archivos_de_sesion(transcript_path: Path) -> list[Path]:
    """Transcript principal más los de subagentes, buscados recursivamente."""
    if not transcript_path.is_file():
        return []
    archivos = [transcript_path]
    carpeta_subagentes = transcript_path.with_suffix("") / "subagents"
    if carpeta_subagentes.is_dir():
        archivos.extend(sorted(carpeta_subagentes.rglob("agent-*.jsonl")))
    return archivos


def _entero(valor: object) -> int:
    if isinstance(valor, int) and not isinstance(valor, bool) and valor >= 0:
        return valor
    return 0


def suma_uso(uso: dict) -> int:
    return sum(uso[campo] for campo in CAMPOS)


def uso_de_entrada(entrada: dict) -> tuple[str, dict] | None:
    """Devuelve (message.id, uso) si la entrada es una respuesta válida; si no, None."""
    if entrada.get("type") != "assistant" or entrada.get("isApiErrorMessage") is True:
        return None
    mensaje = entrada.get("message")
    if not isinstance(mensaje, dict):
        return None
    id_mensaje = mensaje.get("id")
    modelo = mensaje.get("model")
    usage = mensaje.get("usage")
    if not isinstance(id_mensaje, str) or not id_mensaje:
        return None
    if not isinstance(modelo, str) or not modelo or modelo == MODELO_SINTETICO:
        return None
    if not isinstance(usage, dict):
        return None
    uso = {"modelo": modelo}
    for campo, clave in CAMPOS_USAGE.items():
        uso[campo] = _entero(usage.get(clave))
    return id_mensaje, uso


def fusionar(mensajes: dict, id_mensaje: str, uso: dict) -> None:
    """Un mismo message.id aparece repetido; se conserva la repetición con mayor uso total."""
    previo = mensajes.get(id_mensaje)
    if previo is None or suma_uso(uso) > suma_uso(previo):
        mensajes[id_mensaje] = uso


def leer_desde(ruta: Path, offset: int) -> tuple[list[dict], int]:
    """Lee las líneas completas desde `offset`. Devuelve las entradas y el nuevo offset."""
    with ruta.open("rb") as archivo:
        archivo.seek(offset)
        datos = archivo.read()
    corte = datos.rfind(b"\n")
    if corte == -1:
        # Nada completo todavía: la línea a medio escribir se relee en el próximo refresco.
        return [], offset
    entradas = []
    for linea in datos[:corte].split(b"\n"):
        if not linea.strip():
            continue
        try:
            objeto = json.loads(linea)
        except ValueError:  # incluye JSONDecodeError y UnicodeDecodeError
            continue
        if isinstance(objeto, dict):
            entradas.append(objeto)
    return entradas, offset + corte + 1


def actualizar_estado(estado: dict, archivos: list[Path]) -> None:
    """Procesa lo nuevo de cada archivo y lo fusiona en estado['mensajes']."""
    for ruta in archivos:
        try:
            info = ruta.stat()
        except OSError:
            continue
        clave = str(ruta)
        previo = estado["archivos"].get(clave)
        offset = 0
        if previo is not None and previo["inodo"] == info.st_ino and previo["offset"] <= info.st_size:
            offset = previo["offset"]
        try:
            entradas, nuevo_offset = leer_desde(ruta, offset)
        except OSError:
            continue
        for entrada in entradas:
            resultado = uso_de_entrada(entrada)
            if resultado is not None:
                fusionar(estado["mensajes"], *resultado)
        estado["archivos"][clave] = {"inodo": info.st_ino, "offset": nuevo_offset}


def totales_por_modelo(mensajes: dict) -> dict[str, dict[str, int]]:
    totales: dict[str, dict[str, int]] = {}
    for uso in mensajes.values():
        total = totales.setdefault(uso["modelo"], dict.fromkeys(CAMPOS, 0))
        for campo in CAMPOS:
            total[campo] += uso[campo]
    return totales
```

- [ ] **Step 4: Verificar que pasan**

Run: `python3 -m pytest tests/test_transcripts.py -q`
Expected: `11 passed`

- [ ] **Step 5: Commit**

```bash
git add barra_de_uso/transcripts.py tests/test_transcripts.py
git commit -m "feat: lectura incremental de transcripts con dedupe por message.id"
```

---

### Task 6: Caché del estado (`cache.py`)

**Files:**
- Create: `barra_de_uso/cache.py`
- Test: `tests/test_cache.py`

- [ ] **Step 1: Escribir los tests**

```python
import json

from barra_de_uso.cache import VERSION, cargar, estado_vacio, guardar, ruta_cache


def test_ruta_cache_usa_variable_de_entorno(cache_temporal):
    assert ruta_cache("abc-123_X") == cache_temporal / "abc-123_X.json"


def test_ruta_cache_rechaza_ids_inseguros(cache_temporal):
    assert ruta_cache(None) is None
    assert ruta_cache("../etc/passwd") is None
    assert ruta_cache("a/b") is None
    assert ruta_cache("") is None


def test_guardar_y_cargar_ida_y_vuelta(cache_temporal):
    ruta = ruta_cache("s1")
    estado = estado_vacio()
    estado["archivos"]["/x.jsonl"] = {"inodo": 7, "offset": 100}
    estado["mensajes"]["m1"] = {"modelo": "kimi-k3", "in": 1, "cr": 2, "cw": 3, "out": 4}
    guardar(ruta, estado)
    assert cargar(ruta) == estado
    assert [p.name for p in cache_temporal.iterdir()] == ["s1.json"]  # sin temporales sueltos


def test_cache_inexistente_parte_vacio(cache_temporal):
    assert cargar(cache_temporal / "nada.json") == estado_vacio()


def test_cache_corrupto_parte_vacio(cache_temporal):
    cache_temporal.mkdir()
    ruta = cache_temporal / "s1.json"
    ruta.write_text("{no es json", encoding="utf-8")
    assert cargar(ruta) == estado_vacio()


def test_cache_de_otra_version_parte_vacio(cache_temporal):
    cache_temporal.mkdir()
    ruta = cache_temporal / "s1.json"
    ruta.write_text(json.dumps({"version": VERSION + 1, "archivos": {}, "mensajes": {}}), encoding="utf-8")
    assert cargar(ruta) == estado_vacio()


def test_cache_con_forma_invalida_parte_vacio(cache_temporal):
    cache_temporal.mkdir()
    ruta = cache_temporal / "s1.json"
    malo = {"version": VERSION, "archivos": {}, "mensajes": {"m1": {"modelo": "x", "in": "uno"}}}
    ruta.write_text(json.dumps(malo), encoding="utf-8")
    assert cargar(ruta) == estado_vacio()


def test_guardar_en_ruta_imposible_no_lanza(tmp_path):
    bloqueo = tmp_path / "archivo"
    bloqueo.write_text("x", encoding="utf-8")
    guardar(bloqueo / "sub" / "s1.json", estado_vacio())  # la carpeta padre es un archivo
```

- [ ] **Step 2: Verificar que fallan**

Run: `python3 -m pytest tests/test_cache.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'barra_de_uso.cache'`

- [ ] **Step 3: Implementar**

```python
"""Estado incremental por sesión en ~/.cache/barra-de-uso/<session_id>.json."""

from __future__ import annotations

import contextlib
import json
import os
import re
import tempfile
from pathlib import Path

from barra_de_uso.transcripts import CAMPOS

VERSION = 1
# session_id va al nombre de archivo: solo se aceptan caracteres seguros.
PATRON_SESSION_ID = re.compile(r"[A-Za-z0-9_-]+")


def carpeta_cache() -> Path:
    personalizada = os.environ.get("BARRA_DE_USO_CACHE_DIR")
    if personalizada:
        return Path(personalizada)
    return Path.home() / ".cache" / "barra-de-uso"


def ruta_cache(session_id: str | None) -> Path | None:
    if session_id is None or not PATRON_SESSION_ID.fullmatch(session_id):
        return None
    return carpeta_cache() / f"{session_id}.json"


def estado_vacio() -> dict:
    return {"version": VERSION, "archivos": {}, "mensajes": {}}


def _es_valido(datos: object) -> bool:
    if not isinstance(datos, dict) or datos.get("version") != VERSION:
        return False
    archivos = datos.get("archivos")
    mensajes = datos.get("mensajes")
    if not isinstance(archivos, dict) or not isinstance(mensajes, dict):
        return False
    for archivo in archivos.values():
        if not isinstance(archivo, dict):
            return False
        if not isinstance(archivo.get("inodo"), int) or not isinstance(archivo.get("offset"), int):
            return False
    for uso in mensajes.values():
        if not isinstance(uso, dict) or not isinstance(uso.get("modelo"), str):
            return False
        if not all(isinstance(uso.get(campo), int) for campo in CAMPOS):
            return False
    return True


def cargar(ruta: Path) -> dict:
    """Caché ilegible, corrupto o de otra versión: se parte de cero."""
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return estado_vacio()
    return datos if _es_valido(datos) else estado_vacio()


def guardar(ruta: Path, estado: dict) -> None:
    """Escritura atómica. Si falla, se ignora: la barra se imprime igual."""
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporal = tempfile.mkstemp(dir=ruta.parent, prefix=".tmp-", suffix=".json")
    except OSError:
        return
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
            json.dump(estado, archivo)
        os.replace(temporal, ruta)
    except OSError:
        with contextlib.suppress(OSError):
            os.unlink(temporal)
```

- [ ] **Step 4: Verificar que pasan**

Run: `python3 -m pytest tests/test_cache.py -q`
Expected: `8 passed`

- [ ] **Step 5: Commit**

```bash
git add barra_de_uso/cache.py tests/test_cache.py
git commit -m "feat: cache por sesion con validacion y escritura atomica"
```

---

### Task 7: Formato de tokens (`formato.py`)

**Files:**
- Create: `barra_de_uso/formato.py`
- Test: `tests/test_formato.py`

Nota: `abreviar` redondea con aritmética entera a propósito. Con floats, `round(999.95, 1)` da `999.9` por representación binaria y el caso 999_950 fallaría.

- [ ] **Step 1: Escribir los tests**

```python
import pytest

from barra_de_uso.formato import abreviar, tabla_tokens


@pytest.mark.parametrize("n, esperado", [
    (0, "0"),
    (999, "999"),
    (1000, "1.0k"),
    (12_400, "12.4k"),
    (340_149, "340.1k"),
    (999_949, "999.9k"),
    (999_950, "1.0M"),
    (1_000_000, "1.0M"),
    (1_234_567, "1.2M"),
    (12_350_000, "12.4M"),
])
def test_abreviar(n, esperado):
    assert abreviar(n) == esperado


def test_tabla_alinea_columnas_y_ordena_por_total():
    totales = {
        "glm-fast": {"in": 4_100, "cr": 90_300, "cw": 0, "out": 3_000},
        "kimi-k3": {"in": 12_400, "cr": 340_100, "cw": 0, "out": 8_200},
    }
    assert tabla_tokens(totales) == [
        "kimi-k3   in 12.4k · cr 340.1k · cw 0 · out 8.2k",
        "glm-fast  in 4.1k  · cr 90.3k  · cw 0 · out 3.0k",
    ]


def test_tabla_un_modelo():
    totales = {"deepseek-flash": {"in": 781, "cr": 67_456, "cw": 0, "out": 299}}
    assert tabla_tokens(totales) == ["deepseek-flash  in 781 · cr 67.5k · cw 0 · out 299"]


def test_tabla_empate_ordena_alfabetico():
    totales = {
        "b-modelo": {"in": 1, "cr": 0, "cw": 0, "out": 0},
        "a-modelo": {"in": 1, "cr": 0, "cw": 0, "out": 0},
    }
    assert [linea.split()[0] for linea in tabla_tokens(totales)] == ["a-modelo", "b-modelo"]
```

- [ ] **Step 2: Verificar que fallan**

Run: `python3 -m pytest tests/test_formato.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'barra_de_uso.formato'`

- [ ] **Step 3: Implementar**

```python
"""Abreviación de cantidades de tokens y tabla alineada por modelo."""

from __future__ import annotations

from barra_de_uso.transcripts import CAMPOS

SEPARADOR = " · "


def abreviar(n: int) -> str:
    """0 a 999 tal cual; luego una decimal con k o M, redondeo hacia arriba en .5 con enteros."""
    if n < 1000:
        return str(n)
    decimas_k = (n + 50) // 100
    if decimas_k < 10_000:
        return f"{decimas_k // 10}.{decimas_k % 10}k"
    decimas_m = (n + 50_000) // 100_000
    return f"{decimas_m // 10}.{decimas_m % 10}M"


def tabla_tokens(totales: dict[str, dict[str, int]]) -> list[str]:
    """Una línea por modelo, ordenadas por total descendente y luego por nombre."""
    filas = sorted(totales.items(), key=lambda par: (-sum(par[1].values()), par[0]))
    ancho_modelo = max(len(modelo) for modelo, _ in filas) + 2
    textos = [{campo: abreviar(total[campo]) for campo in CAMPOS} for _, total in filas]
    anchos = {campo: max(len(texto[campo]) for texto in textos) for campo in CAMPOS}
    lineas = []
    for (modelo, _), texto in zip(filas, textos):
        partes = [f"{campo} {texto[campo].ljust(anchos[campo])}" for campo in CAMPOS]
        lineas.append((modelo.ljust(ancho_modelo) + SEPARADOR.join(partes)).rstrip())
    return lineas
```

- [ ] **Step 4: Verificar que pasan**

Run: `python3 -m pytest tests/test_formato.py -q`
Expected: `13 passed`

- [ ] **Step 5: Commit**

```bash
git add barra_de_uso/formato.py tests/test_formato.py
git commit -m "feat: abreviacion de tokens y tabla alineada por modelo"
```

---

### Task 8: Orquestación y lanzador (`principal.py`, `barra.py`)

**Files:**
- Create: `barra_de_uso/principal.py`, `barra.py`
- Test: `tests/test_principal.py`

Notas:
- `principal()` tiene la **única** captura amplia (`except Exception`) del proyecto, comentada. No agregar otras.
- La salida se escribe como bytes UTF-8 en `sys.stdout.buffer` para que `·` y `↻` funcionen aunque el locale sea `C` (el test lo fuerza con `LC_ALL=C`).

- [ ] **Step 1: Escribir los tests**

```python
"""End to end: ejecuta barra.py como lo haría Claude Code."""

import json
import os
import subprocess
import sys
from pathlib import Path

from tests.conftest import agregar_jsonl, escribir_jsonl, respuesta

BARRA = Path(__file__).resolve().parent.parent / "barra.py"


def ejecutar(stdin: str, cache_dir: Path, base_url: str | None = None) -> subprocess.CompletedProcess:
    entorno = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_BASE_URL"}
    entorno["BARRA_DE_USO_CACHE_DIR"] = str(cache_dir)
    entorno["LC_ALL"] = "C"  # el locale no debe romper "·" ni "↻"
    if base_url is not None:
        entorno["ANTHROPIC_BASE_URL"] = base_url
    return subprocess.run(
        [sys.executable, str(BARRA)],
        input=stdin.encode("utf-8"),
        capture_output=True,
        env=entorno,
        timeout=10,
        check=False,
    )


def test_stdin_vacio(tmp_path):
    resultado = ejecutar("", tmp_path)
    assert resultado.returncode == 0
    assert resultado.stdout.decode("utf-8") == "barra-de-uso\n"
    assert resultado.stderr == b""


def test_json_invalido(tmp_path):
    resultado = ejecutar("{roto", tmp_path)
    assert resultado.returncode == 0
    assert resultado.stdout.decode("utf-8") == "barra-de-uso\n"


def test_modo_plan(tmp_path):
    payload = {
        "model": {"display_name": "Opus 5.5"},
        "rate_limits": {"five_hour": {"used_percentage": 42}, "seven_day": {"used_percentage": 18}},
    }
    resultado = ejecutar(json.dumps(payload), tmp_path)
    assert resultado.returncode == 0
    assert resultado.stdout.decode("utf-8") == "Opus 5.5 · 5h 42% · sem 18%\n"


def test_modo_otro_proveedor_con_subagente_e_incremental(tmp_path):
    transcript = escribir_jsonl(tmp_path / "proyecto" / "sesion1.jsonl", [respuesta("m1", "kimi-k3", 12_400, 340_100, 0, 8_200)] * 3)
    escribir_jsonl(
        tmp_path / "proyecto" / "sesion1" / "subagents" / "agent-a.jsonl",
        [respuesta("s1", "glm-fast", 4_100, 90_300, 0, 3_000)],
    )
    payload = {"model": {"display_name": "kimi-k3"}, "session_id": "sesion1", "transcript_path": str(transcript)}
    cache_dir = tmp_path / "cache"

    resultado = ejecutar(json.dumps(payload), cache_dir, base_url="http://localhost:4000")
    assert resultado.returncode == 0
    assert resultado.stdout.decode("utf-8") == (
        "kimi-k3   in 12.4k · cr 340.1k · cw 0 · out 8.2k\n"
        "glm-fast  in 4.1k  · cr 90.3k  · cw 0 · out 3.0k\n"
    )
    assert (cache_dir / "sesion1.json").is_file()

    agregar_jsonl(transcript, [respuesta("m2", "kimi-k3", 100, 0, 0, 0)])
    segundo = ejecutar(json.dumps(payload), cache_dir, base_url="http://localhost:4000")
    assert segundo.stdout.decode("utf-8").splitlines()[0] == "kimi-k3   in 12.5k · cr 340.1k · cw 0 · out 8.2k"


def test_otro_proveedor_sin_transcript_muestra_modelo(tmp_path):
    payload = {"model": {"display_name": "deepseek-flash"}, "transcript_path": str(tmp_path / "no.jsonl")}
    resultado = ejecutar(json.dumps(payload), tmp_path, base_url="https://api.deepseek.com/anthropic")
    assert resultado.stdout.decode("utf-8") == "deepseek-flash\n"
```

- [ ] **Step 2: Verificar que fallan**

Run: `python3 -m pytest tests/test_principal.py -q`
Expected: FAIL (barra.py no existe: returncode 2 y stdout vacío)

- [ ] **Step 3: Implementar `barra_de_uso/principal.py`**

```python
"""Punto de entrada: lee stdin, decide el modo e imprime la barra. Nunca falla hacia afuera."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from barra_de_uso.cache import cargar, estado_vacio, guardar, ruta_cache
from barra_de_uso.entrada import NOMBRE_RESPALDO, Payload, parsear_payload
from barra_de_uso.formato import tabla_tokens
from barra_de_uso.modo import es_modo_plan
from barra_de_uso.plan import linea_plan
from barra_de_uso.transcripts import actualizar_estado, archivos_de_sesion, totales_por_modelo


def lineas_otro_proveedor(payload: Payload) -> list[str]:
    if payload.transcript_path is None:
        return [payload.modelo]
    archivos = archivos_de_sesion(Path(payload.transcript_path))
    ruta = ruta_cache(payload.session_id)
    estado = cargar(ruta) if ruta is not None else estado_vacio()
    actualizar_estado(estado, archivos)
    if ruta is not None:
        guardar(ruta, estado)
    totales = totales_por_modelo(estado["mensajes"])
    return tabla_tokens(totales) if totales else [payload.modelo]


def generar_salida(texto: str, base_url: str | None, ahora: datetime) -> str:
    payload = parsear_payload(texto)
    if es_modo_plan(base_url):
        return linea_plan(payload, ahora)
    return "\n".join(lineas_otro_proveedor(payload))


def nombre_de_respaldo(texto: str) -> str:
    try:
        return parsear_payload(texto).modelo
    except (ValueError, TypeError):
        return NOMBRE_RESPALDO


def principal() -> int:
    texto = ""
    try:
        texto = sys.stdin.read()
        salida = generar_salida(texto, os.environ.get("ANTHROPIC_BASE_URL"), datetime.now(timezone.utc))
    except Exception:  # Red de seguridad única del proyecto: la barra nunca muestra un traceback.
        salida = nombre_de_respaldo(texto)
    # Bytes UTF-8 directos: "·" y "↻" no dependen del locale del proceso.
    sys.stdout.buffer.write((salida + "\n").encode("utf-8"))
    sys.stdout.flush()
    return 0
```

- [ ] **Step 4: Implementar `barra.py`**

```python
#!/usr/bin/env python3
"""Lanzador del status line. Claude Code ejecuta este archivo."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from barra_de_uso.principal import principal  # noqa: E402

if __name__ == "__main__":
    sys.exit(principal())
```

Run: `chmod +x barra.py`

- [ ] **Step 5: Verificar que pasan**

Run: `python3 -m pytest tests/test_principal.py -q`
Expected: `5 passed`

- [ ] **Step 6: Suite completa**

Run: `python3 -m pytest -q`
Expected: `65 passed`

- [ ] **Step 7: Commit**

```bash
git add barra_de_uso/principal.py barra.py tests/test_principal.py
git commit -m "feat: orquestacion, lanzador y red de seguridad"
```

---

### Task 9: Verificación final

- [ ] **Step 1: Sin em dashes**

Run: `grep -rnP '\x{2014}' --include=*.py --include=*.toml --include=*.md . || echo "Sin em dashes"`
Expected: `Sin em dashes`

- [ ] **Step 2: Sin `except:` desnudo**

Run: `grep -rnE "except\s*:" barra_de_uso barra.py tests || echo "OK"`
Expected: `OK`

- [ ] **Step 3: Prueba contra un transcript real (solo lectura, caché fuera del repo)**

```bash
export BARRA_DE_USO_CACHE_DIR=/tmp/barra-de-uso-prueba
T=$(ls -t ~/.claude/projects/*/*.jsonl | head -1)
jq -nc --arg t "$T" '{model:{display_name:"prueba"},session_id:"prueba1",transcript_path:$t}' \
  | ANTHROPIC_BASE_URL=http://localhost:4000 python3 barra.py
jq -nc '{model:{display_name:"Opus 5.5"},rate_limits:{five_hour:{used_percentage:42},seven_day:{used_percentage:18,resets_at:1793084400}}}' \
  | env -u ANTHROPIC_BASE_URL python3 barra.py
rm -rf /tmp/barra-de-uso-prueba
```
Expected: la primera muestra una o más filas `modelo  in ... · cr ... · cw ... · out ...`. La segunda muestra exactamente `Opus 5.5 · 5h 42% · sem 18% ↻ mar 04:00` (1793084400 es martes 27-oct-2026 04:00 en Chile; si se corre ese mismo martes, muestra solo `04:00`, que también es correcto). No pegar esta salida en el repo.

- [ ] **Step 4: Reportar a Juan**

Resumen corto: tests pasando (con la salida de pytest), la salida de los dos comandos del Step 3 y la lista de commits (`git log --oneline`). Recordarle que el push y la instalación quedan pendientes de su OK.

---

### Task 10: Instalación (solo con confirmación explícita de Juan)

- [ ] **Step 1: Pedir confirmación**

Mensaje para Juan: "¿Instalo la barra en `~/.claude/settings.json`? Agrego este bloque (o reemplazo el `statusLine` actual si existe):"

```json
"statusLine": {
  "type": "command",
  "command": "python3 /home/juan-galaz/Escritorio/Proyectos/barra-de-uso/barra.py"
}
```

- [ ] **Step 2: Con el OK, editar el archivo y validar que sigue siendo JSON válido**

Run: `jq . ~/.claude/settings.json > /dev/null && echo "JSON valido"`
Expected: `JSON valido`

- [ ] **Step 3: Pedirle a Juan que abra una sesión nueva con `claude` y otra con `ds_mode` y confirme que la barra aparece**
