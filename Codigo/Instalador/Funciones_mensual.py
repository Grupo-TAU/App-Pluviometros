from Codigo.Instalador.Funciones_basicas import *

# Establecer la localización en español. El nombre del locale cambia según la máquina, así que
# se prueban las variantes habituales: si ninguna existe se sigue con el locale por defecto, ya
# que los nombres de meses del informe salen de numero_a_mes() y no de strftime.
for _nombre_locale in ('es_ES.UTF-8', 'es_ES', 'Spanish_Spain.1252', 'es-ES'):
    try:
        locale.setlocale(locale.LC_TIME, _nombre_locale)
        break
    except locale.Error:
        continue

lluvia_historico = {
    1: [38.75, 71.50, 120.00, 448.00],
    2: [45.50, 80.50, 120.55, 276.00],
    3: [47.00, 84.40, 133.95, 450.30],
    4: [42.75, 74.20, 141.50, 499.00],
    5: [39.43, 78.00, 140.75, 320.00],
    6: [43.75, 80.60, 127.00, 347.00],
    7: [45.00, 65.00, 105.73, 243.00],
    8: [38.25, 72.00, 113.25, 360.00],
    9: [47.75, 77.00, 128.25, 295.00],
    10: [46.45, 71.00, 120.98, 265.00],
    11: [43.53, 76.25, 118.50, 251.00],
    12: [47.50, 64.50, 105.15, 286.00]
}

def valor_lluvias_historicas(mes):
    """
    Retorna el valor de precipitaciones históricas para un mes específico.
    
    Parámetros:
    - mes: Número del mes (1-12).

    Retorna:
    - Valor de precipitaciones históricas si el mes es válido, de lo contrario un mensaje de error.
    """
    if mes in lluvia_historico:
        return lluvia_historico[mes] 
    else:
        return f"Mes {mes} no válido"

def obtener_mes(df_acumulados_diarios):
    """
    Obtiene el mes correspondiente a la fecha central del DataFrame.
    
    Parámetros:
    - df_acumulados_diarios: DataFrame con datos de precipitaciones diarias.

    Retorna:
    - Número de mes (1-12) correspondiente al valor central del índice temporal.
    """
    if not pd.api.types.is_datetime64_any_dtype(df_acumulados_diarios.index):
        df_acumulados_diarios.index = pd.to_datetime(df_acumulados_diarios.index, errors='coerce')

    # Obtener el valor central (aproximado)
    valor_central = df_acumulados_diarios.index[len(df_acumulados_diarios) // 2]

    mes = valor_central.month

    return mes

def numero_a_mes(numero_mes):
    """
    Convierte un número de mes en su nombre en español.
    
    Parámetros:
    - numero_mes: Número del mes (1-12).

    Retorna:
    - Nombre del mes en español.
    """
    meses_es = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]
    if 1 <= numero_mes <= 12:
        return meses_es[numero_mes - 1]
    else:
        raise ValueError("El número debe estar entre 1 y 12.")

def graficar_acumulados_barras(df_acumulados_diarios):
    """
    Genera un gráfico de barras con los acumulados totales de precipitación por pluviómetro.
    
    Parámetros:
    - df_acumulados_diarios: DataFrame con los acumulados diarios de precipitaciones.

    Retorna:
    - Figura de matplotlib con el gráfico de barras.
    """
   
    mes = obtener_mes(df_acumulados_diarios)
    
    df_acumulado_total = df_acumulados_diarios.sum()
    mes_lluvia_historica = valor_lluvias_historicas(mes)
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Graficar cada pluviómetro
    ax.bar(df_acumulado_total.index, df_acumulado_total.values, color='blue', label="Pluviómetros", alpha=0.8)     

    ax.set_xlabel('Pluviómetro', fontsize=14)
    
    ax.set_ylabel('Acumulado total (mm)', fontsize=14)
    ax.set_title('Acumulado Total de Precipitación por Pluviómetro', fontsize=16)
    
    plt.xticks(rotation=45, ha='right', fontsize=12)
    plt.yticks(fontsize=12)
    
    plt.grid(True, axis='both', linestyle='--', linewidth=0.5)
    
    colores_percentiles = ['red', 'green', 'orange', 'purple']
    labels_percentiles = ["Primer cuartil", "Mediana", "Tercer cuartil", "Maximo"]  # Lista para los labels de la leyenda
    for i, valor in enumerate(mes_lluvia_historica):
        # Dibujar la línea horizontal para cada percentil
        ax.axhline(y=valor, color=colores_percentiles[i], linestyle='--', linewidth=2, label=f'{labels_percentiles[i]}')
    
    ax.legend(title='', loc='upper left', bbox_to_anchor=(1, 1), fontsize=12)
    
    plt.tight_layout()

    return fig

