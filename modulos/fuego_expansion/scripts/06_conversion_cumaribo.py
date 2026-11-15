"""Conversiones de pradera, exposición a fuego y agrupamientos en Cumaribo."""
from contextlib import ExitStack
from pathlib import Path
import re

import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import Window
from rasterio.warp import transform

from utils import fdr_bh

PRADERA = 12
AGRO = (9, 21, 35)
NODATA_SALIDA = 65535


def archivos_anuales(carpeta):
    """Indexa TIFF por año y rechaza ambigüedades."""
    archivos = {}
    for ruta in sorted(Path(carpeta).iterdir()):
        if ruta.suffix.lower() not in {".tif", ".tiff"}:
            continue
        prefijo = re.match(r"^(\d{4})(?:_|-)", ruta.name)
        if not prefijo:
            raise ValueError(f"El nombre no empieza por el año: {ruta.name}")
        anio = int(prefijo[1])
        if anio in archivos:
            raise ValueError(f"Hay más de un TIFF para {anio} en {carpeta}.")
        archivos[anio] = ruta
    return archivos


def _comprobar_cuadricula(base, capas):
    if (base.crs.to_epsg() != 4326 or base.transform.b != 0 or base.transform.d != 0
            or base.transform.a <= 0 or base.transform.e >= 0):
        raise ValueError("Se requiere una cuadrícula WGS 84 sin rotación, orientada al norte.")
    for capa in capas:
        if (capa.shape, capa.crs, capa.transform, capa.count) != (
                base.shape, base.crs, base.transform, 1):
            raise ValueError(f"La cuadrícula no coincide con la cobertura inicial: {capa.name}")


def _geometria(base, lado):
    """Ubica los centros en celdas métricas y calcula el área por fila."""
    lon = base.transform.c + np.arange(base.width + 1) * base.transform.a
    lat = base.transform.f + np.arange(base.height + 1) * base.transform.e
    x, _ = transform(base.crs, "EPSG:6933", lon.tolist(), np.zeros_like(lon).tolist())
    _, y = transform(base.crs, "EPSG:6933", np.zeros_like(lat).tolist(), lat.tolist())
    col = np.floor((np.asarray(x[:-1]) + x[1:]) / (2 * lado)).astype(int)
    fila = np.floor((np.asarray(y[:-1]) + y[1:]) / (2 * lado)).astype(int)
    area_ha = np.diff(x)[0] * -np.diff(y) / 10000
    ancho = col.max() - col.min() + 1
    ids_fila = (fila - fila.min()) * ancho
    ids_col = col - col.min()
    tam = (fila.max() - fila.min() + 1) * ancho
    celdas = pd.DataFrame({
        "fila": np.arange(tam) // ancho + fila.min(),
        "columna": np.arange(tam) % ancho + col.min(),
    })
    return ids_fila, ids_col, area_ha, celdas


