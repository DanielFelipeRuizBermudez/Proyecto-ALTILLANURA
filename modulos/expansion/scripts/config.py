from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DATOS = RAIZ / "datos"
MAPBIOMAS_CRUDOS = DATOS / "mapbiomas_crudos"
EVA = DATOS / "eva"
PROCESADOS = DATOS / "procesados"

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
