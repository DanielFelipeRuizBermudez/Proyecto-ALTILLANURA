from pathlib import Path

import numpy as np
import pandas as pd
import pytest

BLOQUE = 67


def raster_de_prueba():
    mapa = np.zeros((2 * BLOQUE, 2 * BLOQUE), dtype=np.uint8)
    mapa[:BLOQUE, :BLOQUE] = 21
    mapa[:BLOQUE, BLOQUE:] = 12
    mapa[:BLOQUE, BLOQUE:BLOQUE + 33] = 35
    mapa[BLOQUE:, :BLOQUE] = 3
    return mapa


def test_celdas_de_2_km_son_bloques_de_67_pixeles(moran, transformacion):
    _, bloque, _ = moran.armar_grilla(raster_de_prueba(), transformacion(), 0)
    assert bloque == BLOQUE


def test_porcentaje_de_cada_cobertura_por_celda(moran, transformacion):
    celdas, _, desconocidos = moran.armar_grilla(raster_de_prueba(), transformacion(), 0)
    tabla = celdas.set_index(["fila", "columna"])
    assert len(celdas) == 3
    assert tabla.loc[(0, 0), "pct_agropecuario"] == pytest.approx(100)
    assert tabla.loc[(0, 1), "pct_agropecuario"] == pytest.approx(33 / 67 * 100)
    assert tabla.loc[(0, 1), "pct_sabana"] == pytest.approx(34 / 67 * 100)
    assert tabla.loc[(1, 0), "pct_bosque"] == pytest.approx(100)
    assert tabla.loc[(1, 0), "pct_agropecuario"] == pytest.approx(0)
    assert desconocidos == []


def test_porcentaje_sobre_pixeles_con_dato(moran, transformacion):
    mapa = np.zeros((BLOQUE, 2 * BLOQUE), dtype=np.uint8)
    mapa[:40, :BLOQUE] = 21
    mapa[:20, BLOQUE:] = 21
    celdas, _, _ = moran.armar_grilla(mapa, transformacion(), 0)
    assert list(celdas["columna"]) == [0]
    assert celdas["frac_valida"].iloc[0] == pytest.approx(40 / 67)
    assert celdas["pct_agropecuario"].iloc[0] == pytest.approx(100)


def test_centro_de_la_celda_en_grados(moran, transformacion):
    celdas, _, _ = moran.armar_grilla(raster_de_prueba(), transformacion(), 0)
    primera = celdas.set_index(["fila", "columna"]).loc[(0, 0)]
    pixel = transformacion().a
    assert primera["lon"] == pytest.approx(-73.0 + 33.5 * pixel)
    assert primera["lat"] == pytest.approx(4.0 - 33.5 * pixel)


def test_avisa_codigos_de_clase_desconocidos(moran, transformacion):
    mapa = raster_de_prueba()
    mapa[0, 0] = 99
    _, _, desconocidos = moran.armar_grilla(mapa, transformacion(), 0)
    assert desconocidos == [99]


def test_origen_nacional_queda_en_5_y_2_millones(moran):
    celdas = pd.DataFrame({"lon": [-73.0, -72.0], "lat": [4.0, 4.0]})
    resultado = moran.a_coordenadas_colombia(celdas, "EPSG:4326")
    assert resultado["x_9377"].iloc[0] == pytest.approx(5_000_000, abs=1)
    assert resultado["y_9377"].iloc[0] == pytest.approx(2_000_000, abs=1)


def test_un_grado_al_este_son_unos_111_km(moran):
    celdas = pd.DataFrame({"lon": [-73.0, -72.0], "lat": [4.0, 4.0]})
    resultado = moran.a_coordenadas_colombia(celdas, "EPSG:4326")
    assert 110_000 < resultado["x_9377"].iloc[1] - resultado["x_9377"].iloc[0] < 112_000
    assert abs(resultado["y_9377"].iloc[1] - 2_000_000) < 500


def test_ocho_vecinas_a_menos_de_2_9_km(moran, malla):
    w = moran.matriz_pesos(malla(3, 3), 2900)
    vecinas = np.diff(w.indptr)
    assert vecinas[4] == 8
    assert vecinas[0] == 3
    assert np.allclose(np.asarray(w.sum(axis=1)).ravel(), 1)


