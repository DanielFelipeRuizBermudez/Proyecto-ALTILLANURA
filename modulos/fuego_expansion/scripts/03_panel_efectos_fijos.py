"""Asociaciones contemporánea y rezagada en el panel municipal."""
import numpy as np
import pandas as pd

import config as cfg
from utils import _within


def _coeficientes(y, x, municipios, anios, efectos_anio):
    if efectos_anio:
        # Se reconstruyen las indicadoras con los años presentes en cada muestra.
        niveles = np.unique(anios)[1:]
        x = np.column_stack([x, anios[:, None] == niveles])
    y, x, _, _ = _within(y, x, municipios)
    beta, _, rango, _ = np.linalg.lstsq(x, y, rcond=None)
    if rango != x.shape[1]:
        return None
    return beta[:3]


def ajustar(panel, exposicion="tasa_quema_natural", resultado="d_agro_pct",
            efectos_anio=False, excluir_anios_limitados=False,
            excluir_salto_carreno=False, bloque=3, B=2000):
    """Ajusta municipio, exposición en t y t−1 y lluvia seca en t.

    Remuestrea bloques de años calendario con todos sus municipios.
    Los rezagos se calculan antes de los filtros en el panel de entrada.
    """
    cols = [exposicion, f"{exposicion}_rez1", "lluvia_seca_mm"]
    datos = panel
    if excluir_anios_limitados:
        datos = datos.loc[~(datos["fuego_calidad_limitada"] | datos["fuego_calidad_limitada_rez1"])]
    if excluir_salto_carreno:
        datos = datos.loc[~((datos["cod_mun"] == 99001) & (datos["anio"] == 2014))]
    datos = datos.dropna(subset=[resultado, *cols])
    if datos.empty:
        raise ValueError("El modelo no tiene observaciones completas.")
    y = datos[resultado].to_numpy(float)
    x = datos[cols].to_numpy(float)
    municipios, anios = datos[["cod_mun", "anio"]].to_numpy().T
    beta = _coeficientes(y, x, municipios, anios, efectos_anio)
    if beta is None:
        raise ValueError("La especificación no identifica todos los coeficientes.")

    calendario = np.arange(anios.min(), anios.max() + 1)
    if not 1 <= bloque <= len(calendario) or B < 1:
        raise ValueError("Se requieren bloques válidos y al menos una réplica.")
    ventanas = np.lib.stride_tricks.sliding_window_view(calendario, bloque)
    por_anio = {a: np.flatnonzero(anios == a) for a in calendario}
    cantidad = (len(calendario) + bloque - 1) // bloque
    rng = np.random.default_rng(cfg.SEMILLA)
    replicas = []
    for _ in range(B):
        remuestra = rng.integers(len(ventanas), size=cantidad)
        seleccion = ventanas[remuestra].ravel()[:len(calendario)]
        idx = np.concatenate([por_anio[a] for a in seleccion])
        if idx.size:
            estimacion = _coeficientes(y[idx], x[idx], municipios[idx], anios[idx], efectos_anio)
            if estimacion is not None:
                replicas.append(estimacion)
    if not replicas:
        raise ValueError("Ninguna réplica de bootstrap permitió identificar el modelo.")
    inf, sup = np.percentile(replicas, [2.5, 97.5], axis=0)
    return pd.DataFrame({
        "variable": cols,
        "coef": beta,
        "ic95_inf": inf,
        "ic95_sup": sup,
        "n": len(datos),
        "municipios": datos["cod_mun"].nunique(),
        "anios": datos["anio"].nunique(),
        "bloque": bloque,
        "replicas_validas": len(replicas),
        "replicas_solicitadas": B,
    })
