# barra-de-uso: spec de diseño

Fecha: 2026-10-21. Autor: Juan Galaz (diseño con Claude Opus 5.5).

## 1. Objetivo

Status line propio para Claude Code. Muestra:

- **Modo plan** (Claude Code con login OAuth de Anthropic): uso de la ventana de 5 h y de la semanal, con la hora de reset en hora de Chile continental.
- **Modo otro proveedor** (`ds_mode`, `kimi_mode`, `glm_51`, `gemini_mode`, `multi_mode`, `or_mode`): tokens acumulados de la sesión, separados por modelo (principal y subagentes) y por tipo (entrada, lectura de caché, escritura de caché, salida), para que Juan multiplique por el precio de cada modelo.

Fuera de alcance (YAGNI): cálculo de costos, precios, uso semanal por modelo (Opus/Sonnet), overage, ritmo de consumo, git, contexto, temas de colores, TUI de configuración, llamadas de red de cualquier tipo.

## 2. Restricciones

- Python 3.12, **solo biblioteca estándar** en tiempo de ejecución. pytest solo para tests.
- **Sin red. Sin leer credenciales.** Nunca abrir `~/.claude/.credentials.json`. Todo sale del JSON que Claude Code entrega por stdin y de los transcripts locales.
- Convenciones de `~/Escritorio/Proyectos/CLAUDE.md`: funciones, variables y comentarios en español; sin `except:` desnudo; sin em dashes en ningún archivo; tests con pytest.
- Repo **público** (`CienciaEstelar/barra-de-uso`): ningún dato real de Juan en el repo. Los fixtures de test se escriben a mano (sintéticos). Los payloads reales capturados se guardan fuera del repo.
- Tiempo por ejecución: objetivo < 150 ms con caché tibio. Medido con el borrador sobre transcripts reales: 0,09 a 0,13 s tibio; la primera lectura de una sesión de 127 MB tarda 1,4 s (solo una vez por sesión).

## 3. Referencia

`pcvelz/ccstatusline-usage` (MIT, TypeScript) se usa como referencia de comportamiento, no se copia código. Datos tomados de ahí y verificados:

- El payload trae `rate_limits.five_hour` y `rate_limits.seven_day`, cada uno con `used_percentage` (puede ser fraccional, ej. 23.4) y `resets_at` (segundos epoch Unix; puede llegar como string, hay que convertir a número). Ambos campos pueden ser `null` o faltar. `rate_limits` completo puede ser `null` o faltar.
- El proceso del status line hereda las variables de entorno de Claude Code (el fork lee `ANTHROPIC_BASE_URL` al renderizar).
- Entradas de transcript con `isApiErrorMessage: true` se descartan.

Verificado en transcripts reales de Juan (no está en el fork):

- Cada respuesta de la API aparece **repetida** (3 veces en lo observado) con el mismo `message.id`. Hay que deduplicar.
- Un mismo `message.id` puede traer usage distinto entre repeticiones (casos con valores reales y casos en cero). Regla: por `message.id` quedarse con la entrada de **mayor suma** `input + cache_read + cache_creation + output`.
- Hay entradas con `message.model == "<synthetic>"`: se descartan.
- Los subagentes escriben en `<transcript sin .jsonl>/subagents/**/agent-*.jsonl`, con subcarpetas anidadas (ej. `subagents/workflows/wf_xxx/agent-yyy.jsonl`). Hay que buscar **recursivo**.
- DeepSeek sí reporta `cache_read_input_tokens` (ej. 781 de entrada normal y 67.456 de caché en una misma respuesta).

## 4. Entrada

JSON por stdin. Campos usados (todos opcionales, el programa no puede caerse si falta cualquiera):

| Campo | Uso |
|---|---|
| `model.display_name` | nombre en modo plan y fallback |
| `model.id` | fallback si falta `display_name` |
| `session_id` | clave del caché |
| `transcript_path` | transcript principal |
| `rate_limits.five_hour.{used_percentage,resets_at}` | modo plan |
| `rate_limits.seven_day.{used_percentage,resets_at}` | modo plan |

Entorno: `ANTHROPIC_BASE_URL`.

## 5. Detección de modo

- `ANTHROPIC_BASE_URL` ausente, vacía, o cuyo host es `api.anthropic.com` → **modo plan**.
- Cualquier otro valor (ej. `https://api.deepseek.com/anthropic`, `http://localhost:4000`) → **modo otro proveedor**.

No se usa la presencia de `rate_limits` para decidir: en el primer refresco de una sesión `claude` puede no venir todavía.

## 6. Salida

Texto plano por stdout, sin colores ANSI. Siempre código de salida 0.