def test_gradiente_da_moran_positivo_y_significativo(moran, malla, generador):
    xy = malla(15, 15)
    w = moran.matriz_pesos(xy, 2900)
    observado, p_valor, z = moran.prueba_moran(xy[:, 0] + xy[:, 1], w, 999, generador)
    assert observado > 0.8
    assert p_valor == pytest.approx(0.001)
    assert z > 3


def test_tablero_de_ajedrez_da_moran_menos_uno(moran, malla):
    xy = malla(10, 10)
    fila, columna = np.divmod(np.arange(100), 10)
    w = moran.matriz_pesos(xy, 2100)
    assert moran.indice_moran(((fila + columna) % 2).astype(float), w) == pytest.approx(-1)


def test_valores_al_azar_no_tienen_autocorrelacion(moran, malla, generador):
    xy = malla(20, 20)
    w = moran.matriz_pesos(xy, 2900)
    assert abs(moran.indice_moran(generador.normal(size=len(xy)), w)) < 0.15


def test_moran_global_es_el_promedio_de_los_locales(moran, malla, generador):
    xy = malla(12, 12)
    valores = generador.normal(size=len(xy)) + xy[:, 0] / 2000
    w = moran.matriz_pesos(xy, 2900)
    local, _, _ = moran.moran_local(valores, w, 99, generador)
    assert local.mean() == pytest.approx(moran.indice_moran(valores, w))


def test_zonas_alto_alto_y_bajo_bajo(moran, malla, generador):
    xy = malla(20, 20)
    valores = np.where(xy[:, 0] < 20_000, 90.0, 5.0) + generador.normal(0, 1, len(xy))
    w = moran.matriz_pesos(xy, 2900)
    _, _, zona = moran.moran_local(valores, w, 199, generador)
    columna = np.arange(len(xy)) % 20
    fila = np.arange(len(xy)) // 20
    interior = (fila > 0) & (fila < 19)
    assert np.mean(zona[interior & (columna == 2)] == "Alto-Alto") > 0.9
    assert np.mean(zona[interior & (columna == 17)] == "Bajo-Bajo") > 0.9


def test_zonas_coinciden_con_el_cuadrante(moran, malla, generador):
    xy = malla(15, 15)
    valores = generador.normal(size=len(xy)) + np.where(xy[:, 1] < 10_000, 3.0, 0.0)
    w = moran.matriz_pesos(xy, 2900)
    _, _, zona = moran.moran_local(valores, w, 99, generador)
    z = valores - valores.mean()
    rezago = w @ z
    assert np.all(z[zona == "Alto-Alto"] > 0) and np.all(rezago[zona == "Alto-Alto"] > 0)
    assert np.all(z[zona == "Bajo-Bajo"] < 0) and np.all(rezago[zona == "Bajo-Bajo"] < 0)


def test_alcance_es_la_primera_banda_sin_relacion(moran):
    corr = pd.DataFrame({"desde_km": [0, 3, 6, 10], "moran_i": [0.8, 0.4, -0.05, -0.1], "p_valor": [0.005, 0.005, 0.3, 0.01]})
    assert moran.alcance(corr) == 6


def test_alcance_mayor_que_la_ultima_banda(moran):
    corr = pd.DataFrame({"desde_km": [0, 3], "moran_i": [0.8, 0.4], "p_valor": [0.005, 0.005]})
    assert np.isnan(moran.alcance(corr))
    assert moran.texto_alcance(np.nan) == f"más de {moran.BANDAS_KM[-1]} km"


@pytest.mark.parametrize("archivo, codigo", [
    ("cobertura_2024_PuertoLopez.tif", 50573),
    ("cobertura_2024_PuertoGaitan.tif", 50568),
    ("cobertura_2024_Mapiripan.tif", 50325),
    ("cobertura_2024_PuertoCarreño.tif", 99001),
    ("cobertura_2024_LaPrimavera.tif", 99524),
    ("cobertura_2024_SantaRosalia.tif", 99624),
    ("cobertura_2024_Cumaribo.tif", 99773),
])
def test_identifica_el_municipio_por_el_nombre_del_archivo(moran, archivo, codigo):
    assert moran.identificar(Path(archivo))[0] == codigo