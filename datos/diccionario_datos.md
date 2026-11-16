# Diccionario de datos

## Suelos (cuadernos 40 y 42, Katalina)

### `datos/comunes/suelo_celda.csv` (cuaderno 42, DVC)
Una fila por celda de la grilla común de 2 km (34.763 filas). Llave: `id_celda`. Fuente: SoilGrids 2.0 (ISRIC), 0-30 cm, sin fecha.

| Variable | Descripción | Unidad | Fuente |
|---|---|---|---|
| `id_celda` | Llave de la grilla común: esquina inferior izquierda en km, EPSG:9377 | texto | grilla_2km.gpkg (cuaderno 02) |
| `mpio_cdpmp` | Código DIVIPOLA del municipio | texto, 5 dígitos | grilla_2km.gpkg |
| `area_km2` | Área de la celda dentro de la Altillanura (4 si está completa) | km² | grilla_2km.gpkg |
| `n_pixeles` | Píxeles de SoilGrids (≈ 278 m) con centro en la celda | píxeles | SoilGrids |
| `relleno_vecino` | True si la celda no tenía píxeles y tomó el del píxel más cercano (283 celdas) | booleano | cuaderno 42 |
| `ph_medio` | pH en agua, promedio de los píxeles | pH | SoilGrids |
| `cos_medio_gkg` | Carbono orgánico, promedio de los píxeles | g/kg | SoilGrids |
| `log_cos_medio` | Logaritmo natural de cos_medio_gkg | ln(g/kg) | cuaderno 42 |
| `pct_area_ph_menor_5` | % de píxeles con pH < 5 (toxicidad por aluminio) | % del área | SoilGrids |
| `clase_ph` | Clase de pH del promedio de la celda | categoría | cuaderno 42 |
| `pct_ph_menor_4_5` | % de píxeles con pH < 4,5 | % del área | SoilGrids |
| `pct_ph_4_5_a_5_0` | % de píxeles con 4,5 ≤ pH ≤ 5,0 | % del área | SoilGrids |
| `pct_ph_5_1_a_5_5` | % de píxeles con 5,0 < pH ≤ 5,5 | % del área | SoilGrids |
| `pct_ph_mayor_5_5` | % de píxeles con pH > 5,5 | % del área | SoilGrids |
| `ph_kriging` | pH por kriging ordinario con 300 puntos (vacío en 851 celdas de borde) | pH | cuaderno 40 |
| `cos_kriging_gkg` | COS por kriging en log con corrección exp(pred + var/2) (vacío en las mismas celdas) | g/kg | cuaderno 40 |