### 6.1 Modo plan (una línea)

```
Opus 5.5 · 5h 42% ↻ 16:30 · sem 18% ↻ mar 04:00
```

- Separador: ` · ` (espacio, punto medio U+00B7, espacio).
- Porcentaje: `round()` a entero, sin decimales.
- Reset: `resets_at` convertido a `America/Santiago` con `zoneinfo`.
  - Si la fecha local del reset es la misma que la fecha local de ahora: solo `HH:MM`.
  - Si no: día abreviado en español + `HH:MM`. Días: `lun mar mié jue vie sáb dom`.
- Ventana sin `used_percentage`: `5h --` o `sem --`.
- Ventana sin `resets_at`: se omite ` ↻ ...` de esa ventana.
- `rate_limits` ausente o `null`: `Opus 5.5 · 5h -- · sem --`.

Dato de control: el reset semanal de Juan es martes 04:00 hora de Chile continental. Sirve para validar la conversión, pero el valor mostrado sale siempre de `resets_at`.

### 6.2 Modo otro proveedor (una línea por modelo)

```
kimi-k3   in 12.4k · cr 340.1k · cw 0 · out 8.2k
glm-fast  in 4.1k  · cr 90.3k  · cw 0 · out 3.0k
```

- Una fila por valor distinto de `message.model`, sumando transcript principal y subagentes.
- Orden: por total de tokens (suma de los cuatro), descendente. Empate: alfabético.
- `in` = `input_tokens`, `cr` = `cache_read_input_tokens`, `cw` = `cache_creation_input_tokens`, `out` = `output_tokens`. Campo ausente o `null` cuenta como 0.
- Abreviación: `n < 1000` → entero (`0`, `999`); `n < 1_000_000` → una decimal + `k` (`12.4k`, `1000` → `1.0k`); si no → una decimal + `M` (`1.2M`). Si al redondear a una decimal un valor en `k` llega a `1000.0k` (ej. 999_950), se muestra como `1.0M`.
- Alineación: el nombre del modelo se rellena a la derecha hasta el más largo + 2 espacios. Cada valor abreviado (`12.4k`) se rellena a la derecha hasta el más largo de su columna, para que los ` · ` queden en la misma columna.
- Sin datos todavía (sin transcript o sin entradas válidas): una línea con el nombre del modelo del payload.

### 6.3 Fallback de errores

Si cualquier cosa falla (stdin vacío, JSON inválido, transcript ilegible, caché corrupto): imprimir el nombre del modelo si se pudo leer, si no `barra-de-uso`. Nunca traceback por stdout. Nunca línea vacía.

## 7. Arquitectura

```
barra-de-uso/
  barra.py                      # lanzador: agrega su carpeta a sys.path y llama a principal()
  barra_de_uso/
    __init__.py
    principal.py                # orquesta: leer stdin, detectar modo, formatear, imprimir, fallback
    entrada.py                  # parsear payload a dataclass Payload (tolerante a faltantes)
    modo.py                     # es_modo_plan(base_url) -> bool
    plan.py                     # linea_plan(payload, ahora) -> str
    transcripts.py              # archivos de la sesión, lectura incremental, dedupe, totales por modelo
    cache.py                    # cargar/guardar estado incremental (escritura atómica)
    formato.py                  # abreviar(n), tabla_tokens(totales) -> list[str]
  tests/
    __init__.py
    conftest.py                 # ayudantes que arman transcripts SINTÉTICOS en tmp_path
    test_entrada.py
    test_modo.py
    test_plan.py
    test_formato.py
    test_transcripts.py
    test_cache.py
    test_principal.py           # end to end vía subprocess sobre barra.py
  pyproject.toml                # solo config de pytest, sin dependencias
  .gitignore
```

Cada módulo es puro salvo `principal.py` (stdin/stdout), `transcripts.py` (lee archivos) y `cache.py` (lee/escribe caché). `plan.py` recibe `ahora` como parámetro para poder testear sin depender del reloj.

## 8. Lectura incremental y caché

- Archivo: `~/.cache/barra-de-uso/<session_id>.json`. Si falta `session_id`, no se usa caché (se lee todo).
- Contenido:
  ```json
  {
    "version": 1,
    "archivos": {"<ruta absoluta>": {"inodo": 123, "offset": 45678}},
    "mensajes": {"<message.id>": {"modelo": "kimi-k3", "in": 1, "cr": 2, "cw": 3, "out": 4}}
  }
  ```
