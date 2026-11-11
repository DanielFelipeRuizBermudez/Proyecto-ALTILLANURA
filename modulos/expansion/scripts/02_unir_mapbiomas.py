import re
import sys

import pandas as pd

from config import MAPBIOMAS_CRUDOS, MUNICIPIOS, PROCESADOS

NIVEL_1 = {
    "Forest formation": "Formación forestal",
    "Natural non forest formation": "Formación natural no forestal",
    "Agricultural and livestock area": "Zona agrícola y ganadera",
    "Non-vegetated area": "Zona sin vegetación",
    "Water body": "Cuerpo de agua",
}

NIVEL_2 = {
    "Forest": "Bosque",
    "Mangrove": "Manglar",
    "Flooded forest": "Bosque inundado",
    "Wooded sand vegetation": "Vegetación de arena boscosa",
    "Wetland": "Humedal",
    "Grasslands / herbaceous": "Praderas / herbáceas",
    "Hypersaline tidal flat": "Llanura de marea hipersalina",
    "Rocky outcrop": "Afloramiento rocoso",
    "Herbaceous sand vegetation": "Vegetación herbácea de arena",
    "Other non forest formation": "Otras formaciones no forestales",
    "Andinean Herbaceous and Shrubby Vegetation": "Vegetación herbácea y arbustiva andina",
    "Flooded Andinean Herbaceous and Shrubby Vegetation": "Vegetación herbácea y matorral andino inundado",
    "Forest plantation": "Plantación forestal",
    "Palm oil": "Aceite de palma",
    "Banana": "Plátano",
    "Mosaic of agriculture and pasture": "Mosaico de agricultura y pastos",
    "Beach, dune and sand spot": "Lugar de playa, duna y arena",
    "Infrastructure": "Infraestructura",
    "Mining": "Minería",
    "Other natural  non-vegetated area": "Otras zonas naturales no vegetadas",
    "Other non-vegetated area": "Otras zonas no vegetadas",
    "Solar panel farm": "Granja de paneles solares",
    "River, lake or ocean": "Río, lago u océano",
    "Aquaculture": "Acuicultura",
    "Glacier": "Glaciar",
}


def leer(archivo, codigo):
    df = pd.read_csv(archivo)
    df["Level 2"] = df["Level 2"].fillna("").str.strip()
    df = df[df["Level 2"] != ""]
    largo = df.melt(id_vars=["Level 1", "Level 2"], var_name="anio", value_name="hectareas")
    largo["anio"] = largo["anio"].astype(int)
    largo["hectareas"] = pd.to_numeric(largo["hectareas"], errors="coerce").fillna(0.0)
    municipio, departamento = MUNICIPIOS[codigo]
    largo.insert(0, "departamento", departamento)
    largo.insert(0, "municipio", municipio)
    largo.insert(0, "cod_mun", codigo)
    largo = largo.rename(columns={"Level 1": "nivel_1_en", "Level 2": "nivel_2_en"})
    largo["nivel_1"] = largo["nivel_1_en"].map(NIVEL_1).fillna(largo["nivel_1_en"])
    largo["nivel_2"] = largo["nivel_2_en"].map(NIVEL_2).fillna(largo["nivel_2_en"])
    return largo


def main():
    PROCESADOS.mkdir(parents=True, exist_ok=True)
    partes = []
    for archivo in sorted(MAPBIOMAS_CRUDOS.glob("*.csv")):
        m = re.search(r"(\d{5})_", archivo.name)
        if m and int(m.group(1)) in MUNICIPIOS:
            partes.append(leer(archivo, int(m.group(1))))
    encontrados = {int(p["cod_mun"].iloc[0]) for p in partes}
    faltan = set(MUNICIPIOS) - encontrados
    if faltan:
        sys.exit(f"Faltan los archivos de: {[MUNICIPIOS[c][0] for c in sorted(faltan)]}")

    datos = pd.concat(partes, ignore_index=True)
    datos = datos[datos.groupby("nivel_2_en")["hectareas"].transform("sum") > 0]
    columnas = ["cod_mun", "municipio", "departamento", "anio", "nivel_1", "nivel_2", "hectareas", "nivel_1_en", "nivel_2_en"]
    datos = datos[columnas].sort_values(["cod_mun", "nivel_1", "nivel_2", "anio"])
    datos.to_csv(PROCESADOS / "mapbiomas_largo.csv", index=False, encoding="utf-8-sig")

    total = datos.groupby(["municipio", "anio"])["hectareas"].sum().unstack("anio")
    variacion = (total.max(axis=1) - total.min(axis=1)).max()
    print(f"Filas: {len(datos)} | clases presentes: {datos['nivel_2'].nunique()}")
    print(f"Máxima variación del área total de un municipio entre años: {variacion:.3f} ha")
    print(f"Suma de los 7 municipios: {total.iloc[:, 0].sum():,.0f} ha")


if __name__ == "__main__":
    main()
