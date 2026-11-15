"""Funciones para armar el panel municipio-año (2001-2024) con todas las fuentes.

Entradas (datos/):
  procesados/mapbiomas_eva/mapbiomas_nivel_1_ancho.csv   cobertura MapBiomas
  procesados/mapbiomas_eva/mapbiomas_nivel_2_ancho.csv   plantación forestal
  procesados/mapbiomas_eva/cruce_mapbiomas_eva.csv       EVA (área sembrada)
  crudos/mapbiomas_fuego/fuego_<mpio>.csv                área quemada por clase
  crudos/perdida_vegetacion/perdida_veg_<mpio>.csv       supresión de vegetación
  procesados/firms_mensual_municipio.csv                 focos de calor MODIS
  procesados/chirps_mensual_municipio.csv                lluvia mensual
  procesados/oni_mensual.csv                             índice ONI

Devuelve el panel de 7 municipios x 24 años y permite agregar la serie regional.
"""
import numpy as np
import pandas as pd

import config as cfg
from utils import leer_csv

ANIOS = list(range(cfg.ANIO_INI - 1, cfg.ANIO_FIN + 1))
CODIGOS = list(cfg.MUNICIPIOS)


# ----------------------------------------------------------- MapBiomas
def cobertura() -> pd.DataFrame:
    d = leer_csv(cfg.PROCESADOS / "mapbiomas_eva" / "mapbiomas_nivel_1_ancho.csv")
    d = d[d["cod_mun"].isin(CODIGOS)].copy()
    cols = {
        "Zona agrícola y ganadera": "agro_ha",
        "Formación natural no forestal": "natural_ha",
        "Formación forestal": "bosque_ha",
        "Cuerpo de agua": "agua_ha",
        "Zona sin vegetación": "sin_veg_ha",
    }
    nivel2 = leer_csv(cfg.PROCESADOS / "mapbiomas_eva" / "mapbiomas_nivel_2_ancho.csv")
    d = d.merge(nivel2[["cod_mun", "anio", "Plantación forestal"]],
                on=["cod_mun", "anio"], how="left", validate="one_to_one")
    d = d.rename(columns=cols)
    d["agro_sin_forestal_ha"] = d["agro_ha"] - d["Plantación forestal"]
    d["area_total_ha"] = d[list(cols.values())].sum(axis=1)
    d = d.sort_values(["cod_mun", "anio"])
    por_municipio = d.groupby("cod_mun")
    consecutivos = por_municipio["anio"].diff().eq(1)
    d["area_total_ha_rez1"] = por_municipio["area_total_ha"].shift().where(consecutivos)
    d["agro_ha_rez1"] = por_municipio["agro_ha"].shift().where(consecutivos)
    for c in ("agro_ha", "agro_sin_forestal_ha", "natural_ha", "bosque_ha"):
        d[f"d_{c}"] = por_municipio[c].diff().where(consecutivos)
    for c in ("natural", "bosque"):
        d[f"d_{c}_pct"] = 100 * d[f"d_{c}_ha"] / d["area_total_ha"]
    territorio_previo = d["area_total_ha_rez1"].where(d["area_total_ha_rez1"] > 0)
    agro_previo = d["agro_ha_rez1"].where(d["agro_ha_rez1"] > 0)
    d["d_agro_pct"] = 100 * d["d_agro_ha"] / territorio_previo
    d["d_agro_sin_forestal_pct"] = 100 * d["d_agro_sin_forestal_ha"] / territorio_previo
    d["crec_agro_pct"] = 100 * d["d_agro_ha"] / agro_previo
    d["agro_pct"] = d["agro_ha"] / d["area_total_ha"] * 100
    return d[
        ["cod_mun", "anio", "area_total_ha", "agro_ha", "natural_ha", "bosque_ha",
         "agro_pct", "d_agro_sin_forestal_pct", "d_agro_ha", "d_natural_ha", "d_bosque_ha",
         "area_total_ha_rez1", "agro_ha_rez1", "d_agro_pct", "crec_agro_pct",
         "d_natural_pct", "d_bosque_pct"]
    ]


