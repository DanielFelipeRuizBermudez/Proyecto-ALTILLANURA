import sys
import unicodedata

import pandas as pd

from config import EVA, MUNICIPIOS

URL_2006_2018 = "https://www.datos.gov.co/api/views/2pnw-mmge/rows.csv?accessType=DOWNLOAD"
URL_2019_2025 = "https://www.datos.gov.co/api/views/uejq-wxrr/rows.csv?accessType=DOWNLOAD"

COLS_2006_2018 = {
    "CÓD. DEP.": "cod_dep",
    "DEPARTAMENTO": "departamento",
    "CÓD. MUN.": "cod_mun",
    "MUNICIPIO": "municipio",
    "GRUPO DE CULTIVO": "grupo_cultivo",
    "SUBGRUPO DE CULTIVO": "subgrupo_cultivo",
    "CULTIVO": "cultivo",
    "DESAGREGACIÓN REGIONAL Y/O SISTEMA PRODUCTIVO": "desagregacion",
    "AÑO": "anio",
    "PERIODO": "periodo",
    "Área Sembrada (ha)": "area_sembrada_ha",
    "Área Cosechada (ha)": "area_cosechada_ha",
    "Producción (t)": "produccion_t",
    "Rendimiento (t/ha)": "rendimiento_t_ha",
    "CICLO DE CULTIVO": "ciclo",
}

COLS_2019_2025 = {
    "Código Dane departamento": "cod_dep",
    "Departamento": "departamento",
    "Código Dane municipio": "cod_mun",
    "Municipio": "municipio",
    "Grupo cultivo": "grupo_cultivo",
    "Subgrupo": "subgrupo_cultivo",
    "Cultivo": "cultivo",
    "Desagregación cultivo": "desagregacion",
    "Año": "anio",
    "Periodo": "periodo",
    "Área sembrada": "area_sembrada_ha",
    "Área cosechada": "area_cosechada_ha",
    "Producción": "produccion_t",
    "Rendimiento": "rendimiento_t_ha",
    "Ciclo del cultivo": "ciclo",
}

NUMERICAS = ["area_sembrada_ha", "area_cosechada_ha", "produccion_t", "rendimiento_t_ha"]
TEXTO = ["departamento", "municipio", "grupo_cultivo", "subgrupo_cultivo", "cultivo", "desagregacion", "ciclo", "periodo"]


def normalizar(texto):
    texto = "" if pd.isna(texto) else str(texto)
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return " ".join(texto.upper().split())


def a_numero(serie):
    if not pd.api.types.is_numeric_dtype(serie):
        serie = serie.astype("string").str.replace(",", "", regex=False).str.strip()
    return pd.to_numeric(serie, errors="coerce")


def cargar(origen, columnas, etiqueta):
    print(f"Leyendo {etiqueta}...")
    df = pd.read_csv(origen, dtype=str)
    reales = {normalizar(c): c for c in df.columns}
    faltan = [c for c in columnas if normalizar(c) not in reales]
    if faltan:
        sys.exit(f"{etiqueta}: no se encontraron las columnas {faltan}. Columnas disponibles: {list(df.columns)}")
    df = df[[reales[normalizar(c)] for c in columnas]]
    df.columns = list(columnas.values())
    df["cod_mun"] = a_numero(df["cod_mun"]).astype("Int64")
    df["anio"] = a_numero(df["anio"]).astype("Int64")
    for c in NUMERICAS:
        df[c] = a_numero(df[c])
    for c in TEXTO:
        df[c] = df[c].map(normalizar)
    nombres = {normalizar(n) for n, _ in MUNICIPIOS.values()}
    por_codigo = df["cod_mun"].isin(MUNICIPIOS.keys())
    por_nombre = df["departamento"].isin({"META", "VICHADA"}) & df["municipio"].isin(nombres)
    df = df[por_codigo | por_nombre].copy()
    df["fuente"] = etiqueta
    return df


def main():
    origen_a = sys.argv[1] if len(sys.argv) > 2 else URL_2006_2018
    origen_b = sys.argv[2] if len(sys.argv) > 2 else URL_2019_2025
    EVA.mkdir(parents=True, exist_ok=True)

    a = cargar(origen_a, COLS_2006_2018, "EVA 2006-2018")
    b = cargar(origen_b, COLS_2019_2025, "EVA 2019-2025")
    eva = pd.concat([a, b], ignore_index=True)

    codigos = {normalizar(n): c for c, (n, _) in MUNICIPIOS.items()}
    valido = eva["cod_mun"].isin(MUNICIPIOS.keys()).fillna(False)
    eva["cod_mun"] = eva["cod_mun"].where(valido, eva["municipio"].map(codigos)).astype(int)
    eva["municipio"] = eva["cod_mun"].map(lambda c: MUNICIPIOS[c][0])
    eva["departamento"] = eva["cod_mun"].map(lambda c: MUNICIPIOS[c][1])
    eva = eva.sort_values(["cod_mun", "cultivo", "anio", "periodo"])
    eva.to_csv(EVA / "eva_altillanura_detalle.csv", index=False, encoding="utf-8-sig")

    anual = eva.groupby(
        ["cod_mun", "municipio", "departamento", "grupo_cultivo", "cultivo", "anio"], as_index=False
    )[["area_sembrada_ha", "area_cosechada_ha", "produccion_t"]].sum(min_count=1)
    anual["rendimiento_t_ha"] = anual["produccion_t"] / anual["area_cosechada_ha"]
    anual.to_csv(EVA / "eva_altillanura_anual.csv", index=False, encoding="utf-8-sig")

    print(f"Filas detalle: {len(eva)} | filas anuales: {len(anual)}")
    print(f"Años: {anual['anio'].min()}-{anual['anio'].max()}")
    print(anual.groupby("municipio").size().rename("filas").to_string())
    faltantes = {n for n, _ in MUNICIPIOS.values()} - set(anual["municipio"])
    if faltantes:
        print(f"Sin datos para: {sorted(faltantes)}")
    ultimo = anual[anual["anio"] == anual["anio"].max()]
    print("Cultivos con más área sembrada en el último año (ha):")
    print(ultimo.groupby("cultivo")["area_sembrada_ha"].sum().sort_values(ascending=False).head(10).round(0).to_string())


if __name__ == "__main__":
    main()