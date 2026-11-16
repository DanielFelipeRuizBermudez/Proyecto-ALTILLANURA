"""Composición y tendencias del área quemada por cobertura."""
import pandas as pd
from scipy import stats

from utils import mann_kendall


SERIES_TENDENCIA = {
    "focos_seca_terra": "Focos MODIS dic-mar (Terra)",
    "quem_total_ha": "Área quemada total (ha)",
    "quem_natural_ha": "Vegetación natural no forestal quemada (ha)",
    "quem_agro_ha": "Área agropecuaria quemada (ha)",
    "tasa_quema_natural": "Tasa de quema natural no forestal (%)",
    "tasa_quema_agro": "Tasa de quema agropecuaria (%)",
}


def composicion(p):
    g = p.groupby("municipio")
    t = pd.DataFrame(
        {
            "quemado_medio_ha": g["quem_total_ha"].mean(),
            "pct_natural": g["quem_natural_ha"].sum() / g["quem_total_ha"].sum() * 100,
            "pct_agro": g["quem_agro_ha"].sum() / g["quem_total_ha"].sum() * 100,
            "pct_bosque": g["quem_bosque_ha"].sum() / g["quem_total_ha"].sum() * 100,
            "pct_sin_vegetacion": g["quem_sin_veg_ha"].sum() / g["quem_total_ha"].sum() * 100,
            "tasa_quema_natural_media": g["tasa_quema_natural"].mean(),
            "tasa_quema_agro_media": g["tasa_quema_agro"].mean(),
        }
    )
    t["razon_tasa_agro_natural"] = t["tasa_quema_agro_media"] / t["tasa_quema_natural_media"]
    # Comparación por pares dentro de cada año con ambas tasas disponibles.
    for m, d in p.groupby("municipio"):
        diferencias = (d["tasa_quema_agro"] - d["tasa_quema_natural"]).dropna()
        if not diferencias.empty:
            t.loc[m, "p_wilcoxon_agro_vs_natural"] = stats.wilcoxon(diferencias).pvalue
    return t.round(3).sort_values("quemado_medio_ha", ascending=False)


def tendencias(p, reg):
    filas = []
    for var, etq in SERIES_TENDENCIA.items():
        tau, pv, sen = mann_kendall(reg[var].to_numpy(), reg["anio"].to_numpy())
        filas.append(("Altillanura", etq, tau, pv, sen))
        for m, d in p.groupby("municipio"):
            tau, pv, sen = mann_kendall(d[var].to_numpy(float), d["anio"].to_numpy())
            filas.append((m, etq, tau, pv, sen))
    return pd.DataFrame(filas, columns=["territorio", "serie", "tau", "p", "pendiente_sen_por_anio"]).round(4)