# --------------------------------------------------- MapBiomas Fuego
CLASE_FUEGO = {
    "Agricultural area": "quem_agro_ha",
    "Non-forest natural formation": "quem_natural_ha",
    "Forest formation": "quem_bosque_ha",
    "Non-vegetated area": "quem_sin_veg_ha",
}


def fuego_mapbiomas() -> pd.DataFrame:
    filas = []
    for cod, slug in cfg.SLUG.items():
        d = leer_csv(cfg.CRUDOS / "mapbiomas_fuego" / f"fuego_{slug}.csv")
        l1 = d[d["Level 2"].isna()].set_index("Level 1")
        l2 = d[d["Level 2"].notna()]
        anios = [c for c in d.columns if c.isdigit()]
        # control: la suma del nivel 2 coincide con la del nivel 1
        dif = (l1[anios].sum() - l2[anios].sum()).abs().max()
        assert dif < 1e-3, f"fuego {slug}: niveles 1 y 2 no cuadran ({dif})"
        for clase, nombre in CLASE_FUEGO.items():
            for a in anios:
                filas.append((cod, int(a), nombre, float(l1.loc[clase, a])))
    larga = pd.DataFrame(filas, columns=["cod_mun", "anio", "var", "ha"])
    ancho = larga.pivot_table(index=["cod_mun", "anio"], columns="var", values="ha").reset_index()
    ancho["quem_total_ha"] = ancho[list(CLASE_FUEGO.values())].sum(axis=1)
    return ancho


# ------------------------------------------------ pérdida de vegetación
def perdida_vegetacion() -> pd.DataFrame:
    filas = []
    for cod, slug in cfg.SLUG.items():
        d = leer_csv(cfg.CRUDOS / "perdida_vegetacion" / f"perdida_veg_{slug}.csv").set_index("Level 1")
        for a in [c for c in d.columns if c.isdigit()]:
            filas.append(
                (cod, int(a),
                 float(d.loc["Primary Vegetation Suppression", a]),
                 float(d.loc["Secondary Vegetation Suppression", a]))
            )
    out = pd.DataFrame(filas, columns=["cod_mun", "anio", "perdida_primaria_ha", "perdida_secundaria_ha"])
    out["perdida_total_ha"] = out["perdida_primaria_ha"] + out["perdida_secundaria_ha"]
    return out


# --------------------------------------------------------- FIRMS (focos)
def _anio_temporada(mes: pd.Series) -> pd.Series:
    """Año de la temporada seca: diciembre pertenece a la temporada del año siguiente."""
    p = pd.PeriodIndex(mes, freq="M")
    anio = p.year.to_numpy()
    return pd.Series(np.where(p.month == 12, anio + 1, anio), index=mes.index)


def focos() -> pd.DataFrame:
    d = leer_csv(cfg.PROCESADOS / "firms_mensual_municipio.csv")
    d = d.rename(columns={"mpio_cdpmp": "cod_mun"})
    p = pd.PeriodIndex(d["mes"], freq="M")
    d["mes_num"] = p.month
    d["anio_cal"] = p.year
    d["anio_temp"] = _anio_temporada(d["mes"])
    seca = d[d["mes_num"].isin(cfg.MESES_SECA)]
    a = seca.groupby(["cod_mun", "anio_temp"])[["focos_terra", "focos_total"]].sum()
    a.columns = ["focos_seca_terra", "focos_seca_total"]
    a.index.names = ["cod_mun", "anio"]
    b = d.groupby(["cod_mun", "anio_cal"])[["focos_terra", "focos_total"]].sum()
    b.columns = ["focos_anual_terra", "focos_anual_total"]
    b.index.names = ["cod_mun", "anio"]
    out = a.join(b, how="outer").reset_index()
    # la temporada 2001 es la primera completa (la serie empieza en 2000-11)
    # Aqua opera desde mediados de 2002: el total Terra+Aqua solo es comparable desde 2004
    out.loc[out["anio"] < 2004, ["focos_seca_total", "focos_anual_total"]] = np.nan
    out.loc[out["anio"] < cfg.ANIO_INI, ["focos_seca_terra", "focos_seca_total"]] = np.nan
    return out


