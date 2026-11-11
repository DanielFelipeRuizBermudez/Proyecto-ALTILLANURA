import numpy as np
import pandas as pd

from config import MUNICIPIOS, NOMBRE_REGION


def test_de_csv_crudos_a_pronostico_arima(union, arima, tmp_path, monkeypatch):
    monkeypatch.setattr(union, "PROCESADOS", tmp_path)
    union.main()
    archivo = tmp_path / "mapbiomas_largo.csv"
    largo = pd.read_csv(archivo, encoding="utf-8-sig")
    assert {"cod_mun", "municipio", "anio", "nivel_1", "nivel_2", "hectareas"} <= set(largo.columns)
    assert set(largo["cod_mun"]) == set(MUNICIPIOS)

    monkeypatch.setattr(arima, "ARCHIVO_MAPBIOMAS", archivo)
    series = arima.cargar_series()
    assert len(series) == len(MUNICIPIOS) + 1
    assert all(len(serie) == 40 for serie in series.values())
    suma = sum(serie for nombre, serie in series.items() if nombre != NOMBRE_REGION)
    assert np.allclose(series[NOMBRE_REGION].to_numpy(), suma.to_numpy())

    resultado = arima.modelar("Puerto López", series["Puerto López"])
    assert resultado["modelo"]["modelos_probados"] == (arima.MAXIMO_P + 1) * (arima.MAXIMO_Q + 1)
    pronostico = resultado["pronostico"]
    assert list(pronostico["anio"]) == list(range(2025, 2025 + arima.HORIZONTE))
    assert np.isfinite(pronostico["pronostico"]).all()
    assert (pronostico["limite_inferior"] <= pronostico["pronostico"]).all()
    assert (pronostico["pronostico"] <= pronostico["limite_superior"]).all()


def test_de_raster_a_zonas_de_moran(moran, transformacion, tmp_path, monkeypatch):
    monkeypatch.setattr(moran, "SALIDA_GRAFICAS", tmp_path)
    monkeypatch.setattr(moran, "PERMUTACIONES", 99)
    monkeypatch.setattr(moran, "PERMUTACIONES_CORRELOGRAMA", 19)
    bloque = 67
    mapa = np.full((10 * bloque, 10 * bloque), 12, dtype=np.uint8)
    mapa[:, : 4 * bloque] = 21

    celdas, _, _ = moran.armar_grilla(mapa, transformacion(), 0)
    celdas = moran.a_coordenadas_colombia(celdas, "EPSG:4326")
    celdas, resultado, corr, zonas, ruta = moran.analizar("Prueba", celdas, np.random.default_rng(1))

    assert resultado["n_celdas"] == 100
    assert resultado["celdas_sin_vecinos"] == 0
    assert resultado["moran_i"] > 0.5
    assert resultado["p_valor"] < 0.05
    assert not corr.empty
    assert zonas["n_celdas"].sum() == 100
    assert set(celdas["zona_lisa"]) <= set(moran.ZONAS)
    assert ruta.exists()
