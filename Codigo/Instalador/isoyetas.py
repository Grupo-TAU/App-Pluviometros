from Codigo.Instalador.Funciones_basicas import *

def obtener_ubicaciones(df_config):
    """
    Extrae las coordenadas de ubicación de los equipos desde un DataFrame de configuración.
    
    Parámetros:
    - df_config: DataFrame con las configuraciones de los equipos, incluyendo ID, X y Y.

    Retorna:
    - Diccionario donde las claves son los IDs y los valores son tuplas con coordenadas (X, Y).
    """
    return {row['ID']: (row['X'], row['Y']) for _, row in df_config.iterrows()}

def obtener_precipitaciones(df_lluvias, nombres_equipos):
    """
    Extrae los valores de precipitación de los nombres de estaciones en el DataFrame.
    
    Parámetros:
    - df_lluvias: DataFrame con las precipitaciones acumuladas.
    - nombres_equipos: Lista con los nombres de los equipos a extraer.

    Retorna:
    - np.array con los valores de precipitación en el mismo orden que nombres_equipos.
    """
    return np.array([df_lluvias.at["Total", nombre] if nombre in df_lluvias.columns else 0 for nombre in nombres_equipos])

def extraer_coordenadas(ubicaciones, df_acumulados_diarios_total):
    """
    Obtiene las coordenadas y los valores de precipitación para cada estación.
    
    Parámetros:
    - ubicaciones: Diccionario con las ubicaciones de los equipos.
    - df_acumulados_diarios_total: DataFrame con los datos de precipitación acumulada.

    Retorna:
    - Lista de nombres de estaciones, arrays de coordenadas X e Y, y valores de precipitación Z.
    """
    nombres = list(ubicaciones.keys())
    X = np.array([ubicaciones[n][0] for n in nombres])
    Y = np.array([ubicaciones[n][1] for n in nombres])
    Z = obtener_precipitaciones(df_acumulados_diarios_total, nombres)
    return nombres, X, Y, Z

def interpolar_idw(X, Y, Z, xq, yq, power=2):
    """
    Interpola los valores de precipitación usando el método de ponderación inversa a la distancia (IDW).
    
    Parámetros:
    - X, Y, Z: Arrays con coordenadas y valores de precipitación.
    - xq, yq: Arrays de consulta para la interpolación.
    - power: Exponente de la ponderación de la distancia (por defecto 2).

    Retorna:
    - Grillas interpoladas Xq, Yq y Zq con los valores estimados.
    """
    Xq, Yq = np.meshgrid(xq, yq)
    Zq = np.zeros(Xq.shape)
    for i in range(Xq.shape[0]):
        for j in range(Xq.shape[1]):
            distances = np.sqrt((X - Xq[i, j])**2 + (Y - Yq[i, j])**2)
            weights = 1 / distances**power
            weights[distances == 0] = np.inf
            Zq[i, j] = np.sum(weights * Z) / np.sum(weights)
    return Xq, Yq, Zq

def determinar_niveles(Zq, num_niveles=5):
    """
    Calcula los niveles para las curvas de nivel en función de los valores interpolados.
    
    Parámetros:
    - Zq: Matriz de valores interpolados de precipitación.
    - num_niveles: Cantidad de niveles a generar (mínimo 5).

    Retorna:
    - Array con los valores de los niveles.
    """
    minZ, maxZ = np.min(Zq), np.max(Zq)
    rango = maxZ - minZ
    multiplo = np.ceil(rango / num_niveles)
    niveles = np.arange(np.floor(minZ / multiplo) * multiplo, np.ceil(maxZ / multiplo) * multiplo + multiplo, multiplo)
    if len(niveles) < 5:
        raise ValueError('No hay suficientes niveles para crear el mapa de isoyetas.')
    return niveles