# ------------------------------------------------------------------ lluvia
def lluvia() -> pd.DataFrame:
    d = leer_csv(cfg.PROCESADOS / "chirps_mensual_municipio.csv").rename(columns={"mpio_cdpmp": "cod_mun"})
    p = pd.PeriodIndex(d["mes"], freq="M")
    d["mes_num"] = p.month
    d["anio_cal"] = p.year
    d["anio_temp"] = _anio_temporada(d["mes"])
    seca = d[d["mes_num"].isin(cfg.MESES_SECA)]
    a = seca.groupby(["cod_mun", "anio_temp"]).agg(
        lluvia_seca_mm=("lluvia_mm", "sum"), normal_seca_mm=("normal_mm", "sum"), n_meses=("lluvia_mm", "size")
    )
    a = a[a["n_meses"] == 4].drop(columns="n_meses")
    a["lluvia_seca_anom_pct"] = (a["lluvia_seca_mm"] / a["normal_seca_mm"] - 1) * 100
    a.index.names = ["cod_mun", "anio"]
    # lluvia de la estación húmeda previa (abril a noviembre del año anterior)
    h = d[d["mes_num"].between(4, 11)].groupby(["cod_mun", "anio_cal"])["lluvia_mm"].agg(["sum", "size"])
    h = h[h["size"] == 8]["sum"].rename("lluvia_humeda_mm")
    h.index.names = ["cod_mun", "anio"]
    h = h.reset_index()
    h["anio"] = h["anio"] + 1  # llega como "húmeda previa" de la temporada del año siguiente
    h = h.rename(columns={"lluvia_humeda_mm": "lluvia_humeda_prev_mm"}).set_index(["cod_mun", "anio"])
    return a.join(h, how="outer").reset_index()


# --------------------------------------------------------------------- ONI
def oni() -> pd.DataFrame:
    d = leer_csv(cfg.PROCESADOS / "oni_mensual.csv", parse_dates=["fecha"])
    d["anio_cal"] = d["fecha"].dt.year
    d["mes"] = d["fecha"].dt.month
    filas = []
    for y in range(1951, 2026):
        v = d[
            ((d["anio_cal"] == y - 1) & d["mes"].isin([11, 12])) | ((d["anio_cal"] == y) & d["mes"].isin([1, 2]))
        ]["oni"]
        if len(v) == 4:
            filas.append((y, v.mean()))
    return pd.DataFrame(filas, columns=["anio", "oni_nov_feb"])


# --------------------------------------------------------------------- EVA
def eva() -> pd.DataFrame:
    d = leer_csv(cfg.PROCESADOS / "mapbiomas_eva" / "cruce_mapbiomas_eva.csv")
    return d[["cod_mun", "anio", "eva_total_area_sembrada_ha"]].rename(
        columns={"eva_total_area_sembrada_ha": "eva_sembrada_ha"}
    )


