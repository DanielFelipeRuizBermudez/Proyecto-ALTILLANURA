from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DATOS = RAIZ.parents[1] / "datos"
COBERTURA_MUNICIPAL = DATOS / "crudos" / "mapbiomas" / "cobertura_municipal"
MAPBIOMAS_CRUDOS = COBERTURA_MUNICIPAL / "tablas"
MAPAS_TIF = COBERTURA_MUNICIPAL / "geotiff_2024"
EVA = DATOS / "procesados" / "eva"
PROCESADOS = DATOS / "derivados" / "expansion"

MUNICIPIOS = {
    50573: ("Puerto López", "Meta"),
    50568: ("Puerto Gaitán", "Meta"),
    50325: ("Mapiripán", "Meta"),
    99001: ("Puerto Carreño", "Vichada"),
    99524: ("La Primavera", "Vichada"),
    99624: ("Santa Rosalía", "Vichada"),
    99773: ("Cumaribo", "Vichada"),
}

COD_REGION = 0
NOMBRE_REGION = "Altillanura"
