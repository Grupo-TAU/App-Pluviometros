from Codigo.Instalador.Funciones_basicas import *

# Hora de corte del dia de medicion: cada dia va de las 07:00 a las 07:00 del dia siguiente.
# Poner HORA_CORTE = 0 vuelve al dia civil (00:00 a 00:00) sin tocar nada mas: la ventana del
# mes, el reinicio de las diferencias y la etiqueta de cada dia se derivan todas de aca.
HORA_CORTE = 7

# Un dia que cierra a las 07:00 se etiqueta con su fecha de cierre, asi que abre el dia
# anterior. El dia civil abre en su propia fecha y no lleva desplazamiento.
DESPLAZAMIENTO_DIA = pd.Timedelta(days=1) if HORA_CORTE else pd.Timedelta(0)

# Ancho de los rangos de la tabla de acumulados finos.
FRECUENCIA = '5min'

# Umbrales del control de calidad, como proporcion de la mediana de la red y correlacion
# minima contra el dia tipico. Calibrados sobre datos reales: los equipos sanos quedan
# entre 0.97 y 0.999 de correlacion, y los fallados por debajo de 0.6.
UMBRAL_BAJO = 0.3
UMBRAL_ALTO = 1.75
UMBRAL_CORRELACION = 0.7

# Lluvia maxima admisible en un rango de 5 minutos. Por encima de esto no se toma como lluvia
# sino como falla del equipo: 25 mm en 5 minutos equivalen a 300 mm/h sostenidos, muy por encima
# de cualquier intensidad real en Montevideo. El rango se descarta en vez de contarse.
UMBRAL_OUTLIER_5MIN = 25


def leer_datos_crudos(archivo):
    """
    Lee el CSV de Grafana conservando todas las lecturas originales, sin redondear a 5 minutos.

    A diferencia de leer_archivo_principal(), que redondea y colapsa a una lectura por
    intervalo, aca se necesitan todas las lecturas crudas: cuando llueve fuerte los
    pluviometros reportan varias veces dentro del mismo rango de 5 minutos y esas
    diferencias intermedias forman parte del acumulado del rango.

    Parametros:
    - archivo: Ruta del CSV exportado de Grafana.

    Retorna:
    - DataFrame indexado por fecha/hora, una columna por pluviometro.
    """
    df_datos = pd.read_csv(archivo, encoding="utf-8")

    df_datos['Time'] = pd.to_datetime(df_datos['Time'], **detectar_formato_fecha(df_datos['Time']))

    df_datos = df_datos.set_index('Time').sort_index()

    # Si un mismo instante trae mas de una lectura para el mismo pluviometro se conserva la mayor.
    if df_datos.index.has_duplicates:
        df_datos = df_datos.groupby(level=0).max()

    return df_datos


def limpiar_caidas_espurias(serie):
    """
    Elimina los pozos espurios de una serie acumulada: lecturas que bajan y en la lectura
    siguiente vuelven exactamente al mismo valor previo (ej. 5.08 -> 0.00 -> 5.08).

    Son fallas de transmision, no reinicios reales del contador. Si no se limpian, la
    recuperacion posterior se cuenta como un incremento positivo y se inventa lluvia.

    Parametros:
    - serie: Serie de pandas con el acumulado crudo de un pluviometro (sin nulos).

    Retorna:
    - Serie sin las lecturas espurias.
    """
    if len(serie) < 3:
        return serie

    valores = serie.to_numpy(dtype=float)
    espuria = np.zeros(len(valores), dtype=bool)
    espuria[1:-1] = (valores[1:-1] < valores[:-2]) & (valores[2:] == valores[:-2])

    return serie[~espuria]


