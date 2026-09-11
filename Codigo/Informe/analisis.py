"""
Analisis de calidad y evaluacion de la red (secciones 4, 5 y 7 del informe pluviometrico).
"""
import numpy as np
import pandas as pd

from Codigo.Instalador.Funciones_exportar import (
    FRECUENCIA, UMBRAL_ALTO, UMBRAL_BAJO, UMBRAL_OUTLIER_5MIN, UMBRAL_OUTLIER_10MIN,
    dia_pluviometrico)

# Un equipo se descarta del analisis si le falta mas de esta fraccion del mes.
UMBRAL_DATOS_FALTANTES = 0.5

# Correlacion minima contra el dia tipico de la red para considerar consistente a un equipo.
UMBRAL_CORRELACION = 0.7

# Un hueco de cobertura se cuenta como "salto" a partir de esta cantidad de minutos.
MINUTOS_SALTO = 30


def datos_faltantes(datos):
    """
    Seccion 4.1: porcentaje de rangos de 5 minutos sin lectura para cada equipo.

    Parametros:
    - datos: Instancia de DatosMes.

    Retorna:
    - DataFrame con ID, Lugar, porcentaje faltante y si se descarta por ese motivo.
    """
    total = len(datos.df_cobertura)

    faltante = (1 - datos.df_cobertura.sum() / total) * 100

    tabla = pd.DataFrame({
        'ID': faltante.index,
        'Lugar': [datos.nombre_de(i) for i in faltante.index],
        'Datos faltantes (%)': faltante.round(2).values,
    })
    tabla['Descartar por faltantes'] = tabla['Datos faltantes (%)'] > UMBRAL_DATOS_FALTANTES * 100

    return tabla.sort_values('Datos faltantes (%)', ascending=False).reset_index(drop=True)


def matriz_correlacion(datos):
    """
    Seccion 4.3: correlacion de Pearson entre los acumulados diarios de todos los equipos,
    con INUMET incluido si esta disponible. Es una comparacion contra INUMET, asi que los dias
    van de 7 a 7, como los suyos.

    Se conserva solo el triangulo superior, que es como se presenta en la Tabla 4-1.

    Parametros:
    - datos: Instancia de DatosMes.

    Retorna:
    - DataFrame de correlaciones redondeado, con celdas vacias bajo la diagonal.
    """
    df = datos.diario_con_inumet()

    # Se sacan los dias sin lluvia en ningun equipo: no aportan y ensucian la correlacion.
    df = df[(df.fillna(0) != 0).any(axis=1)]

    correlacion = df.corr().round(2)

    triangulo = np.triu(np.ones(correlacion.shape, dtype=bool))

    return correlacion.where(triangulo).astype(object).where(triangulo, '')


def outliers(datos):
    """
    Seccion 4.4: registros anomalos por intensidad.

    Se aplican los dos criterios del informe: mas de 25 mm en un rango de 5 minutos (que ya
    vienen descartados de la tabla refinada) y mas de 50 mm en 10 minutos consecutivos.

    Parametros:
    - datos: Instancia de DatosMes.

    Retorna:
    - DataFrame con ID, Lugar, fecha/hora, valor y criterio que se supero.
    """
    filas = []

    for _, descarte in datos.df_descartes.iterrows():
        filas.append({
            'ID': descarte.get('ID', descarte['Pluviometro']),
            'Lugar': descarte['Pluviometro'],
            'Fecha y hora': descarte['Fecha y hora'],
            'Valor (mm)': round(descarte['Valor descartado (mm)'], 2),
            'Criterio': f'> {UMBRAL_OUTLIER_5MIN} mm en 5 min',
        })

    # Ventana movil de dos rangos = 10 minutos consecutivos.
    en_10min = datos.df_5min.rolling(2, min_periods=1).sum()

    for identificador in en_10min.columns:
        serie = en_10min[identificador]
        for marca, valor in serie[serie > UMBRAL_OUTLIER_10MIN].items():
            filas.append({
                'ID': identificador,
                'Lugar': datos.nombre_de(identificador),
                'Fecha y hora': marca,
                'Valor (mm)': round(valor, 2),
                'Criterio': f'> {UMBRAL_OUTLIER_10MIN} mm en 10 min',
            })

    tabla = pd.DataFrame(filas, columns=['ID', 'Lugar', 'Fecha y hora', 'Valor (mm)', 'Criterio'])

    return tabla.sort_values('Fecha y hora').reset_index(drop=True) if len(tabla) else tabla


