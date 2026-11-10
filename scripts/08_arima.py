import math
import re
import textwrap
import unicodedata
import warnings

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox, het_arch
from statsmodels.stats.stattools import jarque_bera
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import acf, adfuller, kpss, pacf

import estilo
from config import MUNICIPIOS, NOMBRE_REGION, PROCESADOS, RAIZ

ARCHIVO_MAPBIOMAS = PROCESADOS / "mapbiomas_largo.csv"
SALIDA_DATOS = PROCESADOS / "arima"
SALIDA_GRAFICAS = RAIZ / "graficas" / "arima"

NIVEL_1 = "Zona agrícola y ganadera"
NOMBRE_VARIABLE = "Área agropecuaria"
ESCALA = 1000
UNIDAD = "miles de ha"
ANIO_INICIO = 1985
USAR_LOG = False

ALFA = 0.05
MAXIMO_D = 2
MAXIMO_P = 5
MAXIMO_Q = 5
CRITERIO = "aicc"
REZAGOS_LJUNG_BOX = [5, 10]
REZAGOS_ARCH = 4
REZAGOS_ACF = 12
HORIZONTE = 6
ANIOS_VALIDACION = 5

EXIGIDOS = ["raices_ok", "coef_significativos", "ljung_box_ok"]
DESEABLES = ["normalidad_ok", "homocedasticidad_ok"]
MARGEN_EMPATE = 2
MODULO_MINIMO = 1.01

ORDENES_MANUALES = {}

NOMBRES_CRITERIO = {"aicc": "AICc", "aic": "AIC", "bic": "BIC"}
CHEQUEOS = {
    "raices_ok": ("R", "raíces"),
    "coef_significativos": ("C", "coeficientes"),
    "ljung_box_ok": ("L", "Ljung-Box"),
    "normalidad_ok": ("N", "normalidad"),
    "homocedasticidad_ok": ("H", "homocedasticidad"),
}


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", texto.lower()).strip("_")


def coma(valor, decimales=2):
    return f"{valor:.{decimales}f}".replace(".", ",")


def texto_p(valor):
    if pd.isna(valor):
        return "no disponible"
    return "< 0,001" if valor < 0.001 else f"= {coma(valor, 3)}"


def etiqueta_modelo(p, d, q):
    return f"ARIMA({p},{d},{q})"


def transformar(valores):
    return np.log(valores) if USAR_LOG else valores


def revertir(valores):
    return np.exp(valores) if USAR_LOG else valores


def sin_avisos(funcion, *args, **kwargs):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return funcion(*args, **kwargs)


def cargar_series():
    datos = pd.read_csv(ARCHIVO_MAPBIOMAS, encoding="utf-8-sig")
    faltan = {"cod_mun", "anio", "nivel_1", "hectareas"} - set(datos.columns)
    if faltan:
        raise SystemExit(f"Faltan las columnas {sorted(faltan)} en {ARCHIVO_MAPBIOMAS.name}. Tiene: {list(datos.columns)}")
    elegidos = datos[(datos["nivel_1"] == NIVEL_1) & (datos["anio"] >= ANIO_INICIO)]
    if elegidos.empty:
        raise SystemExit(f"No hay filas con nivel_1 = '{NIVEL_1}'. Valores posibles: {sorted(datos['nivel_1'].unique())}")
    tabla = elegidos.pivot_table(index="anio", columns="cod_mun", values="hectareas", aggfunc="sum").sort_index()
    series = {NOMBRE_REGION: tabla.sum(axis=1)}
    for codigo, (nombre, _) in MUNICIPIOS.items():
        if codigo in tabla.columns:
            series[nombre] = tabla[codigo]
    return {nombre: serie / ESCALA for nombre, serie in series.items()}


def pruebas_estacionariedad(y):
    filas = []
    for d in range(MAXIMO_D + 1):
        x = np.diff(y, n=d)
        adf = sin_avisos(adfuller, x, regression="c", autolag="AIC")
        prueba_kpss = sin_avisos(kpss, x, regression="c", nlags="auto")
        filas.append({
            "d": d,
            "adf_estadistico": adf[0],
            "adf_p": adf[1],
            "kpss_estadistico": prueba_kpss[0],
            "kpss_p": prueba_kpss[1],
            "acf_rezago_1": acf(x, nlags=1, fft=False)[1],
            "desviacion": x.std(ddof=1),
        })
    return pd.DataFrame(filas)


def sobrediferenciada(pruebas, menor, mayor):
    tabla = pruebas.set_index("d")
    return tabla.loc[mayor, "acf_rezago_1"] < -0.5 or tabla.loc[mayor, "desviacion"] > tabla.loc[menor, "desviacion"]


def elegir_d(pruebas):
    adf_ok = pruebas["adf_p"] < ALFA
    kpss_ok = pruebas["kpss_p"] > ALFA
    d_adf = int(pruebas.loc[adf_ok, "d"].min()) if adf_ok.any() else None
    d_kpss = int(pruebas.loc[kpss_ok, "d"].min()) if kpss_ok.any() else None
    if d_adf is None and d_kpss is None:
        d = int(pruebas.loc[pruebas["desviacion"].idxmin(), "d"])
        return d, "ninguna prueba indica estacionariedad, se usa la d de menor desviación"
    if d_adf is None or d_kpss is None:
        d = d_adf if d_kpss is None else d_kpss
        return d, f"solo {'ADF' if d_kpss is None else 'KPSS'} indica estacionariedad"
    if d_adf == d_kpss:
        return d_adf, "ADF y KPSS coinciden"
    menor, mayor = sorted((d_adf, d_kpss))
    if sobrediferenciada(pruebas, menor, mayor):
        return menor, f"ADF y KPSS no coinciden y con d = {mayor} hay señales de sobrediferenciación"
    return mayor, f"ADF y KPSS no coinciden y con d = {mayor} no hay señales de sobrediferenciación"