def graficar_acumulados_diarios(df_acumulados_diarios):
    """
    Genera un gráfico de líneas con los acumulados diarios de precipitación por pluviómetro.
    
    Parámetros:
    - df_acumulados_diarios: DataFrame con acumulados diarios de precipitaciones.

    Retorna:
    - Figura de matplotlib con el gráfico de acumulados diarios.
    """
    df_acumulados_diarios = df_acumulados_diarios.copy()
    df_acumulados_diarios.index = pd.to_datetime(df_acumulados_diarios.index)
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Graficar cada pluviómetro con los acumulados diarios
    for columna in df_acumulados_diarios.columns:
        plt.plot(df_acumulados_diarios.index, df_acumulados_diarios[columna], label=columna)

    plt.xlabel('Día', fontsize=14)
    plt.ylabel('Acumulado de precipitación (mm)', fontsize=14)
    plt.title('Acumulado diario de precipitación por pluviómetro', fontsize=16)
    
    # Configurar el formato del eje X para mostrar más días
    ax = plt.gca()
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))  # Intervalo de 1 día
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))  # Formato: Mes abreviado y día
    
    # Ajustar límites del eje X según los días
    ax.set_xlim([df_acumulados_diarios.index.min(), df_acumulados_diarios.index.max()])
    
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    
    plt.xticks(rotation=45, ha='right', fontsize=12)
    plt.yticks(fontsize=12)
    
    ax.legend(title='', loc='upper left', bbox_to_anchor=(1, 1), fontsize=12)
    
    plt.tight_layout()
    
    return fig

def eliminar_filas_zeros_na(df):
    """
    Elimina las filas donde todos los valores sean NaN o 0.
    
    Parámetros:
    - df: DataFrame con los datos a limpiar.
    
    Retorna:
    - DataFrame limpio, sin filas con todos los valores NaN o 0.
    """
    # Eliminar filas donde todos los valores sean NaN o 0
    df_cleaned = df[(df != 0).any(axis=1)]  
    df_cleaned = df_cleaned.dropna(how='all')  

    return df_cleaned

def tabla_correlacion(df_acumulados_diarios):  
    """
    Calcula la matriz de correlación entre las columnas de precipitación acumulada.
    
    Parámetros:
    - df_acumulados_diarios: DataFrame con las precipitaciones diarias acumuladas por pluviómetro.
    
    Retorna:
    - DataFrame con la matriz de correlación redondeada a 2 decimales y con NaN reemplazados por cadenas vacías.
    """
    df_correlacion = eliminar_filas_zeros_na(df_acumulados_diarios)

    # Calcula la correlación entre las columnas
    df_correlacion = df_correlacion.corr()

    # Mantener solo la parte superior de la matriz
    mask = np.triu(np.ones(df_correlacion.shape, dtype=bool), k=0)
    df_correlacion = df_correlacion.where(mask)

    df_correlacion = df_correlacion.round(2)

    # Reemplazar NaN con cadenas vacías ("")
    df_correlacion = df_correlacion.astype(str).replace("nan", "")

    return df_correlacion

def grafica_lluvias_respecto_inumet(df_acumulados_diarios):
    """
    Grafica la relación entre la precipitación acumulada por pluviómetro y los datos de INUMET.
    
    Parámetros:
    - df_acumulados_diarios: DataFrame con las precipitaciones diarias acumuladas por pluviómetro y datos de INUMET.
    
    Retorna:
    - Figura con la gráfica de la relación de precipitaciones.
    """
    # Eliminar filas donde todos los valores sean NaN o 0
    df_acumulados_diarios = eliminar_filas_zeros_na(df_acumulados_diarios)
    
    # Ordenar cada columna de menor a mayor
    df_acumulados_diarios = df_acumulados_diarios.apply(lambda col: col.sort_values().reset_index(drop=True))
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    for columna in df_acumulados_diarios.columns:
        if columna != 'INUMET':  # Asegurarse de graficar la columna 'INUMET' por otro lado
            plt.plot(df_acumulados_diarios['INUMET'], df_acumulados_diarios[columna], label=columna)
        else:
            plt.plot(df_acumulados_diarios['INUMET'], df_acumulados_diarios[columna], label=columna, linestyle="--", linewidth=2, color="red")
                    
    plt.xlabel('INUMET (mm)', fontsize=14)  # Eje X: valores de precipitación INUMET
    plt.ylabel('Precipitación (mm) por Pluviómetro', fontsize=14)  # Eje Y: valores de precipitación para cada pluviómetro
    plt.title('Relación de precipitación por pluviómetro respecto a INUMET', fontsize=16)
    
    plt.yticks(fontsize=12)
    plt.xticks(fontsize=12)
    
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    
    ax.legend(title='', loc='upper left', bbox_to_anchor=(1, 1), fontsize=12)
    
    plt.tight_layout()
        
    return fig

def cortar_datos_mes_real(mes, df):
    """
    Filtra el DataFrame para obtener solo los datos del mes indicado.

    :param mes: Número del mes (1-12) que se desea filtrar.
    :param df: DataFrame con índice de tipo datetime.
    :return: DataFrame filtrado con solo los datos del mes especificado.
    """
    df_filtrado = df[df.index.month == mes]
    return df_filtrado