- Por cada archivo de la sesión: si el inodo cambió o el tamaño actual es menor que `offset`, leer desde 0. Si no, leer desde `offset`.
- Procesar solo líneas completas (terminadas en `\n`). El `offset` avanza hasta el final de la última línea completa. Una línea final a medio escribir se relee en el próximo refresco.
- Línea que no es JSON válido: se ignora y se sigue.
- Fusionar cada entrada en `mensajes` con la regla de mayor suma (sección 3). Releer desde 0 es seguro porque la fusión es idempotente.
- Entradas válidas: `type == "assistant"`, `message.id` presente, `message.usage` presente, `message.model` distinto de `<synthetic>`, `isApiErrorMessage` distinto de `true`.
- Escritura atómica: archivo temporal en la misma carpeta + `os.replace`.
- Caché ilegible o con `version` distinta: se descarta y se reconstruye desde 0.
- Error al escribir caché: se ignora (la salida de ese refresco igual se imprime).
- Archivos de la sesión: `transcript_path` + `rglob("agent-*.jsonl")` bajo `<transcript_path sin .jsonl>/subagents/`. Si `transcript_path` no existe: sin datos.

## 9. Errores

- Excepciones esperadas se capturan donde ocurren y con tipo específico: `json.JSONDecodeError`, `OSError`, `ValueError`, `TypeError`, `KeyError`.
- `principal()` tiene una única red de seguridad `except Exception` que imprime el fallback de 6.3. Es la única captura amplia del proyecto y va comentada como tal. Nada de `except:` desnudo.
- Nada se imprime por stderr en operación normal.

## 10. Tests

pytest, `python3 -m pytest` desde la raíz. Cobertura mínima declarada: todas las reglas de las secciones 5, 6 y 8 tienen al menos un test. Casos obligatorios:

- Modo: sin variable, vacía, `https://api.anthropic.com`, DeepSeek, `http://localhost:4000`.
- Plan: reset hoy (solo hora), reset otro día (día + hora), martes 04:00 Santiago desde un epoch fijo, porcentaje fraccional redondeado, `resets_at` como string, ventana faltante, `rate_limits` null, horario de verano y de invierno de Chile (martes 04:00 en octubre, UTC-3, y en junio, UTC-4), fecha comparada en hora de Chile y no en UTC, día con tilde (sáb).
- Formato: 0, 999, 1000, 12_400, 999_949 (`999.9k`), 999_950 (`1.0M`), 1_000_000, alineación con nombres de largo distinto.
- Transcripts: duplicados por `message.id` (se cuenta una vez), duplicado con usage distinto (gana el mayor), `<synthetic>` descartado, `isApiErrorMessage` descartado, línea JSON rota ignorada, línea final incompleta, subagente anidado en `subagents/workflows/wf_x/`, dos modelos (principal y subagente) en filas separadas.
- Caché: segunda lectura solo procesa lo agregado, archivo truncado se relee, caché corrupto se reconstruye, sin `session_id` funciona sin caché.
- End to end: stdin vacío, JSON inválido, payload plan, payload otro proveedor con transcript sintético. Siempre exit 0 y stdout no vacío.

Los tests que tocan caché usan `tmp_path` y una variable de entorno `BARRA_DE_USO_CACHE_DIR` para no escribir en `~/.cache` real. Esa variable es la única configuración del programa.

## 11. Instalación (manual, la confirma Juan)

En `~/.claude/settings.json`:

```json
"statusLine": {
  "type": "command",
  "command": "python3 /home/juan-galaz/Escritorio/Proyectos/barra-de-uso/barra.py"
}
```

El implementador **no** modifica `~/.claude/settings.json` sin confirmación explícita de Juan.

## 12. Limitaciones conocidas

- Los tokens son por archivo de transcript de la sesión. Si una sesión reanudada copia historia de otra, esa historia se cuenta en ambas.
- Si Anthropic cambia el formato de `rate_limits` o de los transcripts, la barra cae al fallback en vez de mostrar datos erróneos.
- La forma real del payload en Claude Code 2.1.296 se valida con una captura (tarea 0 del plan) antes de implementar.
- Cantidades sobre mil millones se muestran en `M` (ej. `1484.7M`). No se agrega unidad `G` (YAGNI).

## 13. Validación previa del diseño

Antes de escribir el plan se implementó un borrador completo (65 tests pasando) y se corrió contra transcripts reales de Juan, solo lectura. En una sesión `ds_mode` con 39 subagentes, la barra mostró `deepseek-flash  in 1.2M · cr 33.5M · cw 0 · out 436.7k`, y un cálculo independiente con `jq` (dedupe por `message.id`, mayor uso) dio exactamente 1.246.785 / 33.547.520 / 0 / 436.721.