def ajustar(y, p, d, q):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return ARIMA(y, order=(p, d, q)).fit(), None
    except Exception as error:
        return None, str(error)


def coeficientes(res):
    nombres = list(res.model.param_names)
    tabla = pd.DataFrame({
        "parametro": nombres,
        "estimacion": np.asarray(res.params, dtype=float),
        "error_estandar": np.asarray(res.bse, dtype=float),
        "p_valor": np.asarray(res.pvalues, dtype=float),
    })
    otros = ~tabla["parametro"].str.startswith(("ar.", "ma.")) & (tabla["parametro"] != "sigma2")
    tabla.loc[otros, "parametro"] = "media"
    return tabla


def raices(tabla):
    filas = []
    for prefijo, polinomio, signo in (("ar.", "AR", -1), ("ma.", "MA", 1)):
        valores = tabla.loc[tabla["parametro"].str.startswith(prefijo), "estimacion"].to_numpy()
        if len(valores) == 0:
            continue
        for raiz in np.roots(np.r_[signo * valores[::-1], 1.0]):
            filas.append({"polinomio": polinomio, "real": raiz.real, "imaginaria": raiz.imag, "modulo": abs(raiz)})
    return pd.DataFrame(filas, columns=["polinomio", "real", "imaginaria", "modulo"])


def ljung_box(residuos, grados):
    tabla = acorr_ljungbox(residuos, lags=REZAGOS_LJUNG_BOX, model_df=grados)
    return dict(zip(REZAGOS_LJUNG_BOX, tabla["lb_pvalue"].to_numpy()))


def comparar(y, d):
    filas, ajustes, errores = [], {}, []
    for p in range(MAXIMO_P + 1):
        for q in range(MAXIMO_Q + 1):
            res, error = ajustar(y, p, d, q)
            if res is None:
                errores.append(error)
                continue
            tabla = coeficientes(res)
            sin_varianza = tabla[tabla["parametro"] != "sigma2"]
            retornos = getattr(res, "mle_retvals", None) or {}
            _, diagnostico = diagnosticar(res, p, d, q)
            ljung_box_p = min(diagnostico[f"ljung_box_p_{rezago}"] for rezago in REZAGOS_LJUNG_BOX)
            ajustes[(p, q)] = res
            filas.append({
                "p": p,
                "d": d,
                "q": q,
                "aicc": res.aicc,
                "aic": res.aic,
                "bic": res.bic,
                "converge": bool(retornos.get("converged", True)),
                "raices_ok": bool((raices(tabla)["modulo"] > MODULO_MINIMO).all()),
                "coef_significativos": bool((sin_varianza["p_valor"] < ALFA).all()),
                "ljung_box_ok": bool(ljung_box_p > ALFA),
                "normalidad_ok": bool(diagnostico["shapiro_p"] > ALFA and diagnostico["jarque_bera_p"] > ALFA),
                "homocedasticidad_ok": bool(diagnostico["arch_p"] > ALFA),
                "ljung_box_p": ljung_box_p,
                "shapiro_p": diagnostico["shapiro_p"],
                "jarque_bera_p": diagnostico["jarque_bera_p"],
                "arch_p": diagnostico["arch_p"],
            })
    if not filas:
        raise SystemExit(f"No se pudo ajustar ningún modelo. Último error: {errores[-1] if errores else 'desconocido'}")
    candidatos = pd.DataFrame(filas).sort_values(CRITERIO).reset_index(drop=True)
    candidatos["cumple_todo"] = candidatos[list(CHEQUEOS)].all(axis=1)
    candidatos["falla"] = ["".join(letra for columna, (letra, _) in CHEQUEOS.items() if not fila[columna])
                           for _, fila in candidatos.iterrows()]
    candidatos["puesto"] = np.arange(1, len(candidatos) + 1)
    return candidatos, ajustes


def juntar(textos):
    textos = list(textos)
    return textos[0] if len(textos) == 1 else ", ".join(textos[:-1]) + " y " + textos[-1]


def seleccionar(candidatos):
    criterio = NOMBRES_CRITERIO[CRITERIO]
    exigidos = juntar(CHEQUEOS[columna][1] for columna in EXIGIDOS)
    convergidos = candidatos[candidatos["converge"]] if candidatos["converge"].any() else candidatos
    aptos = convergidos[convergidos[EXIGIDOS].all(axis=1)]
    if aptos.empty:
        return convergidos.index[0], f"ningún modelo cumple {exigidos}; se deja el de menor {criterio}"
    mejor = aptos[CRITERIO].iloc[0]
    empatados = aptos[aptos[CRITERIO] <= mejor + MARGEN_EMPATE]
    completos = empatados[empatados[DESEABLES].all(axis=1)]
    if completos.empty:
        fallas = juntar(CHEQUEOS[columna][1] for columna in DESEABLES if not aptos.iloc[0][columna])
        return aptos.index[0], f"el de menor {criterio} que cumple {exigidos} (falla {fallas})"
    if completos.index[0] == aptos.index[0]:
        return aptos.index[0], f"el de menor {criterio} que cumple todos los supuestos"
    return completos.index[0], (f"cumple todos los supuestos y su {criterio} está a menos de {coma(MARGEN_EMPATE, 0)} "
                                f"del mejor que cumple {exigidos}")


