import importlib
from types import SimpleNamespace

import matplotlib
import numpy as np
import pytest

matplotlib.use("Agg")

PIXEL_GRADOS = 0.00026949458523585647


@pytest.fixture(scope="session")
def union():
    return importlib.import_module("02_unir_mapbiomas")


@pytest.fixture(scope="session")
def moran():
    return importlib.import_module("07_moran_espacial")


@pytest.fixture(scope="session")
def arima():
    return importlib.import_module("08_arima")


@pytest.fixture
def generador():
    return np.random.default_rng(2026)


@pytest.fixture
def transformacion():
    def crear(lon=-73.0, lat=4.0, pixel=PIXEL_GRADOS):
        return SimpleNamespace(a=pixel, c=lon, e=-pixel, f=lat)
    return crear


@pytest.fixture
def malla():
    def crear(filas, columnas, paso=2000.0):
        fila, columna = np.divmod(np.arange(filas * columnas), columnas)
        return np.column_stack([columna * paso, fila * paso]).astype(float)
    return crear
