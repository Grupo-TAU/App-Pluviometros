from Codigo.Instalador.Funciones_basicas import *

def limitar_df_temporal(df, limite_inf, limite_sup):
    """
    Limita el DataFrame a un rango de fechas determinado por los índices.
    
    Parámetros:
    - df: DataFrame con datos temporales indexados.
    - limite_inf: Fecha de inicio del rango.
    - limite_sup: Fecha de fin del rango.
    
    Retorna:
    - DataFrame filtrado dentro del rango temporal especificado.
    """
    return df[(df.index >= limite_inf) & (df.index <= limite_sup)]

def calcular_porcentaje_vacios(df_datos, df_config):
    """
    Calcula el porcentaje de valores nulos en cada columna del DataFrame, excluyendo la primera y última fila.
    
    Parámetros:
    - df_datos: DataFrame con los datos de precipitación por pluviómetro.
    - df_config: DataFrame con la configuración de los pluviómetros para traducir los ID.
    
    Retorna:
    - DataFrame con el porcentaje de valores nulos por pluviómetro y su respectivo nombre.
    """
    df_datos_sin_extremos = df_datos.iloc[1:-1] 
    
    porcentaje_vacios = (df_datos_sin_extremos.isna().sum() / len(df_datos_sin_extremos)) * 100
    
    lugares_nulos = [traducir_id_a_lugar(df_config, id_pluvio) for id_pluvio in porcentaje_vacios.index]
    
    df_nulos = pd.DataFrame({
        'Pluviómetro': lugares_nulos,
        'Porcentaje_Nulos': porcentaje_vacios.values
    })
    
    return df_nulos

def detectar_saltos_temporales(df_datos, df_config, intervalo=5):
    """
    Detecta intervalos de saltos temporales, donde hay valores faltantes (NaN) durante un tiempo prolongado.
    
    Parámetros:
    - df_datos: DataFrame con los datos de precipitación por pluviómetro.
    - df_config: DataFrame con la configuración de los pluviómetros para traducir los ID.
    - intervalo: Duración mínima en minutos para considerar un salto (por defecto 5 minutos).
    
    Retorna:
    - df_saltos_maximos: DataFrame con información sobre el salto más largo para cada pluviómetro.
    - df_saltos: DataFrame con los detalles de cada salto temporal detectado.
    """
    df_saltos_maximos = pd.DataFrame(columns=['Pluviómetro', 'Cantidad de saltos', 'Duración total (min)', 'Duración máx (min)', 'Inicio máx', 'Fin máx'])
    
    df_saltos = pd.DataFrame(columns=['Pluviómetro', 'Duración (min)', 'Inicio', 'Fin'])
    
    # Iterar por cada columna (pluviómetro)
    for pluvio in df_datos.columns:
        # Excluir la primera y última fila
        df_datos_sin_extremos = df_datos[pluvio].iloc[1:-1] 
        
        # Detectar intervalos nulos consecutivos
        nulos = df_datos_sin_extremos.isna()
        
        # Calcular diferencias temporales
        cambios = nulos.astype(int).diff().fillna(0)
        
        # Detectar inicio y fin de intervalos nulos
        inicio_saltos = df_datos_sin_extremos.index[cambios == 1]
        fin_saltos = df_datos_sin_extremos.index[cambios == -1]
        
        # Si el intervalo empieza con nulos
        if nulos.iloc[0]:
            inicio_saltos = pd.Index([df_datos_sin_extremos.index[0]]).append(inicio_saltos)
        
        # Si termina con nulos
        if nulos.iloc[-1]:
            fin_saltos = fin_saltos.append(pd.Index([df_datos_sin_extremos.index[-1]]))
        
        # Calcular duración de los saltos
        duraciones = (fin_saltos - inicio_saltos).total_seconds() / 60  # minutos
        
        # Filtrar los saltos que cumplen con el intervalo mínimo y convertir a Series numérica
        saltos_detectados = pd.Series(duraciones[duraciones >= intervalo])
        
        # Si no hay saltos, continuar con el siguiente pluviómetro
        if saltos_detectados.empty:
            continue
        
        for i, duracion in saltos_detectados.items():
            df_saltos = pd.concat([df_saltos, pd.DataFrame({
                'Pluviómetro': [traducir_id_a_lugar(df_config, pluvio)],
                'Duración (min)': [duracion],
                'Inicio': [inicio_saltos[i]],
                'Fin': [fin_saltos[i]]
            })], ignore_index=True)
        
        # Acumular la duración de todos los saltos
        duracion_total = saltos_detectados.sum()
        
        # Encontrar el salto más largo
        duracion_max = saltos_detectados.max()
        max_index = saltos_detectados.idxmax()
        
        df_saltos_maximos = pd.concat([df_saltos_maximos, pd.DataFrame({
            'Pluviómetro': [traducir_id_a_lugar(df_config, pluvio)],
            'Cantidad de saltos': [len(saltos_detectados)],
            'Duración total (min)': [duracion_total],
            'Duración máx (min)': [duracion_max],
            'Inicio máx': [inicio_saltos[max_index]],
            'Fin máx': [fin_saltos[max_index]],
        })], ignore_index=True)
    
    return df_saltos_maximos, df_saltos

