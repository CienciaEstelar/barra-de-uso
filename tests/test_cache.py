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
