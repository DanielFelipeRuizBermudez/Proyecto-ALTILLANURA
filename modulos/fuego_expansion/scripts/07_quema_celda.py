"""Fracción quemada por celda de la grilla común con los mapas anuales de MapBiomas Fuego."""
from contextlib import ExitStack, closing
from importlib import import_module
import sqlite3

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import geometry_mask
from rasterio.windows import Window
from rasterio.windows import transform as transformacion_ventana

import config as cfg

espacial = import_module("06_conversion_cumaribo")

# Único periodo con mapas de fuego en los siete municipios. Cumaribo tiene mapas desde
# 2000, pero se recorta a la misma ventana para que todas las celdas midan lo mismo.
ANIOS = tuple(range(2015, 2026))


def quema_municipio(archivos, geometria, lado=2000, alto_bloque=512):
    """Suma por celda el área observada y el área quemada dentro de un municipio.

    archivos: {año: ruta del TIFF}. geometria: polígono del municipio en EPSG:4326.
    Solo cuentan los píxeles con el centro dentro del polígono, así dos municipios
    vecinos nunca suman el mismo píxel. Un píxel está quemado si su valor es mayor que 0.
    """
    anios = sorted(archivos)
    with ExitStack() as stack:
        stack.enter_context(rasterio.Env(GDAL_CACHEMAX=128 * 1024 * 1024))
        quemas = [stack.enter_context(rasterio.open(archivos[t])) for t in anios]
        base = quemas[0]
        espacial._comprobar_cuadricula(base, quemas)
        ids_bloque, area_ha, celdas = espacial._geometria(base, lado)
        n = len(celdas)
        pixeles = np.zeros(n)
        observada = np.zeros(n)
        quemada = np.zeros((len(anios), n))
        alguna_vez = np.zeros(n)

        for inicio in range(0, base.height, alto_bloque):
            fin = min(inicio + alto_bloque, base.height)
            ventana = Window(0, inicio, base.width, fin - inicio)
            dentro = geometry_mask([geometria], out_shape=(fin - inicio, base.width),
                                   transform=transformacion_ventana(ventana, base.transform),
                                   invert=True)
            if not dentro.any():
                continue
            ids = ids_bloque(inicio, fin)[dentro]
            pesos = np.broadcast_to(area_ha[inicio:fin, None], dentro.shape)[dentro]
            pixeles += np.bincount(ids, minlength=n)
            observada += np.bincount(ids, weights=pesos, minlength=n)
            alguna = np.zeros(ids.shape, dtype=bool)
            for k, mapa in enumerate(quemas):
                quema = mapa.read(1, window=ventana, masked=True).filled(0)[dentro] > 0
                quemada[k] += np.bincount(ids[quema], weights=pesos[quema], minlength=n)
                alguna |= quema
            alguna_vez += np.bincount(ids[alguna], weights=pesos[alguna], minlength=n)

    tabla = pd.DataFrame({"id_celda": celdas["id_celda"], "n_pixeles": pixeles,
                          "observada_ha": observada, "alguna_vez_ha": alguna_vez})
    for k, t in enumerate(anios):
        tabla[f"quemada_{t}_ha"] = quemada[k]
    return tabla.loc[tabla["n_pixeles"] > 0].reset_index(drop=True)


def construir(anios=ANIOS):
    """Arma las tablas por celda de los siete municipios.

    Devuelve (resumen, anual, control):
      resumen  una fila por celda de la grilla común (quema_celda.csv)
      anual    una fila por celda y año (quema_celda_anual.csv)
      control  área quemada por municipio y año según los mapas, para contrastarla
               con las estadísticas de la plataforma
    """
    anios = tuple(anios)
    municipios = gpd.read_file(cfg.COMUNES / "altillanura_municipios.gpkg").to_crs("EPSG:4326")
    municipios["mpio_cdpmp"] = municipios["mpio_cdpmp"].astype(str).str.zfill(5)
    limites = municipios.set_index("mpio_cdpmp").geometry
    cols_anio = [f"quemada_{t}_ha" for t in anios]

    partes, control = [], []
    for cod, slug in cfg.SLUG.items():
        archivos = espacial.archivos_anuales(cfg.CRUDOS / f"mapbiomas_fire_{slug}_tiff")
        faltan = [t for t in anios if t not in archivos]
        if faltan:
            raise ValueError(f"Faltan mapas de fuego de {slug}: {faltan}")
        parte = quema_municipio({t: archivos[t] for t in anios}, limites[f"{cod:05d}"])
        partes.append(parte)
        control.append(pd.DataFrame({"mpio_cdpmp": f"{cod:05d}", "municipio": cfg.NOMBRE[cod],
                                     "anio": anios, "quemada_mapas_ha": parte[cols_anio].sum().to_numpy()}))
    # una celda del límite recibe píxeles de dos municipios: se suman
    suma = pd.concat(partes, ignore_index=True).groupby("id_celda", as_index=False).sum()

    with closing(sqlite3.connect(cfg.COMUNES / "grilla_2km.gpkg")) as con:
        grilla = pd.read_sql("SELECT id_celda, mpio_cdpmp FROM grilla", con)
    grilla["mpio_cdpmp"] = grilla["mpio_cdpmp"].astype(str).str.zfill(5)
    fuera = suma.loc[~suma["id_celda"].isin(grilla["id_celda"])]
    if len(fuera):
        print(f"Celdas con píxeles que no están en la grilla común: {len(fuera):,} "
              f"({fuera['observada_ha'].sum():,.0f} ha)")
    tabla = grilla.merge(suma, on="id_celda", how="left", validate="one_to_one")
    tabla["n_pixeles"] = tabla["n_pixeles"].fillna(0).astype(int)

    # Las celdas sin píxeles quedan vacías (no hay área para dividir).
    area = tabla["observada_ha"].where(tabla["observada_ha"] > 0)
    pct = 100 * tabla[cols_anio].div(area, axis=0)
    resumen = tabla[["id_celda", "mpio_cdpmp", "n_pixeles"]].copy()
    resumen["quema_media_anual_pct"] = pct.mean(axis=1)
    resumen["quema_alguna_vez_pct"] = 100 * tabla["alguna_vez_ha"] / area
    resumen["anios_con_quema"] = (tabla[cols_anio] > 0).sum(axis=1).where(area.notna()).astype("Int64")

    pct.columns = list(anios)
    anual = (pct.assign(id_celda=tabla["id_celda"])
             .melt(id_vars="id_celda", var_name="anio", value_name="quema_pct")
             .sort_values(["id_celda", "anio"], ignore_index=True))
    anual["anio"] = anual["anio"].astype(int)
    return resumen, anual, pd.concat(control, ignore_index=True)
