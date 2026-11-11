import re
import unicodedata

import pandas as pd

from config import COD_REGION, EVA, MUNICIPIOS, NOMBRE_REGION, PROCESADOS

LLAVES = ["cod_mun", "municipio", "anio"]


def cargar_mapbiomas():
    return pd.read_csv(PROCESADOS / "mapbiomas_largo.csv")


def cargar_eva():
    ruta = EVA / "eva_altillanura_anual.csv"
    if not ruta.exists():
        return None
    return pd.read_csv(ruta)


def _buscar_municipio(nombre_o_codigo):
    if isinstance(nombre_o_codigo, int):
        return nombre_o_codigo
    for codigo, (nombre, _) in MUNICIPIOS.items():
        if _slug(nombre) == _slug(nombre_o_codigo):
            return codigo
    raise ValueError(f"Municipio no reconocido: {nombre_o_codigo}. Opciones: {[n for n, _ in MUNICIPIOS.values()]}")


def _slug(texto):
    texto = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", texto.lower()).strip("_")


def serie(clase, municipio=None, nivel="nivel_1", datos=None):
    datos = cargar_mapbiomas() if datos is None else datos
    filtro = datos[datos[nivel] == clase]
    if filtro.empty:
        raise ValueError(f"Clase no encontrada en {nivel}: {clase}. Opciones: {sorted(datos[nivel].unique())}")
    if municipio is not None:
        filtro = filtro[filtro["cod_mun"] == _buscar_municipio(municipio)]
    s = filtro.groupby("anio")["hectareas"].sum().sort_index()
    s.index = pd.PeriodIndex(s.index.astype(str), freq="Y")
    s.name = f"{clase} - {municipio if municipio is not None else NOMBRE_REGION}"
    return s


def tabla_ancha(nivel="nivel_1", datos=None):
    datos = cargar_mapbiomas() if datos is None else datos
    por_municipio = datos.pivot_table(index=LLAVES, columns=nivel, values="hectareas", aggfunc="sum").reset_index()
    region = datos.pivot_table(index="anio", columns=nivel, values="hectareas", aggfunc="sum").reset_index()
    region.insert(0, "municipio", NOMBRE_REGION)
    region.insert(0, "cod_mun", COD_REGION)
    tabla = pd.concat([por_municipio, region], ignore_index=True)
    tabla.columns.name = None
    return tabla


def eva_ancha(variable="area_sembrada_ha", eva=None, minimo_ha=0):
    eva = cargar_eva() if eva is None else eva
    if eva is None:
        return None
    total = eva.groupby(LLAVES, as_index=False)[variable].sum(min_count=1).rename(columns={variable: f"eva_total_{variable}"})
    importantes = eva.groupby("cultivo")[variable].max()
    cultivos = importantes[importantes > minimo_ha].index
    por_cultivo = eva[eva["cultivo"].isin(cultivos)].pivot_table(index=LLAVES, columns="cultivo", values=variable, aggfunc="sum")
    por_cultivo.columns = [f"eva_{_slug(c)}" for c in por_cultivo.columns]
    return total.merge(por_cultivo.reset_index(), on=LLAVES, how="left")


def cruce_mapbiomas_eva(variable="area_sembrada_ha", minimo_ha=1000, datos=None, eva=None):
    eva = cargar_eva() if eva is None else eva
    if eva is None:
        return None
    datos = cargar_mapbiomas() if datos is None else datos
    clases = {
        "Mosaico de agricultura y pastos": "mb_mosaico_agricultura_pastos",
        "Aceite de palma": "mb_palma",
        "Plantación forestal": "mb_plantacion_forestal",
        "Praderas / herbáceas": "mb_praderas_herbaceas",
    }
    n1 = datos[datos["nivel_1"] == "Zona agrícola y ganadera"].groupby(LLAVES)["hectareas"].sum().rename("mb_agricola_ganadera")
    n2 = datos[datos["nivel_2"].isin(clases)].pivot_table(index=LLAVES, columns="nivel_2", values="hectareas", aggfunc="sum")
    n2 = n2.rename(columns=clases)
    mb = pd.concat([n1, n2], axis=1).reset_index()
    cruce = mb.merge(eva_ancha(variable, eva, minimo_ha), on=["cod_mun", "anio"], how="inner", suffixes=("", "_eva"))
    cruce = cruce.drop(columns=[c for c in cruce.columns if c.endswith("_eva")])
    cruce["eva_sobre_mb_agricola"] = cruce[f"eva_total_{variable}"] / cruce["mb_agricola_ganadera"]
    return cruce.sort_values(["cod_mun", "anio"])


