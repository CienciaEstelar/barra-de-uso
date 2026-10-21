# barra-de-uso v2: spec de diseño

Fecha: 2026-10-21. Autor: Juan Galaz (diseño con Claude Opus 5.5).
Base: v1 (`2026-10-21-barra-de-uso-design.md`), ya implementada, publicada e instalada.

## 1. Objetivo

Que la barra deje de solo informar y ayude a decidir. Cuatro cambios, todos en el modo plan salvo los colores, que también llegan al modo otro proveedor:

1. **Ritmo:** junto a cada ventana, `▲` si gastas más rápido que el tiempo, `▼` si vas holgado, `=` si vas al ritmo.
2. **Colores por gravedad:** porcentajes en verde, amarillo o rojo según nivel. Columnas de tokens con color por tipo.
3. **Contexto:** `ctx 11%` con el uso de la ventana de contexto de la sesión.
4. **Último dato conocido:** al abrir una sesión, mientras Claude Code aún no entrega `rate_limits`, mostrar el último valor guardado, marcado con `~` y en tenue, en vez de `5h -- · sem --`.

Fuera de alcance (YAGNI): modo otro proveedor en una sola línea, mapa de alias a modelo real, `ctx` en modo otro proveedor, umbrales o colores configurables, reemplazo de espacios por espacios duros (NBSP) para VS Code, cálculo de costos.

## 2. Restricciones (sin cambios respecto a v1)

Python 3.12 solo stdlib; cero red; cero credenciales; cero subprocesos; nombres y comentarios en español; sin `except:` desnudo; sin em dashes; repo público sin datos reales; nunca un traceback por stdout; exit 0 siempre.

## 3. Evidencia usada para diseñar

- **Capturas reales** (Claude Code 2.1.296, en `~/.cache/barra-de-uso/capturas/`, fuera del repo):
  - `context_window.used_percentage` viene `null` en el primer refresco de la sesión y luego como entero (ej. 11, 6). `context_window_size` = 1000000.
  - En `ds_mode` el payload no trae la clave `rate_limits`.
  - Reset semanal real: martes 04:00 hora de Chile. Reset de 5 h: hora fija dentro del día.
- **Observado en vivo** (Claude Code 2.1.306): sesión recién abierta muestra `Sonnet 5.5 · 5h -- · sem --` hasta la primera respuesta. Es el problema que resuelve el punto 4.
- **Referencia `pcvelz/ccstatusline-usage`** (`src/ccstatusline.ts`): antepone `\x1b[0m` a cada línea "para anular el atenuado (dim) de Claude Code". Sin ese reinicio los colores se verían apagados.

## 4. Diseño

### 4.1 Colores (`barra_de_uso/color.py`, nuevo)

- Códigos ANSI básicos: negrita `1`, tenue `2`, rojo `31`, verde `32`, amarillo `33`, azul `34`, magenta `35`, cian `36`. Reinicio `\x1b[0m`.
- `pintar(texto, *codigos, activo)`: envuelve en `\x1b[<códigos>m...\x1b[0m`. Si `activo` es falso, no hay códigos o el texto está vacío, devuelve el texto tal cual.
- `color_nivel(porcentaje)`: verde bajo 50; amarillo desde 50; rojo desde 80. Se usa para las ventanas y para `ctx`.
- `colores_activos(entorno)`: falso si `NO_COLOR` está definida y no vacía (convención no-color.org).
- Con colores activos, **cada línea** de la salida parte con `\x1b[0m`.
- Separadores ` · ` en tenue.
- Modo otro proveedor: nombre del modelo en negrita; etiquetas `in` azul, `cr` verde, `cw` magenta, `out` amarillo; valores sin color. El relleno de alineación se calcula sobre el texto visible: **sin ANSI, la tabla es idéntica byte a byte a la de v1**.
- El fallback de errores (nombre del modelo o `barra-de-uso`) sigue sin colores.

### 4.2 Ritmo (`barra_de_uso/plan.py`)

- Duraciones: `5h` = 18000 s, `sem` = 604800 s.
- `transcurrido = clamp((duración - (resets_at - ahora)) / duración, 0, 1) × 100`.
- `diferencia = usado - transcurrido`. `▲` si `diferencia > 5`; `▼` si `diferencia < -5`; `=` en otro caso (el borde exacto de 5 puntos es `=`).
- Colores: `▲` rojo, `▼` verde, `=` sin color (ir al ritmo no es advertencia).
- Sin `resets_at`: sin flecha. Dato estimado (4.4): sin flecha, porque el porcentaje es viejo y compararlo con el reloj actual engañaría.
- Formato: `5h 42% ▲ ↻ 16:30`.

### 4.3 Contexto

- `Payload.contexto` = `context_window.used_percentage` (mismo parseo tolerante que el resto: número o string numérico; `null` o ausente da `None`).
- Solo modo plan, inmediatamente después del modelo: `Opus 5.5 · ctx 11% · 5h ...`. Color por `color_nivel`.
- Si es `None`, el segmento se **omite** (no `ctx --`).