def graficar_lluvia_con_saltos_tormenta(df_lluvia_instantanea, df_saltos, df_saltos_maximos, pluvio_seleccionado, df_config, ver_todos):
    """
    Grafica la lluvia instantánea con las franjas de saltos temporales indicadas en rojo y el salto más grande en azul.
    
    Parámetros:
    - df_lluvia_instantanea: DataFrame con los datos de lluvia instantánea.
    - df_saltos: DataFrame con los detalles de los saltos temporales detectados.
    - df_saltos_maximos: DataFrame con el salto más largo por pluviómetro.
    - pluvio_seleccionado: Nombre del pluviómetro a graficar.
    - df_config: DataFrame con la configuración de los pluviómetros para traducir los ID.
    - ver_todos: Booleano para decidir si graficar todos los pluviómetros o solo el seleccionado.
    
    Retorna:
    - Figura con la gráfica de lluvia instantánea y saltos temporales.
    """    
    if ver_todos:
        fig = graficar_lluvia_instantanea_tormenta(df_lluvia_instantanea)
    else:
        pluvio_seleccionado_ID = traducir_lugar_a_id(df_config, pluvio_seleccionado)
        fig = graficar_lluvia_instantanea_tormenta(df_lluvia_instantanea[[pluvio_seleccionado_ID]])
    
    ax = fig.gca()  
    
    # Filtrar los saltos para el pluviómetro seleccionado
    saltos_pluvio = df_saltos[df_saltos['Pluviómetro'] == pluvio_seleccionado]
    salto_max_pluvio = df_saltos_maximos[df_saltos_maximos['Pluviómetro'] == pluvio_seleccionado]
    
    # Graficar todas las franjas de saltos
    if not saltos_pluvio.empty:
        for _, row in saltos_pluvio.iterrows():
            ax.axvspan(row['Inicio'], row['Fin'], color='red', alpha=0.3, label='Saltos')
    
    # Graficar el salto más grande en otro color
    if not salto_max_pluvio.empty:
        ax.axvspan(
            salto_max_pluvio['Inicio máx'].values[0],
            salto_max_pluvio['Fin máx'].values[0],
            color='blue',
            alpha=0.3,
            label='Salto+largo'
        )
    
    # Evitar etiquetas duplicadas en la leyenda
    handles, labels = ax.get_legend_handles_labels()
    unique_labels = dict(zip(labels, handles))
    ax.legend(unique_labels.values(), unique_labels.keys(), title='', loc='upper left', bbox_to_anchor=(1, 1), fontsize=12)
    
    return fig

