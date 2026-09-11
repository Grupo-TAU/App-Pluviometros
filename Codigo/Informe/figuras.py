"""
Figuras del informe pluviometrico mensual.

Cada funcion devuelve una figura de matplotlib. El guardado lo hace generar_informe.py, que
es quien conoce la carpeta de salida y la numeracion.
"""
import os

import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from Codigo.Instalador.Funciones_basicas import duracion_tormenta, precipitacion_tr
from Codigo.Instalador.Funciones_mensual import valor_lluvias_historicas
from Codigo.Instalador.isoyetas import (determinar_niveles, fig_graficar_isoyetas,
                                        interpolar_idw, obtener_ubicaciones)
from Codigo.Informe.datos import nombre_mes
from Codigo.Informe.eventos import DURACIONES

# Recorte del mapa de Montevideo en coordenadas UTM 21S, igual que en el modulo de isoyetas.
EXTENSION_MAPA = [551332.763, 590932.763, 6131816.936, 6160416.936]

ETIQUETAS_CUARTILES = ['Primer cuartil', 'Mediana', 'Tercer cuartil', 'Maximo']
COLORES_CUARTILES = ['tab:red', 'tab:green', 'tab:orange', 'tab:purple']


def _ruta_mapa(carpeta_base):
    return os.path.join(carpeta_base, 'MONTEVIDEO.png')


def acumulado_mensual(datos, acumulados):
    """
    Figura 6-1: acumulado mensual por equipo, con los cuartiles historicos del mes.

    Parametros:
    - datos: Instancia de DatosMes.
    - acumulados: Serie de acumulados mensuales por ID (puede incluir INUMET).

    Retorna:
    - Figura de matplotlib.
    """
    fig, ax = plt.subplots(figsize=(12, 7))

    colores = ['tab:orange' if i == 'INUMET' else 'tab:blue' for i in acumulados.index]
    ax.bar(acumulados.index, acumulados.values, color=colores, alpha=0.85)

    for cuartil, (valor, etiqueta, color) in enumerate(
            zip(valor_lluvias_historicas(datos.mes), ETIQUETAS_CUARTILES, COLORES_CUARTILES)):
        ax.axhline(valor, color=color, linestyle='--', linewidth=1.8, label=etiqueta)

    for posicion, valor in enumerate(acumulados.values):
        ax.text(posicion, valor, f'{valor:.1f}', ha='center', va='bottom', fontsize=9)

    ax.set_ylabel('Precipitacion acumulada (mm)', fontsize=13)
    ax.set_xlabel('Equipo', fontsize=13)
    ax.set_title(f'Acumulado mensual correspondiente al mes de {nombre_mes(datos.mes)}', fontsize=15)
    ax.grid(True, axis='y', linestyle='--', linewidth=0.5)
    ax.legend(loc='upper left', bbox_to_anchor=(1, 1), fontsize=11)

    plt.tight_layout()

    return fig


def serie_diaria(datos, descartados=()):
    """
    Figura 6-2: serie temporal de precipitacion acumulada diaria.

    Parametros:
    - datos: Instancia de DatosMes.
    - descartados: IDs de equipos excluidos del analisis.

    Retorna:
    - Figura de matplotlib.
    """
    conservados = [c for c in datos.df_diario.columns if c not in set(descartados)]
    df = datos.df_diario[conservados]

    fig, ax = plt.subplots(figsize=(12, 7))

    for columna in df.columns:
        ax.plot(df.index, df[columna], marker='o', markersize=3, linewidth=1.2, label=columna)

    if datos.inumet is not None:
        ax.plot(df.index, datos.inumet.reindex(df.index), color='black', linestyle='--',
                linewidth=2, label='INUMET')

    ax.set_xlabel('Dia', fontsize=13)
    ax.set_ylabel('Precipitacion acumulada diaria (mm)', fontsize=13)
    ax.set_title(f'Serie temporal de precipitacion acumulada diaria para el mes de '
                 f'{nombre_mes(datos.mes)}', fontsize=15)

    ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%m'))
    ax.grid(True, linestyle='--', linewidth=0.5)
    ax.legend(loc='upper left', bbox_to_anchor=(1, 1), fontsize=10)

    plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
    plt.tight_layout()

    return fig