def obtener_posicion_adecuada(x, y, i, X, Y):
    """
    Ajusta la posición de los nombres de las estaciones para evitar superposiciones.
    
    Parámetros:
    - x, y: Coordenadas originales.
    - i: Índice de la estación.
    - X, Y: Arrays con todas las coordenadas.

    Retorna:
    - Coordenadas ajustadas para la etiqueta.
    """
    offset_x, offset_y = 150, 150
    for j in range(len(X)):
        if i != j:
            if np.sqrt((x - X[j])**2 + (y - Y[j])**2) < 100:
                offset_x, offset_y = 50, 50
                break
    return x + offset_x, y + offset_y

def fig_graficar_isoyetas(X, Y, Zq, Xq, Yq, niveles, nombres, mapa_fondo_path):
    """
    Genera un mapa de isoyetas interpolado usando el método IDW.
    
    Parámetros:
    - X, Y: Arrays con las coordenadas de las estaciones.
    - Zq: Matriz con los valores interpolados de precipitación.
    - Xq, Yq: Arrays con la malla de puntos de interpolación.
    - niveles: Lista de niveles de precipitación para las curvas de nivel.
    - nombres: Lista con los nombres de las estaciones.
    - mapa_fondo_path: Ruta de la imagen del mapa de fondo.

    Retorna:
    - Figura de Matplotlib con el mapa de isoyetas.
    """    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Usar los niveles predefinidos
    cs = ax.contourf(Xq, Yq, Zq, levels=niveles, cmap="Blues", alpha=0.8)  
    
    # Cargar el mapa de fondo
    mapa_fondo = mpimg.imread(mapa_fondo_path)
    extent = [551332.763, 590932.763, 6131816.936, 6160416.936]
    ax.imshow(mapa_fondo, extent=extent, origin='upper')
    
    # Agregar las ubicaciones y nombres de las estaciones
    ax.scatter(X, Y, c='red', edgecolors='black', zorder=5)
    for i, nombre in enumerate(nombres):
        x_pos, y_pos = obtener_posicion_adecuada(X[i], Y[i], i, X, Y)
        ax.text(x_pos, y_pos, nombre, fontsize=12, color='blue',
                bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=0.2))
        
    # Añadir las curvas de nivel
    contour_lines = ax.contour(Xq, Yq, Zq, levels=niveles, colors='black')  
    
    # Etiquetas para las curvas de nivel
    ax.clabel(contour_lines, inline=True, fontsize=12, fmt='%d', colors='black')  
    
    # Agregar un colorbar a la derecha para representar los niveles
    cbar = fig.colorbar(cs, ax=ax, orientation='vertical', fraction=0.03, pad=0.04)
    cbar.set_label('Precipitación acumulada (mm)', fontsize=12)
    cbar.set_ticks(niveles[1:-1])
    
    ax.set_xticks([])
    ax.set_yticks([])

    
    ax.set_title('Mapa de Isoyetas usando IDW', fontsize=14)
    ax.set_aspect('equal')
    
    fig.subplots_adjust(left=0.005, right=0.80, top=0.95, bottom=0.1)
    
    return fig

def graficar_isoyetas(df_config, df_acumulados_diarios_total):
    """
    Genera un mapa de isoyetas basado en interpolación IDW a partir de datos de precipitaciones.
    
    Parámetros:
    - df_config: DataFrame con configuraciones y ubicaciones de las estaciones.
    - df_acumulados_diarios_total: DataFrame con precipitaciones acumuladas.

    Retorna:
    - Figura de matplotlib con el mapa de isoyetas.
    """
    ubicaciones = obtener_ubicaciones(df_config)
    nombres, X, Y, Z = extraer_coordenadas(ubicaciones, df_acumulados_diarios_total)
    xq = np.linspace(551332.763, 590932.763, 300)
    yq = np.linspace(6131816.936, 6160416.936, 300)
    Xq, Yq, Zq = interpolar_idw(X, Y, Z, xq, yq)
    niveles = determinar_niveles(Zq)

    return fig_graficar_isoyetas(X, Y, Zq, Xq, Yq, niveles, nombres, 'MONTEVIDEO.png')