def correlacion_con_la_red(datos):
    """
    Correlacion de cada equipo contra el dia tipico de la red (la mediana entre equipos).

    Detecta al equipo que mide cantidades plausibles pero en los dias equivocados, que es lo
    que ni el total mensual ni el porcentaje de faltantes llegan a ver.

    Parametros:
    - datos: Instancia de DatosMes.

    Retorna:
    - Serie de correlaciones indexada por ID de equipo.
    """
    return datos.df_diario.corrwith(datos.df_diario.median(axis=1))


def problemas_identificados(datos):
    """
    Seccion 5: arma la lista candidata de equipos con problemas y la razon de cada uno.

    La decision final de descartar o no es humana (el informe de agosto conserva Paso de la
    Arena pese a tener problemas), asi que esto entrega una sugerencia editable, no un veredicto.

    Parametros:
    - datos: Instancia de DatosMes.

    Retorna:
    - DataFrame con ID, Lugar, Motivo y Descartar (sugerencia).
    """
    faltantes = datos_faltantes(datos).set_index('ID')
    correlaciones = correlacion_con_la_red(datos)
    totales = datos.df_diario.sum(min_count=1)
    mediana = totales.median()
    con_outliers = set(datos.df_descartes['ID']) if 'ID' in datos.df_descartes else set()

    filas = []
    for identificador in datos.df_diario.columns:
        total = totales[identificador]
        correlacion = correlaciones[identificador]
        porcentaje_faltante = faltantes.loc[identificador, 'Datos faltantes (%)']

        motivos = []
        descartar = False

        if porcentaje_faltante > UMBRAL_DATOS_FALTANTES * 100:
            motivos.append(f"presenta {porcentaje_faltante:.2f} % de datos faltantes en el mes")
            descartar = True

        if pd.isna(total) or total == 0:
            motivos.append("no registro precipitacion en todo el mes")
            descartar = True
        elif mediana > 0 and total < UMBRAL_BAJO * mediana:
            motivos.append(f"registro {total:.1f} mm frente a {mediana:.1f} mm de mediana de la red")
            descartar = True
        elif mediana > 0 and total > UMBRAL_ALTO * mediana:
            # Medir de mas no alcanza para descartar: los equipos de la costa y del oeste
            # acumulan bastante mas que la mediana en tormentas que entran por ahi. Solo se
            # sugiere descartarlo si ademas llovio en dias distintos que en el resto de la red,
            # cosa que evalua el criterio de correlacion de mas abajo.
            motivos.append(f"registro {total:.1f} mm frente a {mediana:.1f} mm de mediana de la red")

        if pd.notna(correlacion) and correlacion < UMBRAL_CORRELACION and total:
            motivos.append(f"sus registros no son consistentes con los del resto de la red "
                           f"(correlacion {correlacion:.2f})")
            descartar = True

        if identificador in con_outliers:
            motivos.append("presento registros anomalos a lo largo del mes")

        if motivos:
            filas.append({
                'ID': identificador,
                'Lugar': datos.nombre_de(identificador),
                'Motivo': "; ".join(motivos).capitalize() + ".",
                'Descartar': descartar,
            })

    return pd.DataFrame(filas, columns=['ID', 'Lugar', 'Motivo', 'Descartar'])


def acumulados_mensuales(datos, descartados=()):
    """
    Seccion 6.1: acumulado mensual de cada equipo conservado, mas INUMET.

    Parametros:
    - datos: Instancia de DatosMes.
    - descartados: IDs de equipos excluidos del analisis.

    Retorna:
    - Serie de acumulados mensuales en mm.
    """
    conservados = [c for c in datos.df_diario.columns if c not in set(descartados)]

    totales = datos.df_diario[conservados].sum(min_count=1).round(1)

    if datos.inumet is not None:
        totales['INUMET'] = round(datos.inumet.sum(min_count=1), 1)

    return totales


def dia_de_mayor_precipitacion(datos, descartados=()):
    """
    Dia del mes con mayor precipitacion registrada, que es sobre el que se evalua el
    funcionamiento de la red en la seccion 7.

    Parametros:
    - datos: Instancia de DatosMes.
    - descartados: IDs de equipos excluidos del analisis.

    Retorna:
    - Tupla (dia, id_equipo, valor_maximo).
    """
    conservados = [c for c in datos.df_diario.columns if c not in set(descartados)]
    df = datos.df_diario[conservados]

    dia = df.max(axis=1).idxmax()
    equipo = df.loc[dia].idxmax()

    return dia, equipo, round(df.loc[dia, equipo], 1)