def qq_contra_inumet(datos, descartados=()):
    """
    Figura 4-1: cuantiles del acumulado diario de cada equipo contra los de INUMET.

    Los equipos bien correlacionados con INUMET se acercan a la recta de 45 grados.

    Parametros:
    - datos: Instancia de DatosMes.
    - descartados: IDs de equipos excluidos del analisis.

    Retorna:
    - Figura de matplotlib, o None si no hay datos de INUMET.
    """
    if datos.inumet is None:
        return None

    conservados = [c for c in datos.df_diario.columns if c not in set(descartados)]

    # Comparacion contra INUMET: dias de 7 a 7, como los suyos.
    df = datos.df_diario_inumet[conservados].copy()
    df['INUMET'] = datos.inumet.reindex(df.index)

    # Se sacan los dias sin lluvia, que solo amontonan puntos en el origen.
    df = df[(df.fillna(0) != 0).any(axis=1)]

    ordenado = df.apply(lambda columna: columna.sort_values().reset_index(drop=True))

    fig, ax = plt.subplots(figsize=(11, 8))

    for columna in ordenado.columns:
        if columna == 'INUMET':
            continue
        ax.plot(ordenado['INUMET'], ordenado[columna], marker='o', markersize=4, label=columna)

    tope = float(np.nanmax(ordenado.to_numpy()))
    ax.plot([0, tope], [0, tope], color='black', linestyle='--', linewidth=1.5, label='45°')

    ax.set_xlabel('Cuantiles del acumulado diario de INUMET (mm)', fontsize=13)
    ax.set_ylabel('Cuantiles del acumulado diario por equipo (mm)', fontsize=13)
    ax.set_title('Analisis de precipitacion acumulada respecto a registros de INUMET', fontsize=14)
    ax.grid(True, linestyle='--', linewidth=0.5)
    ax.legend(loc='upper left', bbox_to_anchor=(1, 1), fontsize=10)

    plt.tight_layout()

    return fig


def _isoyetas(datos, valores, titulo, carpeta_base):
    """
    Arma un mapa de isoyetas IDW a partir de una serie de acumulados por ID de equipo.

    Parametros:
    - datos: Instancia de DatosMes.
    - valores: Serie de acumulados indexada por ID de equipo.
    - titulo: Titulo del mapa.
    - carpeta_base: Carpeta donde esta MONTEVIDEO.png.

    Retorna:
    - Figura de matplotlib, o None si no hay coordenadas suficientes.
    """
    equipos = datos.equipos.dropna(subset=['X', 'Y'])
    equipos = equipos[equipos['ID'].isin(valores.index)]

    if len(equipos) < 3:
        return None

    ubicaciones = obtener_ubicaciones(equipos)
    nombres = list(ubicaciones.keys())

    X = np.array([ubicaciones[n][0] for n in nombres], dtype=float)
    Y = np.array([ubicaciones[n][1] for n in nombres], dtype=float)
    Z = np.array([float(valores.get(n, 0)) for n in nombres])

    xq = np.linspace(EXTENSION_MAPA[0], EXTENSION_MAPA[1], 300)
    yq = np.linspace(EXTENSION_MAPA[2], EXTENSION_MAPA[3], 300)
    Xq, Yq, Zq = interpolar_idw(X, Y, Z, xq, yq)

    try:
        niveles = determinar_niveles(Zq)
    except ValueError:
        return None  # Lluvia demasiado pareja para trazar curvas de nivel.

    fig = fig_graficar_isoyetas(X, Y, Zq, Xq, Yq, niveles, nombres, _ruta_mapa(carpeta_base))
    fig.axes[0].set_title(titulo, fontsize=14)

    return fig


def isoyetas_mensuales(datos, acumulados, carpeta_base):
    """Figura 6-3: isoyetas del acumulado mensual."""
    return _isoyetas(datos, acumulados.drop(labels=['INUMET'], errors='ignore'),
                     f'Isoyetas de precipitacion acumulada para el mes de {nombre_mes(datos.mes)}',
                     carpeta_base)


def isoyetas_del_evento(datos, evento, carpeta_base):
    """Figura 6-6/6-10: distribucion espacial de la tormenta."""
    return _isoyetas(datos, evento.acumulados,
                     f'Distribucion espacial de la tormenta del '
                     f'{evento.inicio.day} de {nombre_mes(evento.inicio.month)}',
                     carpeta_base)