def fig_graficar_isoyetas_tr(X, Y, Zq, Xq, Yq, tr, nombres, mapa_fondo_path):
    """
    Genera un mapa de isoyetas interpoladas mediante IDW y superpone las ubicaciones de estaciones sobre un mapa de fondo.
    
    Parámetros:
    - X: np.array con las coordenadas X de las estaciones.
    - Y: np.array con las coordenadas Y de las estaciones.
    - Zq: np.array con los valores interpolados de precipitación en la grilla.
    - Xq: np.array con la malla de coordenadas X generada para la interpolación.
    - Yq: np.array con la malla de coordenadas Y generada para la interpolación.
    - tr: Lista de niveles de precipitación para las curvas de nivel.
    - nombres: Lista de nombres de las estaciones.
    - mapa_fondo_path: Ruta del archivo de imagen del mapa de fondo.

    Retorna:
    - fig: Figura de Matplotlib con el mapa de isoyetas generado.
    """
    fig, ax = plt.subplots(figsize=(14, 8))  # Crear la figura y los ejes
    cs = ax.contourf(Xq, Yq, Zq, levels=tr, cmap="Blues", alpha=0.8)  # Usar los niveles predefinidos
    
    # Cargar el mapa de fondo
    mapa_fondo = mpimg.imread(mapa_fondo_path)
    extent = [551332.763, 590932.763, 6131816.936, 6160416.936]
    ax.imshow(mapa_fondo, extent=extent, origin='upper')
    
    # Agregar las ubicaciones y nombres de las estaciones
    ax.scatter(X, Y, c='red', edgecolors='black', zorder=5)
    for i, nombre in enumerate(nombres):
        x_pos, y_pos = obtener_posicion_adecuada(X[i], Y[i], i, X, Y)
        ax.text(x_pos, y_pos, nombre, fontsize=12, color='blue',
                bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=0.2))
    
    tr_dict = dict(zip(tr, tr_x_duracion))
    
    # Graficar las curvas de nivel con sus etiquetas
    contour_lines = ax.contour(Xq, Yq, Zq, levels=tr, colors='black')  # Añadir las curvas de nivel
    ax.clabel(contour_lines, inline=True, fontsize=12, fmt=lambda x: tr_dict.get(x, f"{x:.1f}"), colors='black')  # Etiquetas para las curvas de nivel
    
    # Agregar un colorbar a la derecha para representar los niveles
    cbar = fig.colorbar(cs, ax=ax, orientation='vertical', fraction=0.03, pad=0.04)
    cbar.set_label('Precipitación acumulada (mm)', fontsize=12)
    # Configurar las etiquetas de la barra de color
    cbar.set_ticks(tr)  # Usar los valores de tr como ticks
    cbar.set_ticklabels([f"{tr_val} - {tr_name}" for tr_val, tr_name in zip(tr, tr_x_duracion)], fontsize=12)  # Etiquetas en formato "TR - Nombre"

    #cbar.set_ticks(tr[1:-1])

    ax.set_xticks([])
    ax.set_yticks([])
    
    ax.set_title('Mapa de Isoyetas usando IDW', fontsize=14)
    ax.set_aspect('equal')
    
    fig.subplots_adjust(left=0.005, right=0.80, top=0.95, bottom=0.1)
    
    # Retornar la figura
    return fig

def graficar_isoyetas_tr(df_config, df_acumulados_diarios_total, tr):
    """
    Genera un mapa de isoyetas utilizando niveles basados en períodos de retorno.
    
    Parámetros:
    - df_config: DataFrame con ubicaciones de estaciones.
    - df_acumulados_diarios_total: DataFrame con precipitaciones acumuladas.
    - tr: Lista de valores de períodos de retorno.

    Retorna:
    - Figura de matplotlib con el mapa de isoyetas.
    """
    ubicaciones = obtener_ubicaciones(df_config)
    nombres, X, Y, Z = extraer_coordenadas(ubicaciones, df_acumulados_diarios_total)
    xq = np.linspace(551332.763, 590932.763, 300)
    yq = np.linspace(6131816.936, 6160416.936, 300)
    Xq, Yq, Zq = interpolar_idw(X, Y, Z, xq, yq)

    return fig_graficar_isoyetas_tr(X, Y, Zq, Xq, Yq, tr, nombres, 'MONTEVIDEO.png')