def diagnosticar(res, p, d, q):
    residuos = np.asarray(res.resid)[d:]
    lb = ljung_box(residuos, p + q)
    jb = jarque_bera(residuos)
    shapiro = stats.shapiro(residuos)
    try:
        arch_p = sin_avisos(het_arch, residuos, nlags=REZAGOS_ARCH)[1]
    except (ValueError, np.linalg.LinAlgError):
        arch_p = np.nan
    resumen = {f"ljung_box_p_{rezago}": valor for rezago, valor in lb.items()}
    resumen.update({"jarque_bera_p": jb[1], "shapiro_p": shapiro[1], "arch_p": arch_p})
    return residuos, resumen


def pronosticar(res, ultimo_anio):
    marco = res.get_forecast(steps=HORIZONTE).summary_frame(alpha=ALFA)
    return pd.DataFrame({
        "anio": np.arange(ultimo_anio + 1, ultimo_anio + 1 + HORIZONTE),
        "pronostico": revertir(marco["mean"].to_numpy()),
        "limite_inferior": revertir(marco["mean_ci_lower"].to_numpy()),
        "limite_superior": revertir(marco["mean_ci_upper"].to_numpy()),
    })


def validar(y, serie, p, d, q):
    res, _ = ajustar(y[:-ANIOS_VALIDACION], p, d, q)
    if res is None:
        return {"rmse_validacion": np.nan, "mape_validacion": np.nan}
    predicho = revertir(res.get_forecast(steps=ANIOS_VALIDACION).summary_frame(alpha=ALFA)["mean"].to_numpy())
    real = serie.to_numpy(dtype=float)[-ANIOS_VALIDACION:]
    return {
        "rmse_validacion": float(np.sqrt(np.mean((predicho - real) ** 2))),
        "mape_validacion": float(np.mean(np.abs(predicho - real) / real) * 100),
    }


def modelar(nombre, serie):
    y = transformar(serie.to_numpy(dtype=float))
    pruebas = pruebas_estacionariedad(y)
    d, razon = elegir_d(pruebas)
    manual = ORDENES_MANUALES.get(nombre)
    if manual:
        d = manual[1]
        razon = "fijado a mano en ORDENES_MANUALES"
    pruebas["elegido"] = pruebas["d"] == d

    candidatos, ajustes = comparar(y, d)
    if manual:
        p, _, q = manual
        res, error = ajustar(y, p, d, q)
        if res is None:
            raise SystemExit(f"No se pudo ajustar el modelo manual de {nombre}: {error}")
        origen = "manual"
        razon_eleccion = "fijado a mano en ORDENES_MANUALES"
    else:
        indice, razon_eleccion = seleccionar(candidatos)
        fila = candidatos.loc[indice]
        p, q = int(fila["p"]), int(fila["q"])
        res = ajustes[(p, q)]
        origen = "automático"
    candidatos["elegido"] = (candidatos["p"] == p) & (candidatos["q"] == q)
    puesto = candidatos.loc[candidatos["elegido"], "puesto"]

    tabla_coef = coeficientes(res)
    tabla_raices = raices(tabla_coef)
    residuos, diagnostico = diagnosticar(res, p, d, q)
    sin_varianza = tabla_coef[tabla_coef["parametro"] != "sigma2"]
    modelo = {
        "serie": nombre,
        "anio_inicio": int(serie.index.min()),
        "anio_fin": int(serie.index.max()),
        "n": len(serie),
        "log": USAR_LOG,
        "p": p,
        "d": d,
        "q": q,
        "origen": origen,
        "razon_d": razon,
        "criterio": NOMBRES_CRITERIO[CRITERIO],
        "modelos_probados": len(candidatos),
        "puesto_criterio": int(puesto.iloc[0]) if len(puesto) else np.nan,
        "razon_eleccion": razon_eleccion,
        "aicc": res.aicc,
        "aic": res.aic,
        "bic": res.bic,
        "raices_ok": bool((tabla_raices["modulo"] > MODULO_MINIMO).all()),
        "coef_no_significativos": ", ".join(sin_varianza.loc[sin_varianza["p_valor"] >= ALFA, "parametro"]),
        **diagnostico,
        **validar(y, serie, p, d, q),
    }
    pronostico = pronosticar(res, int(serie.index.max()))
    for tabla in (pruebas, candidatos, tabla_coef, tabla_raices, pronostico):
        tabla.insert(0, "serie", nombre)
    return {
        "nombre": nombre,
        "serie": serie,
        "y": y,
        "res": res,
        "modelo": modelo,
        "pruebas": pruebas,
        "candidatos": candidatos,
        "coeficientes": tabla_coef,
        "raices": tabla_raices,
        "pronostico": pronostico,
        "residuos": residuos,
    }


