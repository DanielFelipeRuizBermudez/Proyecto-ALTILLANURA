"""Rutas, municipios y parámetros comunes de todos los scripts."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DATOS = RAIZ / "datos"
CRUDOS = DATOS / "crudos"
PROCESADOS = DATOS / "procesados"
DERIVADOS = DATOS / "derivados"
TABLAS = RAIZ / "resultados" / "tablas"
FIGURAS = RAIZ / "resultados" / "figuras"

# código DANE -> (nombre, identificador de archivo, departamento)
MUNICIPIOS = {
    50325: ("Mapiripán", "mapiripan", "Meta"),
    50568: ("Puerto Gaitán", "puerto_gaitan", "Meta"),
    50573: ("Puerto López", "puerto_lopez", "Meta"),
    99001: ("Puerto Carreño", "puerto_carreno", "Vichada"),
    99524: ("La Primavera", "la_primavera", "Vichada"),
    99624: ("Santa Rosalía", "santa_rosalia", "Vichada"),
    99773: ("Cumaribo", "cumaribo", "Vichada"),
}
NOMBRE = {c: v[0] for c, v in MUNICIPIOS.items()}
SLUG = {c: v[1] for c, v in MUNICIPIOS.items()}

# Panel anual. La primera temporada seca completa en FIRMS es la de 2001
# (diciembre de 2000 a marzo de 2001); MapBiomas cobertura llega hasta 2024.
ANIO_INI = 2001
ANIO_FIN = 2024

# MapBiomas Fuego Colección 1 Beta: limitaciones Landsat y apoyo MODIS MCD64A1.
ANIOS_FUEGO_LIMITADOS = (2002, 2005, 2007)

# Temporada seca del año y: diciembre de y-1 a marzo de y.
MESES_SECA = (12, 1, 2, 3)

# Paleta categórica validada (ranuras 1 a 3, superficie clara).
COLOR_AGRO = "#2a78d6"
COLOR_SABANA = "#eb6834"
COLOR_BOSQUE = "#1baf7a"
COLOR_TEXTO = "#0b0b0b"
COLOR_TEXTO_2 = "#52514e"
COLOR_SUPERFICIE = "#fcfcfb"
COLOR_GRILLA = "#e4e3df"

SEMILLA = 42