def hietograma(evento):
    """
    Figura 6-4/6-8: hietograma de la tormenta, con la lluvia de cada equipo por rango de
    5 minutos.

    Parametros:
    - evento: Instancia de Evento.

    Retorna:
    - Figura de matplotlib.
    """
    fig, ax = plt.subplots(figsize=(12, 6))

    for columna in evento.df_5min.columns:
        ax.plot(evento.df_5min.index, evento.df_5min[columna], linewidth=1.2, label=columna)

    ax.set_xlabel('Hora', fontsize=13)
    ax.set_ylabel('Precipitacion cada 5 min (mm)', fontsize=13)
    ax.set_title(f'Hietograma de tormenta del {evento.inicio.strftime("%d-%m-%Y")}', fontsize=15)

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax.grid(True, linestyle='--', linewidth=0.5)
    ax.legend(loc='upper left', bbox_to_anchor=(1, 1), fontsize=10)

    plt.tight_layout()

    return fig


def acumulada_del_evento(evento):
    """
    Figura 6-5/6-9: precipitacion acumulada de la tormenta para cada equipo.

    Parametros:
    - evento: Instancia de Evento.

    Retorna:
    - Figura de matplotlib.
    """
    acumulado = evento.df_5min.fillna(0).cumsum()

    fig, ax = plt.subplots(figsize=(12, 6))

    for columna in acumulado.columns:
        ax.plot(acumulado.index, acumulado[columna], linewidth=1.6, label=columna)

    ax.set_xlabel('Hora', fontsize=13)
    ax.set_ylabel('Precipitacion acumulada (mm)', fontsize=13)
    ax.set_title(f'Precipitacion acumulada de la tormenta del '
                 f'{evento.inicio.strftime("%d-%m-%Y")}', fontsize=15)

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax.grid(True, linestyle='--', linewidth=0.5)
    ax.legend(loc='upper left', bbox_to_anchor=(1, 1), fontsize=10)

    plt.tight_layout()

    return fig


def intensidad_vs_tr(tabla_maximos):
    """
    Figura 6-7/6-11: acumulados maximos medidos contra las curvas IDF del IMFIA.

    Parametros:
    - tabla_maximos: Salida de eventos.maximos_por_duracion.

    Retorna:
    - Figura de matplotlib.
    """
    fig, ax = plt.subplots(figsize=(10, 7))

    for nombre, valores in precipitacion_tr.items():
        ax.plot(duracion_tormenta, valores, linewidth=1.4, label=nombre)

    ax.scatter(tabla_maximos['Duracion (min)'], tabla_maximos['P (mm)'],
               color='red', marker='o', s=60, zorder=5, label='Tormenta registrada')

    ax.set_xlabel('Duracion de la tormenta (min)', fontsize=13)
    ax.set_ylabel('Precipitacion (mm)', fontsize=13)
    ax.set_title('Intensidad de precipitacion para distintos periodos de retorno', fontsize=14)
    ax.set_xlim(0, max(DURACIONES) * 1.1)
    ax.grid(True, linestyle='--', linewidth=0.5)
    ax.legend(fontsize=10)

    plt.tight_layout()

    return fig


def mapa_de_la_red(datos, carpeta_base):
    """
    Figura 1-1: ubicacion de los equipos de la red sobre el mapa del departamento.

    Parametros:
    - datos: Instancia de DatosMes.
    - carpeta_base: Carpeta donde esta MONTEVIDEO.png.

    Retorna:
    - Figura de matplotlib, o None si no hay coordenadas.
    """
    equipos = datos.equipos.dropna(subset=['X', 'Y'])
    if equipos.empty:
        return None

    fig, ax = plt.subplots(figsize=(12, 8))

    ax.imshow(plt.imread(_ruta_mapa(carpeta_base)), extent=EXTENSION_MAPA, origin='upper')
    ax.scatter(equipos['X'], equipos['Y'], c='red', edgecolors='black', s=60, zorder=5)

    for _, equipo in equipos.iterrows():
        ax.text(equipo['X'] + 150, equipo['Y'] + 150, equipo['ID'], fontsize=10, color='blue',
                bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=0.2))

    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect('equal')
    ax.set_title('Red Hidrometeorologica de Montevideo', fontsize=14)

    plt.tight_layout()

    return fig
