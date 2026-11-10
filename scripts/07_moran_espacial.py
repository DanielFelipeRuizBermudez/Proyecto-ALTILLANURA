import re
import unicodedata

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from matplotlib.collections import PolyCollection
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Patch
from pyproj import Transformer
from scipy import sparse
from scipy.spatial import cKDTree

import estilo
from config import MUNICIPIOS, PROCESADOS, RAIZ

MAPAS = RAIZ / "mapas_tif"
SALIDA_DATOS = PROCESADOS / "espacial"
SALIDA_GRAFICAS = RAIZ / "graficas" / "espacial"

CRS_COLOMBIA = "EPSG:9377"
TAMANO_CELDA_M = 2000
MINIMO_VALIDO = 0.5
DISTANCIA_VECINOS_M = 2900
PERMUTACIONES = 999
PERMUTACIONES_CORRELOGRAMA = 199
ALFA = 0.05
BANDAS_KM = [0, 3, 6, 10, 15, 20, 30, 40, 60]
MAXIMO_CELDAS_CORRELOGRAMA = 5000
SEMILLA = 2026

CLASES = {
    3: "Bosque",
    6: "Bosque inundado",
    9: "Plantación forestal",
    11: "Humedal",
    12: "Praderas / herbáceas",
    13: "Otras formaciones no forestales",
    21: "Mosaico de agricultura y pastos",
    23: "Playa, duna y arena",
    24: "Infraestructura",
    25: "Otras zonas no vegetadas",
    29: "Afloramiento rocoso",
    30: "Minería",
    31: "Acuicultura",
    33: "Río, lago u océano",
    35: "Aceite de palma",
    68: "Otras zonas naturales no vegetadas",
    75: "Granja de paneles solares",
}

GRUPOS = {
    "pct_agropecuario": {9, 21, 35},
    "pct_sabana": {12},
    "pct_bosque": {3, 6},
    "pct_humedal": {11},
}

VARIABLE = "pct_agropecuario"

ETIQUETAS = {
    "pct_agropecuario": "agropecuario",
    "pct_sabana": "sabana",
    "pct_bosque": "bosque",
    "pct_humedal": "humedal",
}

ZONAS = {
    "Alto-Alto": "#c8442b",
    "Bajo-Bajo": "#2a78d6",
    "Alto-Bajo": "#f0a58a",
    "Bajo-Alto": "#9cc3ee",
    "No significativo": "#e1e0d9",
}