def dia_pluviometrico(fechas):
    """
    Asigna cada instante a su dia de medicion [HORA_CORTE, HORA_CORTE).

    Con el corte a las 07:00 el dia se etiqueta con la fecha de cierre, que es la convencion
    de la medicion de las 07:00: lo que se acumula entre las 07:00 del 31/07 y las 07:00 del
    01/08 es la lluvia del 01/08. Con HORA_CORTE = 0 el dia es el civil y se etiqueta con su
    propia fecha. En los dos casos un mes completo queda etiquetado con los dias reales de
    ese mes.

    Parametros:
    - fechas: DatetimeIndex o Serie de fechas.

    Retorna:
    - DatetimeIndex (sin hora) del dia de medicion al que pertenece cada instante.
    """
    return ((pd.DatetimeIndex(fechas) - pd.Timedelta(hours=HORA_CORTE)).normalize()
            + DESPLAZAMIENTO_DIA)


def inicio_del_dia(dias):
    """
    Devuelve el instante en que abre cada dia de medicion: la inversa de dia_pluviometrico().

    Parametros:
    - dias: DatetimeIndex o lista de dias (sin hora).

    Retorna:
    - DatetimeIndex con el instante de apertura de cada uno.
    """
    return pd.DatetimeIndex(dias) - DESPLAZAMIENTO_DIA + pd.Timedelta(hours=HORA_CORTE)


