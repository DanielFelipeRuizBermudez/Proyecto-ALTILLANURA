"""Resúmenes descriptivos del panel municipal."""
import pandas as pd

import config as cfg


def descriptivo(p):
    g = p.groupby("municipio")
    t = pd.DataFrame(
        {
            "area_total_ha": g["area_total_ha"].first(),
            "agro_2001_ha": p[p.anio == cfg.ANIO_INI].set_index("municipio")["agro_ha"],
            "agro_2024_ha": p[p.anio == cfg.ANIO_FIN].set_index("municipio")["agro_ha"],
            "expansion_media_ha_anio": g["d_agro_ha"].mean(),
            "cambio_medio_pp_territorio": g["d_agro_pct"].mean(),
            "crecimiento_medio_pct_agro_previo": g["crec_agro_pct"].mean(),
            "focos_seca_medios": g["focos_seca_total"].mean(),
            "focos_seca_por_100km2": g["focos_seca_dens"].mean(),
            "focos_seca_terra_medios": g["focos_seca_terra"].mean(),
            "quemado_medio_ha_anio": g["quem_total_ha"].mean(),
            "quemado_medio_pct_municipio": g["quem_total_pct"].mean(),
            "quemado_agro_medio_ha_anio": g["quem_agro_ha"].mean(),
            "quemado_sabana_medio_ha_anio": g["quem_natural_ha"].mean(),
            "lluvia_seca_media_mm": g["lluvia_seca_mm"].mean(),
        }
    )
    t["expansion_total_ha"] = t["agro_2024_ha"] - t["agro_2001_ha"]
    t = t.round(2).sort_values("area_total_ha", ascending=False)
    t.insert(0, "mpio_cdpmp", t.index.map(cfg.DIVIPOLA))
    return t
