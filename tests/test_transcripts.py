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
