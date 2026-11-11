from config import PROCESADOS
from series import cargar_eva, cargar_mapbiomas, cruce_mapbiomas_eva, serie, tabla_ancha


def main():
    datos = cargar_mapbiomas()

    for nivel in ["nivel_1", "nivel_2"]:
        tabla = tabla_ancha(nivel, datos)
        tabla.to_csv(PROCESADOS / f"mapbiomas_{nivel}_ancho.csv", index=False, encoding="utf-8-sig")
        print(f"mapbiomas_{nivel}_ancho.csv: {len(tabla)} filas x {tabla.shape[1]} columnas")

    ejemplo = serie("Zona agrícola y ganadera", "Puerto Gaitán", datos=datos)
    print(f"\nEjemplo de serie: {ejemplo.name}")
    print(ejemplo.iloc[[0, 1, -2, -1]].round(0).to_string())

    eva = cargar_eva()
    if eva is None:
        print("\nNo se encontró datos/eva/eva_altillanura_anual.csv. Corra primero 01_descargar_eva.py para hacer el cruce con la EVA.")
        return

    cruce = cruce_mapbiomas_eva(datos=datos, eva=eva)
    cruce.to_csv(PROCESADOS / "cruce_mapbiomas_eva.csv", index=False, encoding="utf-8-sig")
    print(f"\ncruce_mapbiomas_eva.csv: {len(cruce)} filas, años {cruce['anio'].min()}-{cruce['anio'].max()}")
    resumen = cruce.groupby("municipio")[["mb_agricola_ganadera", "eva_total_area_sembrada_ha"]].mean().round(0)
    resumen["eva_sobre_mb"] = (resumen["eva_total_area_sembrada_ha"] / resumen["mb_agricola_ganadera"]).round(2)
    print("Promedio anual por municipio (ha):")
    print(resumen.to_string())


if __name__ == "__main__":
    main()