### 4.4 Último dato conocido (`barra_de_uso/memoria.py`, nuevo)

- Archivo: `<carpeta_cache>/ultimo-plan.json` (misma carpeta y variable `BARRA_DE_USO_CACHE_DIR` que v1). Global, no por sesión: el plan es de la cuenta, no de la sesión.
- Formato:
  ```json
  {"version": 1,
   "cinco_horas": {"porcentaje": 42.0, "reset_epoch": 1792570800.0},
   "semanal": {"porcentaje": 18.0, "reset_epoch": 1793084400.0}}
  ```
- **Guardar** (en cada refresco del modo plan): por ventana, solo si el payload trae porcentaje **y** `resets_at` reales. Las ventanas que no vienen se conservan de la memoria previa. Si el resultado es igual a lo que ya hay, **no se escribe** (evita una escritura por refresco). Escritura atómica reutilizando `cache.guardar`.
- **Usar**: por ventana, si el payload no la trae o viene sin porcentaje, y la memoria tiene esa ventana con `reset_epoch` **en el futuro**, se rellena con `Ventana(..., estimada=True)`. Si el reset ya pasó, no se usa (después de un reset el uso real ya no es ese).
- **Mostrar**: `5h ~42% ↻ 16:30`, todo el segmento en tenue, sin flecha. El `~` hace que se entienda también sin colores.
- Memoria ausente, corrupta, de otra versión o con tipos inválidos: se trata como vacía.
- `Ventana` gana el campo `estimada: bool = False`. `Payload` gana `contexto: float | None = None`. Ambos con valor por defecto para no romper código existente.

### 4.5 Ejemplos de salida

```
Opus 5.5 · ctx 11% · 5h 42% ▲ ↻ 16:30 · sem 18% = ↻ mar 04:00     (datos reales)
Opus 5.5 · 5h ~42% ↻ 16:30 · sem ~18% ↻ mar 04:00                   (sesión recién abierta)
kimi-k3   in 12.4k · cr 340.1k · cw 0 · out 8.2k                     (otro proveedor, sin cambios de texto)
```

### 4.6 Imagen del README

- `docs/assets/generar_imagen.py` (nuevo, versionado): arma ejemplos sintéticos, llama a `linea_plan` y `tabla_tokens` **con colores**, y traduce los códigos ANSI a SVG. La imagen es literalmente la salida de la barra.
- Cada trozo de texto va con `x` explícito y `textLength`, para que no dependa de la fuente del visor (con `tspan` encadenados el render se rompía).
- README actualizado: tabla "Cómo leer el modo plan", flujo, verificación, qué hace / qué NO hace, estructura, resumen en inglés. Badge de tests a 108.

## 5. Errores

Sin cambios: la única captura amplia sigue en `principal()`. `memoria.cargar_memoria` captura `OSError` y `ValueError`; `guardar` ya ignora `OSError`.

## 6. Tests

108 en total (65 de v1 ajustados más 43 nuevos). Archivos: `test_color.py` (11), `test_memoria.py` (10), `test_entrada.py` (11), `test_plan.py` (25), `test_formato.py` (14), `test_principal.py` (8), más los de v1 sin cambios (`test_cache`, `test_modo`, `test_transcripts`). Los tests de punta a punta corren con `NO_COLOR=1` salvo los que prueban colores. `tests/conftest.py` gana `sin_ansi()`.

## 7. Validación previa del diseño

Implementado completo en un borrador antes de escribir el plan:

- 108 tests pasando.
- **Pruebas de mutación**: se rompieron a propósito tres piezas (memoria que siempre reescribe, salida sin reinicio ANSI, memoria vencida usada) y cada una hizo fallar tests.
- **Simulación del plan** sobre una copia del repo: cada tarea parte en rojo, termina en verde, la suite completa queda verde tras cada commit (76, 79, 94, 104, 105, 108) y el estado final es idéntico al borrador.
- **Payloads reales**: `Sonnet 5.5 · ctx 11% · 5h 25% ▼ ↻ 05:20 · sem 18% = ↻ mar 04:00`; con colores, la línea parte con `\x1b[0m`.
- **Tiempo**: 0,09 a 0,10 s por refresco, igual que v1.

**No validado todavía**: cómo se ven los colores y el tenue dentro de Claude Code. Eso se confirma en vivo al final del plan.

## 8. Riesgos conocidos

- La barra está **instalada** apuntando al repo: cada archivo que cambia se ve en la próxima actualización de la barra. Como la suite queda verde tras cada tarea y el fallback nunca rompe, lo peor es ver un formato intermedio durante la implementación.
- VS Code podría recortar espacios del status line (el fork usa NBSP por eso). No aplica a la terminal de Juan; queda fuera de alcance.
- Umbrales (50 %, 80 %) y margen de ritmo (5 puntos) son decisiones de diseño, no medidas.