def analizar_conversiones(cobertura, fuego, salida, lado=2000, alto_bloque=512):
    """Resume primeras conversiones confirmadas y escribe su año como GeoTIFF."""
    anios = sorted(cobertura)
    if len(anios) < 3 or anios != list(range(anios[0], anios[-1] + 1)):
        raise ValueError("Se requieren al menos tres coberturas de años consecutivos.")
    finales = anios[1:]
    exposiciones = [t - 2 for t in finales if t - 2 in fuego and t - 2 in cobertura]
    anual = np.zeros((len(finales), 2))
    por_fuego = np.zeros((len(finales), 2, 2))

    with ExitStack() as stack:
        stack.enter_context(rasterio.Env(GDAL_CACHEMAX=128 * 1024 * 1024))
        mapas = [stack.enter_context(rasterio.open(cobertura[t])) for t in anios]
        quemas = {t: stack.enter_context(rasterio.open(fuego[t])) for t in exposiciones}
        base = mapas[0]
        _comprobar_cuadricula(base, [*mapas, *quemas.values()])
        ids_fila, ids_col, area_ha, celdas = _geometria(base, lado)
        totales = np.zeros((2, len(celdas)))
        perfil = base.profile.copy()
        perfil.update(dtype="uint16", nodata=NODATA_SALIDA, compress="deflate", predictor=2)
        raster = stack.enter_context(rasterio.open(salida, "w", **perfil))
        raster.set_band_description(1, "Primer año de conversión persistente; último año provisional")
        raster.update_tags(anio_provisional=anios[-1], valor_sin_conversion=0)

        for inicio in range(0, base.height, alto_bloque):
            fin = min(inicio + alto_bloque, base.height)
            ventana = Window(0, inicio, base.width, fin - inicio)
            cob = [m.read(1, window=ventana, masked=True).filled(0) for m in mapas]
            ids = ids_fila[inicio:fin, None] + ids_col
            pesos = np.broadcast_to(area_ha[inicio:fin, None], ids.shape)
            primero = np.zeros(ids.shape, dtype=np.uint16)
            valido = np.zeros(ids.shape, dtype=bool)

            for i, t in enumerate(finales, start=1):
                antes, despues = cob[i - 1:i + 1]
                valido |= (antes != 0) & (despues != 0)
                elegible = (primero == 0) & (antes == PRADERA) & (despues != 0)
                confirmado = i + 1 < len(cob)
                if confirmado:
                    elegible &= cob[i + 1] != 0
                cambio = elegible & np.isin(despues, AGRO)
                if confirmado:
                    cambio &= np.isin(cob[i + 1], AGRO)
                    for k, mascara in enumerate((elegible, cambio)):
                        totales[k] += np.bincount(ids[mascara], weights=pesos[mascara],
                                                 minlength=len(celdas))
                anual[i - 1] = anual[i - 1] + [pesos[elegible].sum(), pesos[cambio].sum()]
                if t - 2 in quemas:
                    quema = quemas[t - 2].read(1, window=ventana, masked=True).filled(0) > 0
                    observado = elegible & (cob[i - 2] != 0)
                    for k, grupo in enumerate((observado & ~quema, observado & quema)):
                        por_fuego[i - 1, k] += [pesos[grupo].sum(), pesos[grupo & cambio].sum()]
                primero[cambio] = t
            primero[~valido] = NODATA_SALIDA
            raster.write(primero, 1, window=ventana)

    resumen = pd.DataFrame(anual, columns=["pradera_elegible_ha", "conversion_ha"])
    resumen.insert(0, "anio", finales)
    resumen["confirmada"] = resumen["anio"] != anios[-1]
    resumen["tasa_pct"] = _tasa(resumen, "pradera_elegible_ha", 100)
    filas = [
        (t, t - 2, t != anios[-1], grupo, *por_fuego[i, j])
        for i, t in enumerate(finales) if t - 2 in exposiciones
        for j, grupo in enumerate(("Sin quema detectada", "Con quema detectada"))
    ]
    contraste = pd.DataFrame(filas, columns=["anio", "anio_fuego", "confirmada", "grupo",
                                           "pradera_elegible_ha", "conversion_ha"])
    contraste["tasa_pct"] = _tasa(contraste, "pradera_elegible_ha", 100)
    celdas[["pradera_ha_anio", "conversion_ha"]] = totales.T
    celdas = celdas.loc[celdas["pradera_ha_anio"] > 0].copy()
    celdas["tasa_por_1000"] = _tasa(celdas, "pradera_ha_anio", 1000)
    celdas["x_m"] = (celdas["columna"] + 0.5) * lado
    celdas["y_m"] = (celdas["fila"] + 0.5) * lado
    return resumen, contraste, celdas


def _tasa(tabla, denominador, escala):
    base = tabla[denominador]
    return escala * tabla["conversion_ha"] / base.where(base > 0)


def moran_local(celdas, minimo_ha_anio=100, permutaciones=999, semilla=42):
    """Moran local con vecindad reina y prueba condicional bilateral."""
    if permutaciones < 1:
        raise ValueError("Se requiere al menos una permutación.")
    d = celdas[celdas["pradera_ha_anio"] >= minimo_ha_anio].copy()
    posiciones = list(zip(d["fila"], d["columna"]))
    indices = {pos: i for i, pos in enumerate(posiciones)}
    vecinos = [
        [indices[f + df, c + dc] for df in (-1, 0, 1) for dc in (-1, 0, 1)
         if (df or dc) and (f + df, c + dc) in indices]
        for f, c in posiciones
    ]
    activas = np.flatnonzero([bool(v) for v in vecinos])
    d = d.iloc[activas].copy()
    tasas = d["tasa_por_1000"].to_numpy()
    if len(tasas) < 3 or tasas.std() == 0:
        raise ValueError("No hay suficientes celdas vecinas con tasas variables.")
    z = (tasas - tasas.mean()) / tasas.std()
    activos = dict(zip(activas, range(len(activas))))
    ady = [[activos[j] for j in vecinos[i]] for i in activas]
    lag = np.array([z[v].mean() for v in ady])
    local = z * lag
    esperado = -(z ** 2) / (len(z) - 1)
    rng = np.random.default_rng(semilla)
    muestras = {
        k: np.array([rng.choice(len(z) - 1, k, replace=False) for _ in range(permutaciones)])
        for k in sorted({len(v) for v in ady})
    }
    p = np.empty(len(z))
    for i, v in enumerate(ady):
        muestra = muestras[len(v)]
        simulado = z[i] * z[muestra + (muestra >= i)].mean(axis=1)
        extremos = np.count_nonzero(np.abs(simulado - esperado[i]) >= abs(local[i] - esperado[i]) - 1e-12)
        p[i] = (extremos + 1) / (permutaciones + 1)
    q = fdr_bh(p)
    cuadrante = np.select(
        [(z > 0) & (lag > 0), (z < 0) & (lag < 0), (z > 0) & (lag < 0), (z < 0) & (lag > 0)],
        ["Alto–alto", "Bajo–bajo", "Alto–bajo", "Bajo–alto"], default="Sin cuadrante")
    return d.assign(moran_local=local, p_perm=p, q_fdr=q, vecinos=[len(v) for v in ady],
                    cuadrante=cuadrante, grupo_moran=np.where(q < 0.05, cuadrante, "Sin señal al 5 %"))