def ventana_del_mes(df_crudo):
    """
    Calcula la ventana temporal del mes contenido en los datos: desde que abre el primer dia
    del mes hasta que abre el primero del mes siguiente (extremo final excluido).

    Con el corte a las 07:00 eso va de las 07:00 del ultimo dia del mes anterior a las 07:00
    del ultimo dia del mes; con HORA_CORTE = 0 es el mes civil completo.

    El mes se deduce del dato central del archivo, para no confundirse con las horas del
    mes anterior que arrastra el propio corte.

    Parametros:
    - df_crudo: DataFrame indexado por fecha/hora.

    Retorna:
    - Tupla (inicio, fin) de Timestamps.
    """
    centro = df_crudo.index[len(df_crudo) // 2]

    primero_del_mes = pd.Timestamp(year=centro.year, month=centro.month, day=1)
    primero_del_siguiente = primero_del_mes + pd.offsets.MonthBegin(1)

    inicio, fin = inicio_del_dia([primero_del_mes, primero_del_siguiente])

    return inicio, fin


def ventana_del_archivo(df_crudo):
    """
    Calcula la ventana que cubre todas las lecturas del archivo, alineada a dias de medicion
    completos.

    La usa el analisis de tormenta, donde el recorte temporal lo elige el operario y no tiene
    por que coincidir con un mes: ahi acotar al mes detectado borraria datos en silencio.

    Parametros:
    - df_crudo: DataFrame indexado por fecha/hora.

    Retorna:
    - Tupla (inicio, fin) de Timestamps.
    """
    dias = dia_pluviometrico([df_crudo.index.min(), df_crudo.index.max()])

    inicio = inicio_del_dia(dias[:1])[0]
    fin = inicio_del_dia(dias[1:] + pd.Timedelta(days=1))[0]

    return inicio, fin


def calcular_acumulados_5min(df_crudo, inicio=None, fin=None):
    """
    Arma la tabla de acumulados por rangos de 5 minutos: una columna por pluviometro y una
    fila por rango [inicio, inicio+5min).

    El valor del CSV es un contador acumulado que el equipo reinicia a cero por su cuenta,
    asi que la lluvia de cada rango es la suma de las diferencias entre lecturas
    consecutivas dentro de ese rango, descartando las diferencias negativas (reinicios del
    contador). La cadena de diferencias se reinicia en cada dia pluviometrico, por lo que
    el primer rango de cada dia siempre vale 0.

    Parametros:
    - df_crudo: DataFrame con las lecturas crudas (salida de leer_datos_crudos).
    - inicio: Timestamp de comienzo de la ventana. Si es None se toma el del mes detectado.
    - fin: Timestamp de fin de la ventana (excluido). Si es None se toma el del mes detectado.

    Retorna:
    - DataFrame indexado por el inicio de cada rango de 5 minutos.
    """
    inicio_mes, fin_mes = ventana_del_mes(df_crudo)
    inicio = inicio_mes if inicio is None else inicio
    fin = fin_mes if fin is None else fin

    # La grilla se recorta a lo que el archivo realmente cubre, para no inventar rangos vacios.
    inicio = max(inicio, df_crudo.index.min().floor(FRECUENCIA))
    fin = min(fin, df_crudo.index.max().floor(FRECUENCIA) + pd.Timedelta(FRECUENCIA))

    grilla = pd.date_range(start=inicio, end=fin, freq=FRECUENCIA, inclusive='left')

    df_5min = pd.DataFrame(index=grilla, columns=df_crudo.columns, dtype=float)
    df_5min.index.name = 'Inicio'

    for pluvio in df_crudo.columns:
        serie = df_crudo[pluvio].dropna()
        serie = serie[(serie.index >= inicio) & (serie.index < fin)]

        if serie.empty:
            continue  # Pluviometro sin datos en la ventana: la columna queda vacia (NaN).

        serie = limpiar_caidas_espurias(serie)

        # Diferencia contra la lectura anterior del mismo dia pluviometrico.
        incrementos = serie.groupby(dia_pluviometrico(serie.index)).diff()

        # Sin lectura previa (primera del dia) no hay incremento; las bajadas son reinicios.
        incrementos = incrementos.fillna(0).clip(lower=0)

        # Todas las lecturas de un mismo rango de 5 minutos suman al acumulado de ese rango.
        por_rango = incrementos.groupby(incrementos.index.floor(FRECUENCIA)).sum()

        df_5min[pluvio] = por_rango.reindex(grilla, fill_value=0.0)

    return df_5min.round(2)


def descartar_outliers(df_5min, umbral=UMBRAL_OUTLIER_5MIN):
    """
    Descarta los rangos de 5 minutos cuya lluvia supere el umbral de intensidad admisible.

    Un valor asi no es lluvia sino una falla del equipo: un salto del contador por reinicio o
    por una lectura corrupta. Los rangos descartados quedan en blanco y no como cero, porque no
    se sabe cuanto llovio realmente en ese rato; ponerlos en cero afirmaria que no llovio.

    Los descartes se devuelven aparte para poder mostrarle al operario que se saco y de donde,
    en vez de borrar mediciones en silencio.

    Parametros:
    - df_5min: DataFrame de acumulados cada 5 minutos.
    - umbral: Lluvia maxima admisible en un rango, en mm.

    Retorna:
    - Tupla (df_filtrado, df_descartes), donde df_descartes tiene una fila por rango descartado
      con su pluviometro, su fecha/hora y el valor que se quito.
    """
    fuera_de_rango = df_5min > umbral

    descartes = [{'Pluviometro': pluvio, 'Fecha y hora': marca, 'Valor descartado (mm)': valor}
                 for pluvio in df_5min.columns
                 for marca, valor in df_5min[pluvio][fuera_de_rango[pluvio]].items()]

    df_descartes = pd.DataFrame(descartes,
                                columns=['Pluviometro', 'Fecha y hora', 'Valor descartado (mm)'])

    return df_5min.mask(fuera_de_rango), df_descartes.sort_values('Fecha y hora')


def calcular_acumulados_diarios_corte(df_5min):
    """
    Suma los rangos de 5 minutos por dia pluviometrico [07:00, 07:00).

    Parametros:
    - df_5min: DataFrame de acumulados cada 5 minutos (salida de calcular_acumulados_5min).

    Retorna:
    - DataFrame con una fila por dia y una columna por pluviometro.
    """
    dias = dia_pluviometrico(df_5min.index)

    # min_count=1 mantiene en NaN a los pluviometros sin datos en lugar de mostrarlos en 0.
    df_diario = df_5min.groupby(dias).sum(min_count=1)
    df_diario.index.name = 'Dia'

    return df_diario.round(2)


def resumen_control(df_5min, df_diario, df_descartes=None):
    """
    Arma la tabla de control que revisa el operario antes de exportar.

    Se cruzan dos controles independientes, porque detectan fallas distintas:

    - El total del mes contra la mediana de la red. Si llovio sobre Montevideo todos los
      equipos tienen que haber medido algo del mismo orden; el que quedo muy por debajo suele
      estar tapado o sin bascular.
    - La correlacion de la serie diaria contra el dia tipico de la red. Detecta al equipo que
      mide cantidades razonables pero en los dias equivocados, por reloj desfasado o por
      reinicios que le hacen recontar la lluvia. Ese caso el total solo no lo ve.

    Parametros:
    - df_5min: DataFrame de acumulados cada 5 minutos, ya filtrado.
    - df_diario: DataFrame de acumulados diarios.
    - df_descartes: DataFrame de rangos descartados por outlier (salida de descartar_outliers).

    Retorna:
    - DataFrame con una fila por pluviometro y las columnas de control.
    """
    totales = df_diario.sum(min_count=1)
    mediana = totales.median()

    # Dia tipico de la red: mediana entre pluviometros, robusta a los equipos fallados.
    correlaciones = df_diario.corrwith(df_diario.median(axis=1))

    if df_descartes is None or df_descartes.empty:
        descartes_por_pluvio = {}
    else:
        descartes_por_pluvio = df_descartes['Pluviometro'].value_counts().to_dict()

    filas = []
    for pluvio in df_diario.columns:
        total = totales[pluvio]
        correlacion = correlaciones[pluvio]
        lecturas = int(df_5min[pluvio].notna().sum())
        descartados = descartes_por_pluvio.get(pluvio, 0)

        if lecturas == 0 or pd.isna(total):
            estado = 'SIN DATOS'
        elif mediana > 0 and total < UMBRAL_BAJO * mediana:
            estado = 'BAJO - revisar'
        elif pd.notna(correlacion) and correlacion < UMBRAL_CORRELACION:
            estado = 'DESFASADO - revisar'
        elif mediana > 0 and total > UMBRAL_ALTO * mediana:
            estado = 'ALTO - revisar'
        elif descartados:
            # Mide bien en general, pero tuvo lecturas imposibles que hubo que tirar.
            estado = 'CON DESCARTES - revisar'
        else:
            estado = 'OK'

        filas.append({
            'Pluviometro': pluvio,
            'Total mes (mm)': round(total, 2) if pd.notna(total) else 0.0,
            'Dias con lluvia': int((df_diario[pluvio] > 0).sum()),
            'Max diario (mm)': round(df_diario[pluvio].max(), 2) if pd.notna(total) else 0.0,
            'Max 5 min (mm)': round(df_5min[pluvio].max(), 2) if pd.notna(total) else 0.0,
            'Correl. red': round(correlacion, 3) if pd.notna(correlacion) else 0.0,
            'Descartados': descartados,
            'Estado': estado,
        })

    return pd.DataFrame(filas)


def graficar_totales_mes(df_resumen):
    """
    Grafica el total del mes de cada pluviometro contra la mediana de la red.

    Es el control visual mas rapido: las barras deberian quedar todas alrededor de la linea
    de la mediana. La que se despega marca un equipo a revisar.

    Parametros:
    - df_resumen: DataFrame de control (salida de resumen_control).

    Retorna:
    - Figura de matplotlib.
    """
    orden = df_resumen.sort_values('Total mes (mm)')
    totales = orden['Total mes (mm)']
    mediana = totales.median()

    fig, ax = plt.subplots(figsize=(12, 8))

    colores = ['tab:blue' if estado == 'OK' else 'tab:red' for estado in orden['Estado']]
    ax.barh(orden['Pluviometro'], totales.values, color=colores, alpha=0.85)

    ax.axvline(mediana, color='green', linestyle='--', linewidth=2, label=f'Mediana de la red ({mediana:.1f} mm)')

    for i, valor in enumerate(totales.values):
        ax.text(valor, i, f' {valor:.1f}', va='center', fontsize=10)

    ax.set_xlabel('Acumulado del mes (mm)', fontsize=14)
    ax.set_title('Total del mes por pluviometro (rojo = fuera de rango)', fontsize=16)
    ax.grid(True, axis='x', linestyle='--', linewidth=0.5)
    ax.legend(fontsize=12)

    plt.tight_layout()

    return fig


def graficar_diario_por_pluviometro(df_diario):
    """
    Grafica la serie de acumulados diarios de cada pluviometro.

    Sirve para ver si los equipos llovieron los mismos dias: una curva corrida respecto del
    resto delata un problema de reloj o de reinicio del equipo.

    Parametros:
    - df_diario: DataFrame de acumulados diarios.

    Retorna:
    - Figura de matplotlib.
    """
    fig, ax = plt.subplots(figsize=(12, 8))

    for columna in df_diario.columns:
        ax.plot(df_diario.index, df_diario[columna], marker='o', markersize=3, label=columna)

    ax.set_xlabel('Dia pluviometrico (cierre 07:00)', fontsize=14)
    ax.set_ylabel('Acumulado del dia (mm)', fontsize=14)
    ax.set_title('Acumulado diario por pluviometro', fontsize=16)

    ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%m'))

    ax.grid(True, linestyle='--', linewidth=0.5)
    ax.legend(title='', loc='upper left', bbox_to_anchor=(1, 1), fontsize=10)

    plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
    plt.tight_layout()

    return fig


def graficar_intensidad_dia(df_5min, dia):
    """
    Grafica la lluvia cada 5 minutos de un dia pluviometrico y su curva acumulada.

    Es el control fino: los pluviometros de una misma tormenta tienen que mostrar los picos
    a la misma hora. Un salto vertical aislado en una sola curva es un dato malo, no lluvia.

    Parametros:
    - df_5min: DataFrame de acumulados cada 5 minutos.
    - dia: Timestamp del dia pluviometrico a graficar.

    Retorna:
    - Figura de matplotlib.
    """
    del_dia = df_5min[dia_pluviometrico(df_5min.index) == pd.Timestamp(dia)]

    fig, (ax_barras, ax_acum) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    for columna in del_dia.columns:
        ax_barras.plot(del_dia.index, del_dia[columna], linewidth=1, label=columna)
        # fillna antes del acumulado: un rango descartado cortaria la curva de ahi en adelante.
        ax_acum.plot(del_dia.index, del_dia[columna].fillna(0).cumsum(), linewidth=1.5, label=columna)

    ax_barras.set_ylabel('Lluvia cada 5 min (mm)', fontsize=12)
    ax_barras.set_title(f'Detalle del dia {pd.Timestamp(dia).strftime("%d-%m-%Y")} (07:00 del dia anterior a 07:00)', fontsize=15)
    ax_barras.grid(True, linestyle='--', linewidth=0.5)

    ax_acum.set_ylabel('Acumulado del dia (mm)', fontsize=12)
    ax_acum.set_xlabel('Hora', fontsize=12)
    ax_acum.grid(True, linestyle='--', linewidth=0.5)
    ax_acum.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

    ax_acum.legend(title='', loc='upper left', bbox_to_anchor=(1, 1), fontsize=9)

    plt.tight_layout()

    return fig


def escribir_csvs(df_5min, df_diario, carpeta_destino):
    """
    Escribe en disco los dos CSV refinados ya calculados.

    Parametros:
    - df_5min: DataFrame de acumulados cada 5 minutos.
    - df_diario: DataFrame de acumulados diarios.
    - carpeta_destino: Carpeta donde se escriben los archivos.

    Retorna:
    - Tupla (ruta_5min, ruta_diario) con las rutas de los archivos generados.
    """
    sufijo = df_5min.index.max().strftime('%Y-%m')

    ruta_5min = os.path.join(carpeta_destino, f'Acumulados cada 5min {sufijo}.csv')
    ruta_diario = os.path.join(carpeta_destino, f'Acumulado diario {sufijo}.csv')

    salida_5min = df_5min.copy()
    salida_5min.insert(0, 'Fin', (salida_5min.index + pd.Timedelta(FRECUENCIA)).strftime('%d-%m-%Y %H:%M:%S'))
    salida_5min.insert(1, 'Dia', dia_pluviometrico(salida_5min.index).strftime('%d-%m-%Y'))
    salida_5min.index = salida_5min.index.strftime('%d-%m-%Y %H:%M:%S')

    salida_diario = df_diario.copy()
    salida_diario.index = salida_diario.index.strftime('%d-%m-%Y')

    # utf-8-sig para que Excel respete los acentos de los nombres de los pluviometros.
    salida_5min.to_csv(ruta_5min, encoding='utf-8-sig')
    salida_diario.to_csv(ruta_diario, encoding='utf-8-sig')

    return ruta_5min, ruta_diario


def exportar_csvs(archivo, carpeta_destino):
    """
    Genera los dos CSV refinados a partir del CSV crudo de Grafana, en un solo paso.

    Parametros:
    - archivo: Ruta del CSV exportado de Grafana.
    - carpeta_destino: Carpeta donde se escriben los archivos.

    Retorna:
    - Tupla (ruta_5min, ruta_diario) con las rutas de los archivos generados.
    """
    df_5min, df_diario, _ = calcular_tablas_refinadas(archivo)

    return escribir_csvs(df_5min, df_diario, carpeta_destino)


def calcular_tablas_refinadas(archivo, mensual=True):
    """
    Hace todo el procesamiento del CSV crudo: acumulados cada 5 minutos, descarte de outliers
    y acumulados diarios.

    Es el unico camino por el que se calcula lluvia en todo el proyecto. La app, la exportacion
    de CSV y el informe entran todos por aca, para que ninguno pueda dar un numero distinto de
    los otros sobre el mismo archivo.

    Parametros:
    - archivo: Ruta del CSV exportado de Grafana.
    - mensual: True acota al mes detectado; False procesa el archivo entero.

    Retorna:
    - Tupla (df_5min, df_diario, df_descartes).
    """
    return refinar_crudo(leer_datos_crudos(archivo), mensual)


def refinar_crudo(df_crudo, mensual=True):
    """
    Igual que calcular_tablas_refinadas() pero sobre un crudo ya leido.

    La usa el informe, que necesita el crudo aparte para medir la cobertura y no tiene por que
    volver a leer el archivo ni repetir los pasos del calculo.

    Parametros:
    - df_crudo: DataFrame con las lecturas crudas (salida de leer_datos_crudos).
    - mensual: True acota al mes detectado; False procesa el crudo entero.

    Retorna:
    - Tupla (df_5min, df_diario, df_descartes).
    """
    inicio, fin = ventana_del_mes(df_crudo) if mensual else ventana_del_archivo(df_crudo)

    df_5min, df_descartes = descartar_outliers(calcular_acumulados_5min(df_crudo, inicio, fin))

    df_diario = calcular_acumulados_diarios_corte(df_5min)

    return df_5min, df_diario, df_descartes


def preparar_series(archivo, mensual=True):
    """
    Punto de entrada de la interfaz: del CSV crudo salen todas las series que consume la app.

    Se devuelven dos cosas distintas y no hay que confundirlas:

    - df_contador es el contador acumulado del equipo en grilla de 5 minutos, con sus huecos.
      Sirve solo para los controles de estructura (que pluviometros tienen datos, porcentaje
      de nulos, saltos temporales). Nunca se usa para calcular lluvia.
    - df_5min y df_diario son la lluvia, calculada por calcular_tablas_refinadas().

    Parametros:
    - archivo: Ruta del CSV exportado de Grafana.
    - mensual: True acota al mes detectado; False procesa todo el archivo (analisis de
      tormenta, donde el recorte lo elige despues el operario).

    Retorna:
    - Tupla (df_contador, df_5min, df_diario, df_descartes).
    """
    df_contador = leer_archivo_principal(archivo)

    df_5min, df_diario, df_descartes = calcular_tablas_refinadas(archivo, mensual)

    return df_contador, df_5min, df_diario, df_descartes
