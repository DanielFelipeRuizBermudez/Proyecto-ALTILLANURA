from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest


def pruebas(adf, kpss, acf_rezago_1=None, desviacion=None):
    n = len(adf)
    return pd.DataFrame({
        "d": range(n),
        "adf_p": adf,
        "kpss_p": kpss,
        "acf_rezago_1": acf_rezago_1 or [0.0] * n,
        "desviacion": desviacion or [1.0] * n,
    })


def candidatos(filas):
    columnas = ["p", "q", "aicc", "raices_ok", "coef_significativos", "ljung_box_ok", "normalidad_ok", "homocedasticidad_ok"]
    tabla = pd.DataFrame(filas, columns=columnas)
    tabla["converge"] = True
    return tabla.sort_values("aicc").reset_index(drop=True)


def orden(tabla, indice):
    return int(tabla.loc[indice, "p"]), int(tabla.loc[indice, "q"])


def test_d_cuando_adf_y_kpss_coinciden(arima):
    assert arima.elegir_d(pruebas([0.6, 0.01, 0.001], [0.01, 0.1, 0.1])) == (1, "ADF y KPSS coinciden")


def test_d_menor_si_hay_sobrediferenciacion(arima):
    tabla = pruebas([0.6, 0.2, 0.001], [0.01, 0.1, 0.1], [0.9, 0.1, -0.6], [10, 2, 3])
    d, razon = arima.elegir_d(tabla)
    assert d == 1
    assert razon == "ADF y KPSS no coinciden y con d = 2 hay señales de sobrediferenciación"


def test_d_mayor_sin_sobrediferenciacion(arima):
    tabla = pruebas([0.6, 0.2, 0.001], [0.01, 0.1, 0.1], [0.9, 0.1, -0.2], [10, 3, 2])
    assert arima.elegir_d(tabla)[0] == 2


def test_d_cuando_ninguna_prueba_indica_estacionariedad(arima):
    tabla = pruebas([0.6, 0.3, 0.2], [0.01, 0.02, 0.03], desviacion=[5, 2, 3])
    assert arima.elegir_d(tabla)[0] == 1


def test_caminata_aleatoria_se_diferencia_una_vez(arima, generador):
    y = np.cumsum(generador.normal(size=200))
    assert arima.elegir_d(arima.pruebas_estacionariedad(y))[0] == 1


def test_ruido_blanco_no_se_diferencia(arima, generador):
    y = generador.normal(size=200)
    assert arima.elegir_d(arima.pruebas_estacionariedad(y))[0] == 0


def test_ajusta_un_ar1_simulado(arima, generador):
    ruido = generador.normal(size=300)
    y = np.zeros(300)
    for t in range(1, 300):
        y[t] = 0.7 * y[t - 1] + ruido[t]
    res, error = arima.ajustar(y, 1, 0, 0)
    assert error is None
    tabla = arima.coeficientes(res).set_index("parametro")
    assert set(tabla.index) == {"media", "ar.L1", "sigma2"}
    assert tabla.loc["ar.L1", "estimacion"] == pytest.approx(0.7, abs=0.1)


def test_la_constante_se_reporta_como_media(arima):
    res = SimpleNamespace(
        model=SimpleNamespace(param_names=["const", "ar.L1", "sigma2"]),
        params=[10.0, 0.5, 1.0],
        bse=[1.0, 0.1, 0.2],
        pvalues=[0.0, 0.0, 0.0],
    )
    assert list(arima.coeficientes(res)["parametro"]) == ["media", "ar.L1", "sigma2"]


def test_raices_de_los_polinomios_ar_y_ma(arima):
    tabla = pd.DataFrame({"parametro": ["ar.L1", "ma.L1", "sigma2"], "estimacion": [0.5, 0.25, 1.0]})
    raices = arima.raices(tabla).set_index("polinomio")
    assert raices.loc["AR", "modulo"] == pytest.approx(2)
    assert raices.loc["MA", "modulo"] == pytest.approx(4)


def test_raiz_unitaria_no_pasa_el_chequeo(arima):
    tabla = pd.DataFrame({"parametro": ["ar.L1"], "estimacion": [1.0]})
    assert not (arima.raices(tabla)["modulo"] > arima.MODULO_MINIMO).all()


def test_descarta_el_mejor_aicc_si_falla_un_supuesto_exigido(arima):
    tabla = candidatos([
        (2, 2, 100.0, False, True, True, True, True),
        (1, 1, 105.0, True, True, True, True, True),
    ])
    indice, razon = arima.seleccionar(tabla)
    assert orden(tabla, indice) == (1, 1)
    assert razon == "el de menor AICc que cumple todos los supuestos"


def test_prefiere_el_que_cumple_todo_si_esta_dentro_del_margen(arima):
    tabla = candidatos([
        (0, 1, 100.0, True, True, True, False, True),
        (1, 1, 101.5, True, True, True, True, True),
    ])
    indice, razon = arima.seleccionar(tabla)
    assert orden(tabla, indice) == (1, 1)
    assert razon.startswith("cumple todos los supuestos")


def test_fuera_del_margen_se_queda_el_de_menor_aicc(arima):
    tabla = candidatos([
        (0, 1, 100.0, True, True, True, False, True),
        (1, 1, 103.0, True, True, True, True, True),
    ])
    indice, razon = arima.seleccionar(tabla)
    assert orden(tabla, indice) == (0, 1)
    assert razon == "el de menor AICc que cumple raíces, coeficientes y Ljung-Box (falla normalidad)"


def test_ningun_modelo_cumple_los_supuestos(arima):
    tabla = candidatos([
        (0, 1, 100.0, True, False, True, True, True),
        (1, 1, 101.0, False, True, True, True, True),
    ])
    indice, razon = arima.seleccionar(tabla)
    assert orden(tabla, indice) == (0, 1)
    assert razon.startswith("ningún modelo cumple")