def contar_saltos(cobertura_dia):
    """
    Cuenta los huecos de cobertura de un equipo dentro de un dia.

    Parametros:
    - cobertura_dia: Serie booleana de cobertura, un valor por rango de 5 minutos.

    Retorna:
    - Cantidad de huecos que superan MINUTOS_SALTO.
    """
    rangos_por_salto = MINUTOS_SALTO // int(pd.Timedelta(FRECUENCIA).total_seconds() // 60)

    sin_dato = (~cobertura_dia).astype(int)
    grupos = (cobertura_dia != cobertura_dia.shift()).cumsum()

    largos = sin_dato.groupby(grupos).sum()

    return int((largos >= rangos_por_salto).sum())


def evaluacion_de_la_red(datos, dia):
    """
    Seccion 7: clasifica el registro de cada equipo durante el dia de mayor precipitacion.

    Criterios, alineados con los que usa el informe:
    - Regular: el equipo no reporto nada en todo el dia (estaba desconectado).
    - Malo: reporto pero no registro lluvia mientras la red si, o midio algo incoherente
      con el resto de la red.
    - Bien: registro completo y coherente, aunque haya tenido saltos en la transmision.

    Parametros:
    - datos: Instancia de DatosMes.
    - dia: Dia civil a evaluar.

    Retorna:
    - DataFrame con ID, Lugar, Analisis y Lectura.
    """
    del_dia = dia_pluviometrico(datos.df_5min.index) == pd.Timestamp(dia)

    acumulado = datos.df_5min[del_dia].sum(min_count=1)
    cobertura = datos.df_cobertura[del_dia]
    mediana = acumulado.median()

    filas = []
    for identificador in datos.df_5min.columns:
        total = acumulado[identificador]
        cobertura_equipo = cobertura[identificador]
        saltos = contar_saltos(cobertura_equipo)
        porcentaje_nulos = (1 - cobertura_equipo.mean()) * 100

        if not cobertura_equipo.any():
            lectura = 'Regular'
            analisis = "El equipo no se encontraba conectado el dia del evento."
        elif total == 0 and mediana > 0:
            lectura = 'Malo'
            analisis = "El equipo no registro precipitacion durante la duracion del evento."
        elif porcentaje_nulos > UMBRAL_DATOS_FALTANTES * 100:
            lectura = 'Malo'
            analisis = (f"Presenta un porcentaje de datos nulos del {porcentaje_nulos:.2f} % "
                        f"durante el evento.")
        elif mediana > 0 and total < UMBRAL_BAJO * mediana:
            # Solo se penaliza medir de menos. Los equipos de la costa y del oeste suelen
            # acumular bastante mas que la mediana en las tormentas que entran por ahi, y eso
            # no es una falla del equipo.
            lectura = 'Malo'
            analisis = ("Presenta registro de datos de precipitacion durante el evento "
                        "pero sus valores no son consistentes.")
        elif saltos:
            lectura = 'Bien'
            analisis = (f"Presenta {'un salto' if saltos == 1 else f'{saltos} saltos'} en el "
                        f"registro de datos de precipitacion durante el evento y sus valores "
                        f"son consistentes.")
        else:
            lectura = 'Bien'
            analisis = "Presenta registro de datos completo de precipitacion durante el evento."

        filas.append({'ID': identificador, 'Lugar': datos.nombre_de(identificador),
                      'Analisis del registro de mediciones': analisis, 'Lectura': lectura})

    tabla = pd.DataFrame(filas)

    # Los que registraron bien primero, que es el orden en que los lista el informe.
    orden = {'Bien': 0, 'Regular': 1, 'Malo': 2}
    return tabla.sort_values(['Lectura', 'Lugar'], key=lambda c: c.map(orden).fillna(c)) \
                .reset_index(drop=True)


def indicador_de_funcionamiento(tabla_evaluacion):
    """
    Indicador de la seccion 7: equipos con registro optimo sobre el total de la red.

    Parametros:
    - tabla_evaluacion: Salida de evaluacion_de_la_red.

    Retorna:
    - Tupla (cantidad_bien, total_equipos, porcentaje).
    """
    bien = int((tabla_evaluacion['Lectura'] == 'Bien').sum())
    total = len(tabla_evaluacion)

    return bien, total, round(bien / total * 100) if total else 0