def graficar_lluvia_instantanea_tormenta(df_lluvia_instantanea, intervalo_minutos=30): 
    """
    Grafica las precipitaciones instantáneas de los pluviómetros durante una tormenta.
    
    Parámetros:
    - df_lluvia_instantanea: DataFrame con las precipitaciones instantáneas por pluviómetro.
    - intervalo_minutos: Intervalo de tiempo entre marcas en el eje X (en minutos).
    
    Retorna:
    - Figura con la gráfica de las precipitaciones instantáneas.
    """  
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Graficar cada pluviómetro
    for columna in df_lluvia_instantanea.columns:
        plt.plot(df_lluvia_instantanea.index, df_lluvia_instantanea[columna], label=columna)

    plt.xlabel('Evolución temporal (dd:mm:yy)', fontsize=14)
    plt.ylabel('Precipitación instantáneas (en intervalos de 5 minutos)', fontsize=14)
    plt.title('Grafico precipitaciones instantaneas', fontsize=16)
    
    ax = plt.gca()
    ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=intervalo_minutos))  
    ax.xaxis.set_major_formatter(DateFormatter('%y/%m/%d %H:%M'))    
    
    inicio = np.datetime64(df_lluvia_instantanea.index.min(), 'h')  
    fin = np.datetime64(df_lluvia_instantanea.index.max(), 'm') + np.timedelta64(30 - df_lluvia_instantanea.index.max().minute % intervalo_minutos, 'm')

    ax.set_xlim([inicio, fin])
    
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    
    plt.xticks(rotation=90, fontsize=12)
    plt.yticks(fontsize=12)
    
    plt.legend(title='', loc='upper left', bbox_to_anchor=(1, 1), fontsize=12)
    plt.tight_layout()

    return fig

def graficar_lluvia_acumulado_tormenta(df_lluvia_acumulada, intervalo_minutos=30):
    """
    Grafica las precipitaciones acumuladas de los pluviómetros durante una tormenta.
    
    Parámetros:
    - df_lluvia_acumulada: DataFrame con las precipitaciones acumuladas por pluviómetro.
    - intervalo_minutos: Intervalo de tiempo entre marcas en el eje X (en minutos).

    
    Retorna:
    - Figura con la gráfica de las precipitaciones acumuladas.
    """
    fig, ax = plt.subplots(figsize=(12, 8))
    
    for columna in df_lluvia_acumulada.columns:
        plt.plot(df_lluvia_acumulada.index, df_lluvia_acumulada[columna], label=columna)

    plt.xlabel('Evolución temporal (dd:mm:yy)', fontsize=14)
    plt.ylabel('Precipitación instantáneas (en intervalos de 5 minutos)', fontsize=14)
    plt.title('Grafico acumulado precipitaciones', fontsize=16)
    
    ax = plt.gca()
    ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=intervalo_minutos))
    ax.xaxis.set_major_formatter(DateFormatter('%y/%m/%d %H:%M'))   
    
    inicio = np.datetime64(df_lluvia_acumulada.index.min(), 'h')  
    fin = np.datetime64(df_lluvia_acumulada.index.max(), 'm') + np.timedelta64(30 - df_lluvia_acumulada.index.max().minute % intervalo_minutos, 'm')

    ax.set_xlim([inicio, fin])
    
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    
    plt.xticks(rotation=90, fontsize=12)
    plt.yticks(fontsize=12)
    
    plt.legend(title='', loc='upper left', bbox_to_anchor=(1, 1), fontsize=12)
    plt.tight_layout()

    return fig