RAMPA = LinearSegmentedColormap.from_list("azul", ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", texto.lower()).strip("_")


def identificar(ruta):
    nombre = re.sub(r"(cobertura|coverage)[_-]?", "", ruta.stem, flags=re.I)
    nombre = re.sub(r"\d{4}[_-]?", "", nombre).strip("_- ")
    nombre = re.sub(r"(?<=[a-záéíóúñ])(?=[A-ZÁÉÍÓÚÑ])", " ", nombre).replace("_", " ") or ruta.stem
    for codigo, (oficial, _) in MUNICIPIOS.items():
        if normalizar(oficial) == normalizar(nombre):
            return codigo, oficial
    return None, nombre


def leer_mapa(ruta):
    with rasterio.open(ruta) as src:
        mapa = src.read(1)
        transformacion = src.transform
        sin_dato = src.nodata if src.nodata is not None else 0
        crs = src.crs.to_string()
    return mapa, transformacion, sin_dato, crs


def armar_grilla(mapa, transformacion, sin_dato):
    tamano_pixel_m = abs(transformacion.a) * 111320 if abs(transformacion.a) < 1 else abs(transformacion.a)
    bloque = max(1, int(round(TAMANO_CELDA_M / tamano_pixel_m)))
    filas, columnas = mapa.shape
    nf, nc = -(-filas // bloque), -(-columnas // bloque)
    relleno = np.full((nf * bloque, nc * bloque), sin_dato, dtype=mapa.dtype)
    relleno[:filas, :columnas] = mapa
    bloques = relleno.reshape(nf, bloque, nc, bloque)

    validos = (bloques != sin_dato).sum(axis=(1, 3))
    tabla = {
        "fila": np.repeat(np.arange(nf), nc),
        "columna": np.tile(np.arange(nc), nf),
        "frac_valida": (validos / bloque**2).ravel(),
    }
    for nombre, codigos in GRUPOS.items():
        conteo = np.isin(bloques, list(codigos)).sum(axis=(1, 3))
        with np.errstate(invalid="ignore", divide="ignore"):
            tabla[nombre] = np.where(validos > 0, conteo / validos * 100, np.nan).ravel()
    celdas = pd.DataFrame(tabla)

    centro_col = celdas["columna"] * bloque + bloque / 2
    centro_fila = celdas["fila"] * bloque + bloque / 2
    celdas["lon"] = transformacion.c + transformacion.a * centro_col
    celdas["lat"] = transformacion.f + transformacion.e * centro_fila
    celdas = celdas[celdas["frac_valida"] >= MINIMO_VALIDO].reset_index(drop=True)

    desconocidos = sorted(set(np.unique(mapa).tolist()) - set(CLASES) - {sin_dato})
    return celdas, bloque, desconocidos


def a_coordenadas_colombia(celdas, crs_origen):
    transformador = Transformer.from_crs(crs_origen, CRS_COLOMBIA, always_xy=True)
    x, y = transformador.transform(celdas["lon"].values, celdas["lat"].values)
    celdas = celdas.copy()
    celdas["x_9377"] = x
    celdas["y_9377"] = y
    return celdas


def matriz_pesos(xy, distancia_max, distancia_min=0.0):
    arbol = cKDTree(xy)
    pares = arbol.query_pairs(distancia_max, output_type="ndarray")
    if distancia_min > 0 and len(pares):
        d = np.linalg.norm(xy[pares[:, 0]] - xy[pares[:, 1]], axis=1)
        pares = pares[d > distancia_min]
    n = len(xy)
    if len(pares) == 0:
        return sparse.csr_matrix((n, n))
    i = np.concatenate([pares[:, 0], pares[:, 1]])
    j = np.concatenate([pares[:, 1], pares[:, 0]])
    w = sparse.csr_matrix((np.ones(len(i)), (i, j)), shape=(n, n))
    vecinos = np.asarray(w.sum(axis=1)).ravel()
    inversa = np.divide(1.0, vecinos, out=np.zeros_like(vecinos, dtype=float), where=vecinos > 0)
    return (sparse.diags(inversa) @ w).tocsr()


def indice_moran(valores, w):
    z = valores - valores.mean()
    s0 = w.sum()
    if s0 == 0:
        return np.nan
    return (len(z) / s0) * (z @ (w @ z)) / (z @ z)


def prueba_moran(valores, w, permutaciones, generador):
    observado = indice_moran(valores, w)
    simulados = np.array([indice_moran(generador.permutation(valores), w) for _ in range(permutaciones)])
    mayores = np.sum(simulados >= observado)
    p_valor = (min(mayores, permutaciones - mayores) + 1) / (permutaciones + 1)
    z = (observado - simulados.mean()) / simulados.std()
    return observado, p_valor, z


def moran_local(valores, w, permutaciones, generador):
    n = len(valores)
    z = valores - valores.mean()
    m2 = (z @ z) / n
    rezago = w @ z
    local = z * rezago / m2

    vecinos = np.diff(w.indptr)
    k = max(int(vecinos.max()), 1)
    mascara = np.arange(k) < vecinos[:, None]
    divisor = np.maximum(vecinos, 1)
    indices = np.arange(n)
    mayores = np.zeros(n)
    for _ in range(permutaciones):
        sorteo = generador.integers(0, n - 1, size=(n, k))
        sorteo += sorteo >= indices[:, None]
        rezago_simulado = (z[sorteo] * mascara).sum(axis=1) / divisor
        mayores += z * rezago_simulado / m2 >= local
    p_local = (np.minimum(mayores, permutaciones - mayores) + 1) / (permutaciones + 1)
    p_local[vecinos == 0] = 1.0

    zona = np.full(n, "No significativo", dtype=object)
    significativo = p_local < ALFA
    zona[significativo & (z > 0) & (rezago > 0)] = "Alto-Alto"
    zona[significativo & (z < 0) & (rezago < 0)] = "Bajo-Bajo"
    zona[significativo & (z > 0) & (rezago < 0)] = "Alto-Bajo"
    zona[significativo & (z < 0) & (rezago > 0)] = "Bajo-Alto"
    return local, p_local, zona


def correlograma(xy, valores, generador):
    filas = []
    for inferior, superior in zip(BANDAS_KM[:-1], BANDAS_KM[1:]):
        w = matriz_pesos(xy, superior * 1000, inferior * 1000)
        if w.sum() == 0:
            continue
        observado, p_valor, _ = prueba_moran(valores, w, PERMUTACIONES_CORRELOGRAMA, generador)
        filas.append({"desde_km": inferior, "hasta_km": superior, "centro_km": (inferior + superior) / 2, "moran_i": observado, "p_valor": p_valor})
    return pd.DataFrame(filas)


def alcance(corr):
    sin_relacion = corr[(corr["moran_i"] <= 0) | (corr["p_valor"] >= ALFA)]
    return float(sin_relacion["desde_km"].iloc[0]) if len(sin_relacion) else np.nan


def texto_alcance(valor):
    return f"más de {BANDAS_KM[-1]} km" if np.isnan(valor) else f"unos {valor:g} km"


def cuadros(celdas):
    x = celdas["x_9377"].values / 1000
    y = celdas["y_9377"].values / 1000
    m = TAMANO_CELDA_M / 2000
    return np.stack([np.column_stack([x - m, y - m]), np.column_stack([x + m, y - m]),
                     np.column_stack([x + m, y + m]), np.column_stack([x - m, y + m])], axis=1)


def preparar_mapa(ax, titulo):
    ax.autoscale_view()
    ax.set_aspect("equal")
    ax.grid(False)
    ax.set_title(titulo, loc="left", fontsize=10, color=estilo.TINTA)
    ax.set_xlabel("Este (km)")
    ax.set_ylabel("Norte (km)")


def figura(nombre, celdas, resultado, corr, w):
    etiqueta = ETIQUETAS.get(VARIABLE, VARIABLE)
    minimo_p = 1 / (PERMUTACIONES + 1)
    texto_p = f"≤ {minimo_p:.3f}" if resultado["p_valor"] <= minimo_p else f"= {resultado['p_valor']:.3f}"
    texto_p = texto_p.replace(".", ",")
    texto_i = f"{resultado['moran_i']:.3f}".replace(".", ",")
    texto_celda = f"{TAMANO_CELDA_M / 1000:g}".replace(".", ",")

    fig, ejes = plt.subplots(2, 2, figsize=(13, 11.5))
    fig.subplots_adjust(left=0.07, right=0.97, top=0.89, bottom=0.06, wspace=0.25, hspace=0.45)
    fig.text(0.07, 0.955, f"Autocorrelación espacial del % {etiqueta} · {nombre}", fontsize=14, fontweight="bold", color=estilo.TINTA)
    fig.text(0.07, 0.92, f"MapBiomas Colombia 2024, celdas de {texto_celda} km en MAGNA-SIRGAS Origen Nacional (EPSG:9377). "
             f"I de Moran = {texto_i} (p {texto_p}). Relación positiva entre vecinas hasta {texto_alcance(resultado['alcance_km'])}.",
             fontsize=9.5, color=estilo.TINTA_2)

    ax = ejes[0, 0]
    porcentaje = PolyCollection(cuadros(celdas), array=celdas[VARIABLE].values, cmap=RAMPA, edgecolors="face", linewidths=0.3)
    porcentaje.set_clim(0, 100)
    ax.add_collection(porcentaje)
    preparar_mapa(ax, f"% {etiqueta} por celda")
    barra = fig.colorbar(porcentaje, ax=ax, shrink=0.8)
    barra.set_label(f"% {etiqueta}")
    barra.outline.set_visible(False)

    ax = ejes[0, 1]
    colores = [ZONAS[z] for z in celdas["zona_lisa"]]
    ax.add_collection(PolyCollection(cuadros(celdas), facecolors=colores, edgecolors="face", linewidths=0.3))
    preparar_mapa(ax, f"Zonas de Moran local (p < {ALFA:g})".replace(".", ","))
    conteo = celdas["zona_lisa"].value_counts()
    leyenda = [Patch(facecolor=color, label=f"{zona} ({conteo.get(zona, 0)})") for zona, color in ZONAS.items()]
    ax.legend(handles=leyenda, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=3, fontsize=8, frameon=False)

    ax = ejes[1, 0]
    z = celdas[VARIABLE].values - celdas[VARIABLE].mean()
    rezago = w @ z
    ax.scatter(z, rezago, s=6, c=colores, alpha=0.7, linewidths=0)
    pendiente = np.polyfit(z, rezago, 1)
    eje_x = np.array([z.min(), z.max()])
    ax.plot(eje_x, np.polyval(pendiente, eje_x), color=estilo.TINTA, linewidth=1.5)
    ax.axhline(0, color=estilo.EJE, linewidth=0.8)
    ax.axvline(0, color=estilo.EJE, linewidth=0.8)
    ax.set_title("Diagrama de Moran: cada celda contra el promedio de sus vecinas", loc="left", fontsize=10, color=estilo.TINTA)
    ax.set_xlabel(f"% {etiqueta} de la celda (centrado)")
    ax.set_ylabel("Promedio de las vecinas (centrado)")

    ax = ejes[1, 1]
    if not corr.empty:
        significativo = corr["p_valor"] < ALFA
        ax.plot(corr["centro_km"], corr["moran_i"], color=estilo.SERIE_1, linewidth=2)
        ax.scatter(corr.loc[significativo, "centro_km"], corr.loc[significativo, "moran_i"], color=estilo.SERIE_1, s=36, zorder=3, label=f"p < {ALFA:g}".replace(".", ","))
        ax.scatter(corr.loc[~significativo, "centro_km"], corr.loc[~significativo, "moran_i"], facecolor=estilo.SUPERFICIE, edgecolor=estilo.SERIE_1, s=36, zorder=3, label="No significativo")
        ax.axhline(0, color=estilo.EJE, linewidth=0.8)
        if not np.isnan(resultado["alcance_km"]):
            ax.axvline(resultado["alcance_km"], color=estilo.TENUE, linestyle="--", linewidth=1)
            ax.text(resultado["alcance_km"], ax.get_ylim()[1], f" {resultado['alcance_km']:g} km", va="top", fontsize=8, color=estilo.TENUE)
        ax.legend(loc="upper right", fontsize=8)
    ax.set_title("Correlograma: I de Moran según la distancia", loc="left", fontsize=10, color=estilo.TINTA)
    ax.set_xlabel("Distancia entre celdas (km)")
    ax.set_ylabel("I de Moran")

    ruta = SALIDA_GRAFICAS / f"moran_{VARIABLE}_{normalizar(nombre)}.png"
    fig.savefig(ruta, dpi=170)
    plt.close(fig)
    return ruta


def analizar(nombre, celdas, generador):
    celdas = celdas.copy()
    xy = celdas[["x_9377", "y_9377"]].values
    valores = celdas[VARIABLE].values.astype(float)
    w = matriz_pesos(xy, DISTANCIA_VECINOS_M)

    observado, p_valor, z = prueba_moran(valores, w, PERMUTACIONES, generador)
    local, p_local, zona = moran_local(valores, w, PERMUTACIONES, generador)
    celdas["moran_local"] = local
    celdas["p_local"] = p_local
    celdas["zona_lisa"] = zona

    if len(celdas) > MAXIMO_CELDAS_CORRELOGRAMA:
        muestra = generador.choice(len(celdas), MAXIMO_CELDAS_CORRELOGRAMA, replace=False)
        corr = correlograma(xy[muestra], valores[muestra], generador)
    else:
        corr = correlograma(xy, valores, generador)

    resultado = {
        "territorio": nombre,
        "variable": VARIABLE,
        "n_celdas": len(celdas),
        "celdas_sin_vecinos": int((np.diff(w.indptr) == 0).sum()),
        "media": valores.mean(),
        "moran_i": observado,
        "moran_i_esperado": -1 / (len(valores) - 1),
        "z_permutacion": z,
        "p_valor": p_valor,
        "alcance_km": alcance(corr),
    }

    area_celda = (TAMANO_CELDA_M / 1000) ** 2
    zonas = celdas.groupby("zona_lisa")[VARIABLE].agg(n_celdas="size", media="mean").reindex(list(ZONAS))
    zonas.index.name = "zona"
    zonas = zonas.reset_index()
    zonas["n_celdas"] = zonas["n_celdas"].fillna(0).astype(int)
    zonas["area_km2_aprox"] = zonas["n_celdas"] * area_celda

    for tabla in (corr, zonas):
        tabla.insert(0, "territorio", nombre)
        tabla.insert(1, "variable", VARIABLE)

    ruta = figura(nombre, celdas, resultado, corr, w)
    return celdas, resultado, corr, zonas, ruta


def reportar(resultado, ruta):
    print(f"  I de Moran = {resultado['moran_i']:.3f} (p = {resultado['p_valor']:.4f}), "
          f"relación positiva hasta {texto_alcance(resultado['alcance_km'])} -> {ruta.name}")


def main():
    estilo.aplicar()
    SALIDA_DATOS.mkdir(parents=True, exist_ok=True)
    SALIDA_GRAFICAS.mkdir(parents=True, exist_ok=True)
    generador = np.random.default_rng(SEMILLA)

    archivos = sorted(MAPAS.glob("*.tif"))
    if not archivos:
        raise SystemExit(f"No hay archivos .tif en {MAPAS}")

    municipios, resultados, correlogramas, zonas = [], [], [], []
    for archivo in archivos:
        codigo, nombre = identificar(archivo)
        mapa, transformacion, sin_dato, crs = leer_mapa(archivo)
        celdas, bloque, desconocidos = armar_grilla(mapa, transformacion, sin_dato)
        celdas = a_coordenadas_colombia(celdas, crs)
        celdas.insert(0, "codigo", codigo)
        celdas.insert(1, "territorio", nombre)
        print(f"{archivo.name}: sistema {crs}, celdas de {bloque}x{bloque} pixeles, {len(celdas)} celdas")
        if codigo is None:
            print("  Atención, el nombre del archivo no coincide con ningún municipio de config.MUNICIPIOS.")
        if desconocidos:
            print(f"  Atención, códigos de clase no reconocidos: {desconocidos}. Revise CLASES y GRUPOS.")
        celdas, resultado, corr, zona, ruta = analizar(nombre, celdas, generador)
        municipios.append(celdas)
        resultados.append(resultado)
        correlogramas.append(corr)
        zonas.append(zona)
        reportar(resultado, ruta)

    if len(municipios) > 1:
        conjunto = pd.concat(municipios, ignore_index=True).drop(columns=["moran_local", "p_local", "zona_lisa"])
        print(f"Altillanura completa: {len(conjunto)} celdas")
        conjunto, resultado, corr, zona, ruta = analizar("Altillanura", conjunto, generador)
        conjunto.to_csv(SALIDA_DATOS / "celdas_2km_altillanura.csv", index=False, encoding="utf-8-sig")
        resultados.append(resultado)
        correlogramas.append(corr)
        zonas.append(zona)
        reportar(resultado, ruta)

    pd.concat(municipios, ignore_index=True).to_csv(SALIDA_DATOS / "celdas_2km.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(resultados).to_csv(SALIDA_DATOS / "moran_global.csv", index=False, encoding="utf-8-sig")
    pd.concat(correlogramas, ignore_index=True).to_csv(SALIDA_DATOS / "correlograma_moran.csv", index=False, encoding="utf-8-sig")
    pd.concat(zonas, ignore_index=True).to_csv(SALIDA_DATOS / "zonas_lisa.csv", index=False, encoding="utf-8-sig")
    print(f"\nTablas en {SALIDA_DATOS}")
    print(f"Gráficas en {SALIDA_GRAFICAS}")


if __name__ == "__main__":
    main()