CATALOGO = {
    "mb_area_agropecuaria": ("Área agropecuaria (cultivos + pastos)", "MapBiomas", "ha"),
    "mb_pct_territorio_agropecuario": ("Porcentaje del territorio que es agropecuario", "MapBiomas", "%"),
    "mb_sabana": ("Sabana natural (praderas / herbáceas)", "MapBiomas", "ha"),
    "mb_perdida_sabana_anual": ("Sabana natural perdida en el año", "MapBiomas", "ha"),
    "mb_humedal": ("Humedales", "MapBiomas", "ha"),
    "mb_bosque": ("Bosque (incluye bosque inundado)", "MapBiomas", "ha"),
    "mb_plantacion_forestal": ("Plantación forestal", "MapBiomas", "ha"),
    "mb_palma": ("Palma de aceite detectada por satélite", "MapBiomas", "ha"),
    "mb_infraestructura": ("Infraestructura", "MapBiomas", "ha"),
    "eva_sembrada_total": ("Área sembrada, todos los cultivos", "EVA", "ha"),
    "eva_sembrada_maiz": ("Área sembrada de maíz", "EVA", "ha"),
    "eva_sembrada_soya": ("Área sembrada de soya", "EVA", "ha"),
    "eva_sembrada_palma": ("Área sembrada de palma de aceite", "EVA", "ha"),
    "eva_produccion_maiz": ("Producción de maíz", "EVA", "t"),
    "eva_rendimiento_maiz": ("Rendimiento de maíz", "EVA", "t/ha"),
    "eva_produccion_soya": ("Producción de soya", "EVA", "t"),
    "eva_rendimiento_soya": ("Rendimiento de soya", "EVA", "t/ha"),
    "pct_area_agropecuaria_cultivada": ("Porcentaje del área agropecuaria que es cultivo", "EVA + MapBiomas", "%"),
}


def construir_series(municipio=None, datos=None, eva=None):
    datos = cargar_mapbiomas() if datos is None else datos
    eva = cargar_eva() if eva is None else eva
    if municipio is not None:
        codigo = _buscar_municipio(municipio)
        datos = datos[datos["cod_mun"] == codigo]
        eva = eva[eva["cod_mun"] == codigo] if eva is not None else None

    def mb(clase, nivel):
        return datos[datos[nivel] == clase].groupby("anio")["hectareas"].sum()

    total = datos.groupby("anio")["hectareas"].sum()
    s = pd.DataFrame(index=sorted(datos["anio"].unique()))
    s["mb_area_agropecuaria"] = mb("Zona agrícola y ganadera", "nivel_1")
    s["mb_pct_territorio_agropecuario"] = s["mb_area_agropecuaria"] / total * 100
    s["mb_sabana"] = mb("Praderas / herbáceas", "nivel_2")
    s["mb_perdida_sabana_anual"] = -s["mb_sabana"].diff()
    s["mb_humedal"] = mb("Humedal", "nivel_2")
    s["mb_bosque"] = mb("Formación forestal", "nivel_1")
    s["mb_plantacion_forestal"] = mb("Plantación forestal", "nivel_2")
    s["mb_palma"] = mb("Aceite de palma", "nivel_2")
    s["mb_infraestructura"] = mb("Infraestructura", "nivel_2")

    if eva is not None and not eva.empty:
        anios_eva = sorted(eva["anio"].unique())
        s = s.reindex(sorted(set(s.index) | set(anios_eva)))

        def ev(cultivo, variable):
            sub = eva if cultivo is None else eva[eva["cultivo"] == cultivo]
            return sub.groupby("anio")[variable].sum(min_count=1).reindex(anios_eva).fillna(0)

        s["eva_sembrada_total"] = ev(None, "area_sembrada_ha")
        s["eva_sembrada_maiz"] = ev("MAIZ", "area_sembrada_ha")
        s["eva_sembrada_soya"] = ev("SOYA", "area_sembrada_ha")
        s["eva_sembrada_palma"] = ev("PALMA DE ACEITE", "area_sembrada_ha")
        for cultivo, nombre in [("MAIZ", "maiz"), ("SOYA", "soya")]:
            produccion = ev(cultivo, "produccion_t")
            cosechada = ev(cultivo, "area_cosechada_ha")
            s[f"eva_produccion_{nombre}"] = produccion
            s[f"eva_rendimiento_{nombre}"] = (produccion / cosechada).where(cosechada > 0)
        s["pct_area_agropecuaria_cultivada"] = s["eva_sembrada_total"] / s["mb_area_agropecuaria"] * 100

    s.index.name = "anio"
    return s