# ------------------------------------------------------------------ panel
def construir_panel() -> pd.DataFrame:
    base = pd.MultiIndex.from_product([CODIGOS, ANIOS], names=["cod_mun", "anio"]).to_frame(index=False)
    panel = base
    for t in (cobertura(), fuego_mapbiomas(), perdida_vegetacion(), focos(), lluvia(), eva()):
        panel = panel.merge(t, on=["cod_mun", "anio"], how="left", validate="one_to_one")
    panel = panel.merge(oni(), on="anio", how="left", validate="many_to_one")
    panel.insert(1, "municipio", panel["cod_mun"].map(cfg.NOMBRE))

    # Densidades por municipio y tasas por cobertura.
    km2 = panel["area_total_ha"] / 100
    panel["focos_seca_dens"] = panel["focos_seca_terra"] / km2 * 100      # focos por 100 km2
    panel["focos_anual_dens"] = panel["focos_anual_terra"] / km2 * 100
    panel["quem_total_pct"] = panel["quem_total_ha"] / panel["area_total_ha"] * 100
    panel["quem_agro_pct"] = panel["quem_agro_ha"] / panel["area_total_ha"] * 100
    panel["quem_natural_pct"] = panel["quem_natural_ha"] / panel["area_total_ha"] * 100
    panel["tasa_quema_agro"] = np.where(panel["agro_ha"] > 0, panel["quem_agro_ha"] / panel["agro_ha"] * 100, np.nan)
    panel["tasa_quema_natural"] = panel["quem_natural_ha"] / panel["natural_ha"].where(panel["natural_ha"] > 0) * 100
    panel["perdida_veg_pct"] = panel["perdida_total_ha"] / panel["area_total_ha"] * 100

    panel["fuego_calidad_limitada"] = panel["anio"].isin(cfg.ANIOS_FUEGO_LIMITADOS)
    rezago = panel[["cod_mun", "anio", "tasa_quema_natural", "focos_seca_dens",
                    "fuego_calidad_limitada"]].copy()
    rezago["anio"] += 1
    rezago = rezago.rename(columns={c: f"{c}_rez1" for c in rezago.columns[2:]})
    panel = panel.merge(rezago, on=["cod_mun", "anio"], how="left", validate="one_to_one")
    panel = panel.loc[panel["anio"] >= cfg.ANIO_INI].reset_index(drop=True)
    panel["fuego_calidad_limitada_rez1"] = panel["fuego_calidad_limitada_rez1"].astype(bool)
    return panel


def serie_regional(panel: pd.DataFrame) -> pd.DataFrame:
    """Agrega por año y recalcula las proporciones con denominadores regionales."""

    # serie regional: se suman variables extensivas y se recalculan las relativas
    ext = ["area_total_ha", "agro_ha", "natural_ha", "bosque_ha", "d_agro_ha", "d_natural_ha", "d_bosque_ha",
           "area_total_ha_rez1", "agro_ha_rez1",
           "quem_agro_ha", "quem_natural_ha", "quem_bosque_ha", "quem_sin_veg_ha", "quem_total_ha",
           "perdida_primaria_ha", "perdida_secundaria_ha", "perdida_total_ha",
           "focos_seca_terra", "focos_anual_terra", "eva_sembrada_ha"]
    reg = panel.groupby("anio")[ext].sum(min_count=1).reset_index()
    km2r = reg["area_total_ha"] / 100
    reg["d_agro_pct"] = 100 * reg["d_agro_ha"] / reg["area_total_ha_rez1"].where(reg["area_total_ha_rez1"] > 0)
    reg["crec_agro_pct"] = 100 * reg["d_agro_ha"] / reg["agro_ha_rez1"].where(reg["agro_ha_rez1"] > 0)
    reg["d_natural_pct"] = reg["d_natural_ha"] / reg["area_total_ha"] * 100
    reg["focos_seca_dens"] = reg["focos_seca_terra"] / km2r * 100
    reg["quem_total_pct"] = reg["quem_total_ha"] / reg["area_total_ha"] * 100
    reg["tasa_quema_agro"] = reg["quem_agro_ha"] / reg["agro_ha"] * 100
    reg["tasa_quema_natural"] = reg["quem_natural_ha"] / reg["natural_ha"] * 100
    # lluvia regional ponderada por área; ONI es común
    w = panel.assign(w=panel["area_total_ha"])
    for c in ("lluvia_seca_mm", "lluvia_seca_anom_pct", "lluvia_humeda_prev_mm"):
        reg[c] = w.groupby("anio").apply(lambda g, c=c: np.average(g[c], weights=g["w"]), include_groups=False).values
    clima = panel.groupby("anio")["oni_nov_feb"].first()
    reg["oni_nov_feb"] = reg["anio"].map(clima)
    reg["fuego_calidad_limitada"] = reg["anio"].isin(cfg.ANIOS_FUEGO_LIMITADOS)
    return reg
