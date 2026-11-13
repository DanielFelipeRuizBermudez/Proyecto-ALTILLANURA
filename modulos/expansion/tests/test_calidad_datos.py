import re

import numpy as np
import pandas as pd
import pytest

from config import MAPAS_TIF, MAPBIOMAS_CRUDOS, MUNICIPIOS

ANIOS = [str(anio) for anio in range(1985, 2025)]
CRUDOS = sorted(MAPBIOMAS_CRUDOS.glob("*.csv"))
MAPAS = sorted(MAPAS_TIF.glob("*.tif"))
PIXEL_GRADOS = 0.00026949458523585647


def leer(ruta):
    tabla = pd.read_csv(ruta)
    tabla["Level 2"] = tabla["Level 2"].fillna("").str.strip()
    return tabla


@pytest.fixture(params=CRUDOS, ids=lambda ruta: ruta.stem)
def crudo(request):
    return leer(request.param)


def test_hay_un_csv_por_municipio():
    codigos = [int(re.match(r"(\d{5})_", ruta.name).group(1)) for ruta in CRUDOS]
    assert sorted(codigos) == sorted(MUNICIPIOS)


def test_columnas_y_anios_completos(crudo):
    assert list(crudo.columns) == ["Level 1", "Level 2", *ANIOS]


def test_hectareas_numericas_y_no_negativas(crudo):
    valores = crudo[ANIOS].apply(pd.to_numeric, errors="coerce")
    assert not valores.isna().any().any()
    assert (valores >= 0).all().all()


def test_clases_conocidas(crudo, union):
    assert set(crudo["Level 1"]) <= set(union.NIVEL_1)
    assert set(crudo.loc[crudo["Level 2"] != "", "Level 2"]) <= set(union.NIVEL_2)


def test_sin_clases_repetidas(crudo):
    assert not crudo.duplicated(["Level 1", "Level 2"]).any()


def test_area_del_municipio_constante_entre_anios(crudo):
    total = crudo.loc[crudo["Level 2"] != "", ANIOS].astype(float).sum()
    assert (total.max() - total.min()) / total.mean() < 1e-6


def test_nivel_1_es_la_suma_de_sus_clases(crudo):
    niveles = crudo[crudo["Level 2"] == ""].set_index("Level 1")[ANIOS].astype(float)
    clases = crudo[crudo["Level 2"] != ""].groupby("Level 1")[ANIOS].sum().astype(float)
    clases = clases.reindex(niveles.index, fill_value=0.0)
    assert np.allclose(clases.to_numpy(), niveles.to_numpy(), rtol=1e-6, atol=1e-3)


@pytest.mark.skipif(not MAPAS, reason="mapas_tif no está en esta copia; se trae con dvc pull")
@pytest.mark.parametrize("ruta", MAPAS, ids=lambda ruta: ruta.stem)
def test_mapas_tif(ruta, moran):
    mapa, transformacion, sin_dato, crs = moran.leer_mapa(ruta)
    assert crs == "EPSG:4326"
    assert abs(transformacion.a) == pytest.approx(PIXEL_GRADOS, rel=1e-6)
    assert set(np.unique(mapa).tolist()) - {sin_dato} <= set(moran.CLASES)
    assert moran.identificar(ruta)[0] in MUNICIPIOS
