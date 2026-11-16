"""Conversiones de pradera, exposición a fuego y agrupamientos en Cumaribo."""
from contextlib import ExitStack, closing
from pathlib import Path
import re
import sqlite3

import numpy as np
import pandas as pd
from pyproj import Transformer
import rasterio
from rasterio.windows import Window

from utils import fdr_bh

PRADERA = 12
AGRO = (9, 21, 35)
NODATA_SALIDA = 65535
# Las celdas son las de datos/comunes/grilla_2km.gpkg: cuadrados de 2 km en EPSG:9377 con
# esquinas en múltiplos de 2.000 m. EPSG:6933 (área equivalente) solo mide la superficie
# de cada píxel; no define celdas.
CRS_CELDAS = "EPSG:9377"
CRS_AREA = "EPSG:6933"


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
    """Área de los píxeles por fila y marco de celdas de la grilla común que cubre el ráster."""
    lon = base.transform.c + np.arange(base.width + 1) * base.transform.a
    lat = base.transform.f + np.arange(base.height + 1) * base.transform.e
    a_area = Transformer.from_crs(base.crs, CRS_AREA, always_xy=True)
    x, _ = a_area.transform(lon[:2], np.zeros(2))
    _, y = a_area.transform(np.zeros_like(lat), lat)
    area_ha = (x[1] - x[0]) * -np.diff(y) / 10000

    # En EPSG:9377 la celda de un píxel depende a la vez de su longitud y su latitud, así
    # que se asigna píxel a píxel. Los extremos de x e y están en el borde del ráster.
    lon_c = (lon[:-1] + lon[1:]) / 2
    lat_c = (lat[:-1] + lat[1:]) / 2
    a_celdas = Transformer.from_crs(base.crs, CRS_CELDAS, always_xy=True)
    borde_lon = np.concatenate([lon_c, lon_c, np.full(lat_c.size, lon_c[0]), np.full(lat_c.size, lon_c[-1])])
    borde_lat = np.concatenate([np.full(lon_c.size, lat_c[0]), np.full(lon_c.size, lat_c[-1]), lat_c, lat_c])
    bx, by = a_celdas.transform(borde_lon, borde_lat)
    col0, fila0 = int(np.floor(bx.min() / lado)), int(np.floor(by.min() / lado))
    ancho = int(np.floor(bx.max() / lado)) - col0 + 1
    alto = int(np.floor(by.max() / lado)) - fila0 + 1
    columna = np.arange(ancho * alto) % ancho + col0
    fila = np.arange(ancho * alto) // ancho + fila0
    km = lado // 1000
    celdas = pd.DataFrame({
        # mismo formato que el cuaderno 02: esquina inferior izquierda en km
        "id_celda": [f"x{c * km}_y{f * km}" for c, f in zip(columna, fila)],
        "x_m": (columna + 0.5) * lado,
        "y_m": (fila + 0.5) * lado,
    })

    def ids_bloque(inicio, fin):
        """Índice de celda de cada píxel de las filas inicio a fin, por su centro."""
        lon2, lat2 = np.meshgrid(lon_c, lat_c[inicio:fin])
        x9, y9 = a_celdas.transform(lon2, lat2)
        return ((np.floor(y9 / lado).astype(np.int64) - fila0) * ancho
                + np.floor(x9 / lado).astype(np.int64) - col0)

    return ids_bloque, area_ha, celdas


def analizar_conversiones(cobertura, fuego, salida, lado=2000, alto_bloque=512):
    """Resume primeras conversiones confirmadas y escribe su año como GeoTIFF."""
    if lado % 1000:
        raise ValueError("El lado de la celda debe ser un múltiplo de 1.000 m.")
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
        ids_bloque, area_ha, celdas = _geometria(base, lado)
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
            ids = ids_bloque(inicio, fin)
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
    celdas["conversion_por_1000_ha_anio"] = _tasa(celdas, "pradera_ha_anio", 1000)
    return resumen, contraste, celdas


def unir_grilla(celdas, ruta_grilla):
    """Deja las celdas que están en la grilla común y les agrega municipio y área.

    Devuelve también las que quedan fuera: píxeles del ráster más allá del límite de la
    Altillanura que usa la grilla.
    """
    with closing(sqlite3.connect(ruta_grilla)) as con:
        grilla = pd.read_sql("SELECT id_celda, mpio_cdpmp, area_km2 FROM grilla", con)
    grilla["mpio_cdpmp"] = grilla["mpio_cdpmp"].astype(str).str.zfill(5)
    unidas = grilla.merge(celdas, on="id_celda", how="inner", validate="one_to_one")
    fuera = celdas.loc[~celdas["id_celda"].isin(grilla["id_celda"])]
    return unidas.reset_index(drop=True), fuera


def _tasa(tabla, denominador, escala):
    base = tabla[denominador]
    return escala * tabla["conversion_ha"] / base.where(base > 0)


def moran_local(celdas, minimo_ha_anio=100, permutaciones=999, semilla=42, lado_km=2):
    """Moran local con vecindad reina y prueba condicional bilateral.

    La vecindad sale de id_celda (esquina inferior izquierda en km, cada lado_km).
    """
    if permutaciones < 1:
        raise ValueError("Se requiere al menos una permutación.")
    d = celdas[celdas["pradera_ha_anio"] >= minimo_ha_anio].copy()
    esquina = d["id_celda"].str.extract(r"^x(-?\d+)_y(-?\d+)$").astype(int) // lado_km
    posiciones = list(zip(esquina[1], esquina[0]))
    indices = {pos: i for i, pos in enumerate(posiciones)}
    vecinos = [
        [indices[f + df, c + dc] for df in (-1, 0, 1) for dc in (-1, 0, 1)
         if (df or dc) and (f + df, c + dc) in indices]
        for f, c in posiciones
    ]
    activas = np.flatnonzero([bool(v) for v in vecinos])
    d = d.iloc[activas].copy()
    tasas = d["conversion_por_1000_ha_anio"].to_numpy()
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