def max_suma_ventana_df(df, ventana):
    """
    Calcula el valor máximo de la suma de precipitaciones dentro de una ventana de tiempo.
    
    Parámetros:
    - df: DataFrame con las precipitaciones por pluviómetro.
    - ventana: Duración de la ventana en minutos.
    
    Retorna:
    - max_valor: El valor máximo de la suma de precipitaciones en la ventana.
    - pluvio_maximo: El nombre del pluviómetro que tiene el máximo valor de precipitación en la ventana.
    """
    # Convertir la ventana a intervalos (cada 5 minutos)
    intervalos = ventana // 5
    
    maximos_por_pluvio = {}

    # Calcular el máximo para cada pluviómetro (columna)
    for columna in df.columns:
        precipitaciones = df[columna].dropna().tolist()
        sumas_ventana = [sum(precipitaciones[i:i + intervalos]) 
                         for i in range(len(precipitaciones) - intervalos + 1)]
        
        maximos_por_pluvio[columna] = max(sumas_ventana) if sumas_ventana else sum(precipitaciones)

    # Identificar el nombre del pluviómetro y su máximo
    pluvio_maximo = max(maximos_por_pluvio, key=maximos_por_pluvio.get)
    max_valor = maximos_por_pluvio[pluvio_maximo]
    
    return max_valor, pluvio_maximo

def calcular_precipitacion_para_tr(df):
    """
    Calcula las precipitaciones máximas para diferentes duraciones de tormenta.
    
    Parámetros:
    - df: DataFrame con las precipitaciones por pluviómetro.
    
    Retorna:
    - precipitaciones: Lista con las precipitaciones máximas para cada duración de tormenta.
    """
    precipitaciones = []

    for ventana in duracion_tormenta:
        # Calcular el máximo usando la función de suma de ventana
        max_valor, pluvio_maximo = max_suma_ventana_df(df, ventana)
               
        precipitaciones.append((ventana, max_valor, pluvio_maximo))

    return precipitaciones

def calcular_precipitacion_pluvio(df, pluvio):
    """
    Calcula las precipitaciones máximas para un pluviómetro específico.
    
    Parámetros:
    - df: DataFrame con las precipitaciones por pluviómetro.
    - pluvio: Nombre del pluviómetro.
    
    Retorna:
    - precipitaciones: Lista con las precipitaciones máximas para cada duración de tormenta.
    """
    df_pluvio = df[[pluvio]]  
    return calcular_precipitacion_para_tr(df_pluvio)

def grafica_tr(lista_tr, precipitaciones, limite_precipitacion, limite_tiempo, etiqueta, titulo, figsize=(8,4)):
    """
    Grafica las precipitaciones máximas en función de la duración de la tormenta.
    
    Parámetros:
    - lista_tr: Lista binaria que indica cuáles tormentas incluir en la gráfica.
    - precipitaciones: Diccionario con las precipitaciones por tormenta.
    - limite_precipitacion: Límite superior para la precipitación en el eje Y.
    - limite_tiempo: Límite superior para la duración de la tormenta en el eje X.
    - etiqueta: Etiqueta para los puntos de precipitación.
    - titulo: Título de la gráfica.
    
    Retorna:
    - Figura con la gráfica de precipitaciones por duración de tormenta.
    """
    fig, ax = plt.subplots(figsize=figsize)

    tr_names = list(precipitacion_tr.keys())
    
    for i, tr in enumerate(tr_names):
        if lista_tr[i] == 1:  
            ax.plot(duracion_tormenta, precipitacion_tr[tr], label=tr, linestyle='-', linewidth=1.5)
    
    if precipitaciones is not None:
        ax.scatter(duracion_tormenta, precipitaciones, label=etiqueta, color='red', marker='o', facecolors="none", linewidth=1.5)
        
    ax.set_title(titulo, fontsize=16)
    ax.set_xlabel('Minutos de Duración de la Tormenta', fontsize=14)
    ax.set_ylabel('Precipitación (mm)', fontsize=14)
    
    plt.xticks(fontsize=12)
    plt.yticks(fontsize=12)
    
    ax.legend(loc="upper left", fontsize=12)
    ax.set_ylim(0, limite_precipitacion)
    ax.set_xlim(0, limite_tiempo)
    ax.grid(True)
    fig.tight_layout(pad=2.0)
    
    return fig