def correlograma(ax, valores, titulo, parcial=False):
    rezagos_max = max(1, min(REZAGOS_ACF, len(valores) // 2 - 1))
    if parcial:
        coef = pacf(valores, nlags=rezagos_max, method="ywm")
    else:
        coef = acf(valores, nlags=rezagos_max, fft=False)
    rezagos = np.arange(1, rezagos_max + 1)
    banda = 1.96 / np.sqrt(len(valores))
    ax.axhspan(-banda, banda, color=estilo.SERIE_1, alpha=0.12, linewidth=0)
    ax.vlines(rezagos, 0, coef[1:], color=estilo.SERIE_1, linewidth=1.5)
    ax.scatter(rezagos, coef[1:], color=estilo.SERIE_1, s=18, zorder=3)
    ax.axhline(0, color=estilo.EJE, linewidth=0.8)
    ax.set_ylim(-1, 1)
    ax.set_xlim(0.3, rezagos_max + 0.7)
    ax.set_xticks(rezagos)
    ax.set_xlabel("Rezago (años)")
    ax.set_title(titulo, loc="left", fontsize=10, color=estilo.TINTA)


def texto_p_kpss(valor):
    if valor >= 0.1:
        return "≥ 0,10"
    if valor <= 0.01:
        return "≤ 0,01"
    return f"= {coma(valor, 3)}"


def titulo_figura(fig, titulo, subtitulo):
    fig.text(0.06, 1 - 0.3 / fig.get_figheight(), titulo, fontsize=14, fontweight="bold", color=estilo.TINTA, va="top")
    fig.text(0.06, 1 - 0.75 / fig.get_figheight(), textwrap.fill(subtitulo, width=int(fig.get_figwidth() * 11.5)),
             fontsize=9.5, color=estilo.TINTA_2, va="top", linespacing=1.5)


def guardar(fig, nombre, archivo):
    carpeta = SALIDA_GRAFICAS / normalizar(nombre)
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / archivo
    fig.savefig(ruta, dpi=160)
    plt.close(fig)
    return ruta


def figura_identificacion(resultado):
    nombre, serie, y, modelo = resultado["nombre"], resultado["serie"], resultado["y"], resultado["modelo"]
    pruebas = resultado["pruebas"].set_index("d")
    d = modelo["d"]
    anios = serie.index.to_numpy()
    filas = MAXIMO_D + 1
    alto = 3.2 * filas + 1.9
    fig, ejes = plt.subplots(filas, 3, figsize=(14, alto), gridspec_kw={"width_ratios": [1.5, 1, 1]}, squeeze=False)
    fig.subplots_adjust(left=0.06, right=0.98, top=1 - 1.9 / alto, bottom=0.5 / alto, hspace=0.85, wspace=0.25)
    titulo_figura(fig, f"Identificación · {nombre}: ¿cuántas diferencias necesita la serie?",
                  f"Se elige d = {d} ({modelo['razon_d']}). ADF tiene H0 = raíz unitaria, así que se busca p < {coma(ALFA)}. "
                  f"KPSS tiene H0 = serie estacionaria, así que se busca p > {coma(ALFA)}. Si al diferenciar la ACF en el rezago 1 "
                  f"baja de −0,5 o la serie varía más que antes, es señal de que se diferenció de más.")
    etiquetas_y = {0: "log" if USAR_LOG else UNIDAD, 1: "cambio anual", 2: "cambio del cambio"}
    for k in range(filas):
        x = np.diff(y, n=k)
        fila = pruebas.loc[k]
        elegida = k == d
        texto_fila = "Serie original" if k == 0 else f"Con {k} diferencia{'s' if k > 1 else ''}"
        ax = ejes[k, 0]
        if k > 0:
            ax.axhline(0, color=estilo.EJE, linewidth=0.8)
        ax.plot(anios[k:], x, color=estilo.SERIE_2 if elegida else estilo.SERIE_1, linewidth=1.6)
        ax.set_ylabel(etiquetas_y.get(k, f"diferencia {k}"))
        ax.set_title(f"{texto_fila}{' (elegida)' if elegida else ''}\nADF p {texto_p(fila['adf_p'])} · KPSS p {texto_p_kpss(fila['kpss_p'])}",
                     loc="left", fontsize=10, color=estilo.TINTA, fontweight="bold" if elegida else "normal")
        correlograma(ejes[k, 1], x, f"ACF · rezago 1 = {coma(fila['acf_rezago_1'])}")
        correlograma(ejes[k, 2], x, "PACF", parcial=True)
    return guardar(fig, nombre, "1_identificacion.png")


def figura_comparacion(resultado):
    nombre, modelo, candidatos = resultado["nombre"], resultado["modelo"], resultado["candidatos"]
    d = modelo["d"]
    criterio = NOMBRES_CRITERIO[CRITERIO]
    fig = plt.figure(figsize=(15, 8.5))
    rejilla = fig.add_gridspec(1, 2, width_ratios=[1, 1.15], wspace=0.25, left=0.05, right=0.98, top=0.74, bottom=0.07)
    titulo_figura(fig, f"Modelos probados · {nombre}",
                  f"{len(candidatos)} modelos ARIMA(p,{d},q), con p de 0 a {MAXIMO_P} y q de 0 a {MAXIMO_Q}. Cada casilla es un modelo y el número "
                  f"es su {criterio}: más oscuro es menor, y menor es mejor. Se recorren de menor a mayor {criterio} y se elige el primero con raíces fuera "
                  f"del círculo, coeficientes significativos y residuos sin autocorrelación; normalidad y homocedasticidad desempatan entre modelos "
                  f"con {criterio} a menos de {coma(MARGEN_EMPATE, 0)} del mejor. Letras = lo que falla: R raíces dentro o encima del círculo unitario, "
                  "C algún coeficiente no significativo, L autocorrelación en los residuos (Ljung-Box), N residuos no normales (Shapiro o Jarque-Bera), "
                  "H varianza no constante (ARCH). ✓ = cumple todo. Recuadro naranja = elegido.")
    minimo = candidatos[CRITERIO].min()
    maximo = candidatos[CRITERIO].quantile(0.9)
    if not maximo > minimo:
        maximo = minimo + 1
    rampa = LinearSegmentedColormap.from_list("aic", ["#0d366b", "#1c5cab", "#3987e5", "#86b6ef", "#cde2fb", "#f1f6fd"])

    ax = fig.add_subplot(rejilla[0, 0])
    matriz = np.full((MAXIMO_P + 1, MAXIMO_Q + 1), np.nan)
    for fila in candidatos.itertuples():
        matriz[fila.p, fila.q] = getattr(fila, CRITERIO)
    ax.imshow(np.clip(matriz, minimo, maximo), cmap=rampa, vmin=minimo, vmax=maximo, aspect="auto")
    for p in range(MAXIMO_P + 1):
        for q in range(MAXIMO_Q + 1):
            if np.isnan(matriz[p, q]):
                ax.text(q, p, "—", ha="center", va="center", fontsize=9, color=estilo.TENUE)
    for fila in candidatos.itertuples():
        valor = getattr(fila, CRITERIO)
        nivel = (min(valor, maximo) - minimo) / (maximo - minimo)
        color = "white" if nivel < 0.45 else estilo.TINTA
        ax.text(fila.q, fila.p - 0.14, coma(valor, 1), ha="center", va="center", fontsize=8.5, color=color)
        ax.text(fila.q, fila.p + 0.22, "✓" if fila.cumple_todo else fila.falla, ha="center", va="center",
                fontsize=8, color=color, fontweight="bold")
        if fila.elegido:
            ax.add_patch(Rectangle((fila.q - 0.5, fila.p - 0.5), 1, 1, fill=False, edgecolor=estilo.SERIE_2, linewidth=3.5))
    ax.set_xticks(range(MAXIMO_Q + 1))
    ax.set_yticks(range(MAXIMO_P + 1))
    ax.set_xlabel("q (orden MA)")
    ax.set_ylabel("p (orden AR)")
    ax.grid(False)
    ax.set_title(f"ARIMA(p,{d},q)", loc="left", fontsize=10, color=estilo.TINTA)

    ax = fig.add_subplot(rejilla[0, -1])
    ax.axis("off")
    ax.set_title(f"Recorrido de menor a mayor {criterio}", loc="left", fontsize=10, color=estilo.TINTA)
    ordenados = candidatos[candidatos["converge"]] if candidatos["converge"].any() else candidatos
    ordenados = ordenados.reset_index(drop=True)
    posiciones = list(np.flatnonzero(ordenados["elegido"].to_numpy()))
    mostrar = list(range(min(len(ordenados), 11)))
    if posiciones and posiciones[0] >= 11:
        mostrar = list(range(9)) + [None, posiciones[0]]
    y = 0.98
    for i in mostrar:
        if i is None:
            ax.text(0, y, "…", transform=ax.transAxes, va="top", fontsize=9, color=estilo.TINTA_2)
            y -= 0.05
            continue
        fila = ordenados.iloc[i]
        elegido = bool(fila["elegido"])
        fallas = [texto for columna, (_, texto) in CHEQUEOS.items() if not fila[columna]]
        estado = "cumple todo" if not fallas else "falla: " + ", ".join(fallas)
        linea = f"{i + 1}. {etiqueta_modelo(int(fila['p']), d, int(fila['q']))} · {criterio} = {coma(fila[CRITERIO], 1)}"
        ax.text(0, y, f"{linea}{'   ← elegido' if elegido else ''}\n      {estado}", transform=ax.transAxes, va="top", fontsize=8.5,
                color=estilo.TINTA if elegido else estilo.TINTA_2, fontweight="bold" if elegido else "normal", linespacing=1.4)
        y -= 0.085
    if modelo["origen"] == "manual":
        ax.text(0, max(y, 0.02), "El modelo final se fijó a mano en ORDENES_MANUALES.", transform=ax.transAxes, va="top",
                fontsize=8.5, color=estilo.TINTA, fontweight="bold")
    return guardar(fig, nombre, "2_comparacion_aicc.png")


def grafica_raices(ax, tabla):
    angulo = np.linspace(0, 2 * np.pi, 400)
    ax.plot(np.cos(angulo), np.sin(angulo), color=estilo.TINTA_2, linewidth=1.2)
    ax.set_title("Raíces de los polinomios AR y MA\n(deben quedar fuera del círculo de radio 1)", loc="left", fontsize=10, color=estilo.TINTA)
    ax.grid(False)
    if tabla.empty:
        ax.text(0, 0, "El modelo no tiene\nparte AR ni MA:\nno hay raíces que revisar", ha="center", va="center", fontsize=9, color=estilo.TINTA_2)
        limite = 1.6
    else:
        ax.axhline(0, color=estilo.EJE, linewidth=0.8)
        ax.axvline(0, color=estilo.EJE, linewidth=0.8)
        limite = min(max(1.6, tabla["modulo"].max() * 1.2), 3.5)
        for polinomio, marcador, color in (("AR", "x", estilo.SERIE_1), ("MA", "o", estilo.SERIE_2)):
            sub = tabla[tabla["polinomio"] == polinomio]
            if sub.empty:
                continue
            modulos = ", ".join(coma(m) for m in sub["modulo"])
            if marcador == "x":
                ax.scatter(sub["real"].clip(-limite, limite), sub["imaginaria"], marker="x", s=80, color=color, linewidths=2, zorder=3,
                           label=f"Raíz {polinomio}: |z| = {modulos}")
            else:
                ax.scatter(sub["real"].clip(-limite, limite), sub["imaginaria"], marker="o", s=70, facecolors="none", edgecolors=color,
                           linewidths=2, zorder=3, label=f"Raíz {polinomio}: |z| = {modulos}")
        ax.legend(loc="lower left", fontsize=8)
    ax.set_xlim(-limite, limite)
    ax.set_ylim(-limite, limite)
    ax.set_aspect("equal")
    ax.set_xlabel("parte real")
    ax.set_ylabel("parte imaginaria")


def grafica_coeficientes(ax, tabla):
    datos = tabla[tabla["parametro"] != "sigma2"].reset_index(drop=True)
    critico = stats.norm.ppf(1 - ALFA / 2)
    ax.set_title(f"Significancia de los coeficientes\n(|z| > {coma(critico)} es significativo al {coma(ALFA * 100, 0)} %)",
                 loc="left", fontsize=10, color=estilo.TINTA)
    if datos.empty:
        ax.axis("off")
        ax.text(0.5, 0.5, "El modelo no tiene coeficientes\naparte de la varianza", ha="center", va="center",
                fontsize=9, color=estilo.TINTA_2, transform=ax.transAxes)
        return
    z = (datos["estimacion"] / datos["error_estandar"]).to_numpy()
    posiciones = np.arange(len(datos))
    ax.axvspan(-critico, critico, color=estilo.GRILLA, alpha=0.8, linewidth=0)
    ax.barh(posiciones, z, color=[estilo.SERIE_1 if valor < ALFA else estilo.EJE for valor in datos["p_valor"]], height=0.45)
    ax.axvline(0, color=estilo.TINTA_2, linewidth=0.8)
    for i, (valor, p_valor) in enumerate(zip(z, datos["p_valor"])):
        ax.text(valor, i - 0.36, f"p {texto_p(p_valor)}", ha="center", va="bottom", fontsize=8, color=estilo.TINTA_2)
    ax.set_yticks(posiciones)
    ax.set_yticklabels([f"{f.parametro} = {coma(f.estimacion, 3)}" for f in datos.itertuples()])
    ax.set_ylim(len(datos) - 0.5, -0.8)
    limite = max(np.nanmax(np.abs(z)) * 1.3, critico * 1.8)
    ax.set_xlim(-limite, limite)
    ax.set_xlabel("z = estimación / error estándar")
    ax.grid(axis="x", visible=True)
    ax.grid(axis="y", visible=False)


def figura_diagnostico(resultado):
    nombre, modelo, residuos = resultado["nombre"], resultado["modelo"], resultado["residuos"]
    p, d, q = modelo["p"], modelo["d"], modelo["q"]
    anios = resultado["serie"].index.to_numpy()
    ljung_ok = min(modelo[f"ljung_box_p_{r}"] for r in REZAGOS_LJUNG_BOX) > ALFA
    normal_ok = modelo["shapiro_p"] > ALFA and modelo["jarque_bera_p"] > ALFA
    arch_ok = modelo["arch_p"] > ALFA
    coef_ok = not modelo["coef_no_significativos"]
    fallas = [texto for texto, ok in (("raíces", modelo["raices_ok"]), ("significancia", coef_ok), ("autocorrelación", ljung_ok),
                                      ("normalidad", normal_ok), ("varianza constante", arch_ok)) if not ok]
    conclusion = "el modelo cumple todos los supuestos." if not fallas else f"revisar {', '.join(fallas)}."
    fig = plt.figure(figsize=(14, 10))
    rejilla = fig.add_gridspec(2, 3, hspace=0.6, wspace=0.42, left=0.07, right=0.98, top=0.8, bottom=0.07)
    titulo_figura(fig, f"Diagnóstico · {nombre} · {etiqueta_modelo(p, d, q)}",
                  f"Raíces fuera del círculo unitario: {'sí' if modelo['raices_ok'] else 'no'}. "
                  f"Coeficientes significativos: {'sí' if coef_ok else 'no (' + modelo['coef_no_significativos'] + ')'}. "
                  f"Residuos sin autocorrelación: {'sí' if ljung_ok else 'no'}. Residuos normales: {'sí' if normal_ok else 'no'}. "
                  f"Varianza constante (ARCH-LM): {'sí' if arch_ok else 'no'}. Conclusión: {conclusion}")

    grafica_raices(fig.add_subplot(rejilla[0, 0]), resultado["raices"])
    grafica_coeficientes(fig.add_subplot(rejilla[0, 1]), resultado["coeficientes"])

    ax = fig.add_subplot(rejilla[0, 2])
    ax.axhline(0, color=estilo.EJE, linewidth=0.8)
    ax.plot(anios[d:], residuos, color=estilo.SERIE_1, linewidth=1.2, marker="o", markersize=3)
    ax.set_ylabel("log" if USAR_LOG else UNIDAD)
    ax.set_title(f"Residuos en el tiempo\nARCH-LM p {texto_p(modelo['arch_p'])}",
                 loc="left", fontsize=10, color=estilo.TINTA)

    texto_lb = ", ".join(f"p {texto_p(modelo[f'ljung_box_p_{r}'])} ({r} rezagos)" for r in REZAGOS_LJUNG_BOX)
    correlograma(fig.add_subplot(rejilla[1, 0]), residuos, f"ACF de los residuos\nLjung-Box: {texto_lb}")

    estandarizados = residuos / residuos.std(ddof=1)
    ax = fig.add_subplot(rejilla[1, 1])
    ax.hist(estandarizados, bins=10, density=True, color=estilo.SERIE_1, alpha=0.55, edgecolor=estilo.SUPERFICIE)
    extremo = max(3.5, np.abs(estandarizados).max() + 0.5)
    malla = np.linspace(-extremo, extremo, 300)
    ax.plot(malla, stats.norm.pdf(malla), color=estilo.TINTA, linewidth=1.2)
    ax.set_xlabel("Residuos estandarizados")
    ax.set_title(f"Histograma con la curva normal\nShapiro-Wilk p {texto_p(modelo['shapiro_p'])}", loc="left", fontsize=10, color=estilo.TINTA)

    ax = fig.add_subplot(rejilla[1, 2])
    (teoricos, ordenados), (pendiente, intercepto, _) = stats.probplot(estandarizados, dist="norm")
    ax.scatter(teoricos, ordenados, s=16, color=estilo.SERIE_1, zorder=3)
    ax.plot(teoricos, pendiente * teoricos + intercepto, color=estilo.TINTA, linewidth=1)
    ax.set_xlabel("Cuantiles teóricos normales")
    ax.set_ylabel("Residuos estandarizados")
    ax.set_title(f"Q-Q normal\nJarque-Bera p {texto_p(modelo['jarque_bera_p'])}", loc="left", fontsize=10, color=estilo.TINTA)
    return guardar(fig, nombre, "3_diagnostico.png")


def figura_pronostico(resultado):
    nombre, serie, res, modelo = resultado["nombre"], resultado["serie"], resultado["res"], resultado["modelo"]
    pronostico = resultado["pronostico"]
    p, d, q = modelo["p"], modelo["d"], modelo["q"]
    anios = serie.index.to_numpy()
    inicio_validacion = int(anios[-ANIOS_VALIDACION])
    fig, ax = plt.subplots(figsize=(14, 6.5))
    fig.subplots_adjust(left=0.06, right=0.98, top=0.8, bottom=0.09)
    titulo_figura(fig, f"{NOMBRE_VARIABLE} · {nombre} · pronóstico {pronostico['anio'].iloc[0]}–{pronostico['anio'].iloc[-1]}",
                  f"{etiqueta_modelo(p, d, q)}. Validación: si se ajusta hasta {inicio_validacion - 1} y se pronostica "
                  f"{inicio_validacion}–{int(anios[-1])}, el error promedio es {coma(modelo['mape_validacion'], 1)} %. "
                  f"La banda es el intervalo del {coma((1 - ALFA) * 100, 0)} %, que se abre con los años.")
    ajuste = revertir(np.asarray(res.fittedvalues, dtype=float))
    ax.plot(anios, serie.to_numpy(), color=estilo.SERIE_1, linewidth=2, label="Observado (MapBiomas)")
    ax.plot(anios[d:], ajuste[d:], color=estilo.TENUE, linestyle="--", linewidth=1.2, label="Ajuste a un paso")
    ax.fill_between(np.r_[anios[-1], pronostico["anio"]], np.r_[serie.iloc[-1], pronostico["limite_inferior"]],
                    np.r_[serie.iloc[-1], pronostico["limite_superior"]],
                    color=estilo.SERIE_2, alpha=0.15, linewidth=0, label=f"Intervalo del {coma((1 - ALFA) * 100, 0)} %")
    ax.plot(np.r_[anios[-1], pronostico["anio"]], np.r_[serie.iloc[-1], pronostico["pronostico"]],
            color=estilo.SERIE_2, linewidth=2, label="Pronóstico")
    ax.set_ylabel(UNIDAD)
    ax.legend(loc="upper left", fontsize=9)
    return guardar(fig, nombre, "4_pronostico.png")


def figura_resumen(resultados):
    columnas = 4
    filas = math.ceil(len(resultados) / columnas)
    fig, ejes = plt.subplots(filas, columnas, figsize=(16, 3.8 * filas + 1.5), squeeze=False)
    fig.subplots_adjust(left=0.05, right=0.98, top=0.82, bottom=0.06, hspace=0.6, wspace=0.28)
    fig.text(0.05, 0.955, f"{NOMBRE_VARIABLE}: observado y pronóstico ARIMA", fontsize=14, fontweight="bold", color=estilo.TINTA)
    fig.text(0.05, 0.92, f"MapBiomas Colombia, {UNIDAD}. Banda: intervalo del {coma((1 - ALFA) * 100, 0)} %.", fontsize=9.5, color=estilo.TINTA_2)
    for ax, resultado in zip(ejes.ravel(), resultados):
        serie, pronostico, modelo = resultado["serie"], resultado["pronostico"], resultado["modelo"]
        ax.plot(serie.index, serie.to_numpy(), color=estilo.SERIE_1, linewidth=1.8)
        ax.fill_between(np.r_[serie.index[-1], pronostico["anio"]], np.r_[serie.iloc[-1], pronostico["limite_inferior"]],
                        np.r_[serie.iloc[-1], pronostico["limite_superior"]], color=estilo.SERIE_2, alpha=0.15, linewidth=0)
        ax.plot(np.r_[serie.index[-1], pronostico["anio"]], np.r_[serie.iloc[-1], pronostico["pronostico"]], color=estilo.SERIE_2, linewidth=1.8)
        ax.set_title(f"{resultado['nombre']}\n{etiqueta_modelo(modelo['p'], modelo['d'], modelo['q'])}", loc="left", fontsize=9.5, color=estilo.TINTA)
    for ax in ejes.ravel()[len(resultados):]:
        ax.set_visible(False)
    ruta = SALIDA_GRAFICAS / "arima_resumen.png"
    fig.savefig(ruta, dpi=160)
    plt.close(fig)
    return ruta


def reportar(resultado):
    m = resultado["modelo"]
    pruebas = resultado["pruebas"].set_index("d")
    print(f"{m['serie']}: d = {m['d']} ({m['razon_d']}; ADF p = {pruebas.loc[m['d'], 'adf_p']:.3f}, KPSS p = {pruebas.loc[m['d'], 'kpss_p']:.3f})")
    print(f"  {etiqueta_modelo(m['p'], m['d'], m['q'])} [{m['origen']}], AICc = {m['aicc']:.1f}")
    if not pd.isna(m["puesto_criterio"]):
        print(f"  Puesto {m['puesto_criterio']} de {m['modelos_probados']} por {m['criterio']}: {m['razon_eleccion']}")
    rezago = REZAGOS_LJUNG_BOX[-1]
    print(f"  Ljung-Box p = {m[f'ljung_box_p_{rezago}']:.3f}, Jarque-Bera p = {m['jarque_bera_p']:.3f}, "
          f"Shapiro p = {m['shapiro_p']:.3f}, ARCH p = {m['arch_p']:.3f}")
    print(f"  Error fuera de muestra (últimos {ANIOS_VALIDACION} años): {m['mape_validacion']:.1f} % en promedio")
    avisos = []
    if not m["raices_ok"]:
        avisos.append("hay raíces dentro del círculo unitario")
    if m["coef_no_significativos"]:
        avisos.append(f"coeficientes no significativos: {m['coef_no_significativos']}")
    if min(m[f"ljung_box_p_{r}"] for r in REZAGOS_LJUNG_BOX) <= ALFA:
        avisos.append("los residuos tienen autocorrelación (Ljung-Box)")
    if m["jarque_bera_p"] <= ALFA or m["shapiro_p"] <= ALFA:
        avisos.append("los residuos no parecen normales")
    if m["arch_p"] <= ALFA:
        avisos.append("hay heterocedasticidad condicional (ARCH)")
    if pruebas.loc[m["d"], "acf_rezago_1"] < -0.5:
        avisos.append("posible sobrediferenciación (ACF en el rezago 1 menor que -0,5)")
    for aviso in avisos:
        print(f"  Atención: {aviso}")
    print(flush=True)


def main():
    estilo.aplicar()
    SALIDA_DATOS.mkdir(parents=True, exist_ok=True)
    SALIDA_GRAFICAS.mkdir(parents=True, exist_ok=True)

    series = cargar_series()
    print(f"Se prueban hasta {(MAXIMO_P + 1) * (MAXIMO_Q + 1)} modelos por serie.\n", flush=True)
    resultados = []
    for nombre, serie in series.items():
        resultado = modelar(nombre, serie)
        resultado["rutas"] = [figura_identificacion(resultado), figura_comparacion(resultado),
                              figura_diagnostico(resultado), figura_pronostico(resultado)]
        resultados.append(resultado)
        reportar(resultado)
    ruta_resumen = figura_resumen(resultados)

    pd.concat([r["serie"].rename("valor").rename_axis("anio").reset_index().assign(serie=r["nombre"]) for r in resultados], ignore_index=True)[
        ["serie", "anio", "valor"]].to_csv(SALIDA_DATOS / "series_modeladas.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([r["modelo"] for r in resultados]).to_csv(SALIDA_DATOS / "modelos.csv", index=False, encoding="utf-8-sig")
    for clave, archivo in (("pruebas", "estacionariedad.csv"), ("candidatos", "candidatos.csv"), ("coeficientes", "coeficientes.csv"),
                           ("raices", "raices.csv"), ("pronostico", "pronosticos.csv")):
        tablas = [r[clave] for r in resultados if not r[clave].empty]
        tabla = pd.concat(tablas, ignore_index=True) if tablas else resultados[0][clave]
        tabla.to_csv(SALIDA_DATOS / archivo, index=False, encoding="utf-8-sig")
    print(f"\nTablas en {SALIDA_DATOS}")
    print(f"Gráficas en {SALIDA_GRAFICAS}: una carpeta por serie y el resumen {ruta_resumen.name}")


if __name__ == "__main__":
    main()