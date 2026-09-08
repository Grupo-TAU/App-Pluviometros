import os
import math
import unicodedata
import locale
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
import matplotlib.dates as mdates
from matplotlib.dates import DateFormatter
from tkinter import *
import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pyperclip
import matplotlib.image as mpimg
from PIL import Image, ImageTk
from datetime import time

duracion_tormenta = [10, 20, 30, 60, 120, 180, 360, 720, 1440]

# Valores de precipitación para cada periodo de retorno (TR)
precipitacion_tr = {
    "TR 2 años": [15.1, 19.8, 25.3, 33.4, 44.3, 51.4, 65.5, 80.5, 93.8],
    "TR 5 años": [19.4, 26.2, 33.37, 43.6, 57.2, 67.4, 85.9, 106.5, 124.6],
    "TR 10 años": [22.2, 30.4, 38.7, 50.3, 65.8, 78.0, 99.5, 123.7, 145.0],
    "TR 20 años": [24.9, 34.5, 43.9, 56.8, 74.0, 88.2, 112.5, 140.2, 164.6],
    "TR 25 años": [25.8, 35.8, 45.5, 58.8, 76.6, 91.4, 116.5, 145.5, 170.8],
    "TR 50 años": [28.5, 39.7, 50.6, 65.1, 84.6, 101.3, 129.3, 161.6, 189.9],
    "TR 100 años": [31.1, 43.7, 55.6, 71.3, 92.5, 111.2, 142.0, 177.6, 208.9]
}

precipitacion_tr_x_duracion = {
    "10 min": [15.1, 19.4, 22.2, 24.9, 25.8, 28.5, 31.1],
    "20 min": [19.8, 26.2, 30.4, 34.5, 35.8, 39.7, 43.7],
    "30 min": [25.3, 33.37, 38.7, 43.9, 45.5, 50.6, 55.6],
    "60 min": [33.4, 43.6, 50.3, 56.8, 58.8, 65.1, 71.3],
    "120 min": [44.3, 57.2, 65.8, 74.0, 76.6, 84.6, 92.5],
    "180 min": [51.4, 67.4, 78.0, 88.2, 91.4, 101.3, 111.2],
    "360 min": [65.5, 85.9, 99.5, 112.5, 116.5, 129.3, 142.0],
    "720 min": [80.5, 106.5, 123.7, 140.2, 145.5, 161.6, 177.6],
    "1440 min": [93.8, 124.6, 145.0, 164.6, 170.8, 189.9, 208.9]
}

tr_x_duracion = ["TR 2", "TR 5", "TR 10", "TR 20", "TR 25", "TR 50", "TR 100"]

def latlon_a_utm21s(lat, lon):
    """
    Convierte coordenadas geograficas WGS 84 (EPSG:4326) a UTM zona 21 Sur (EPSG:32721).

    Es la proyeccion Transversa de Mercator estandar. Se calcula aca en vez de usar pyproj
    porque esa libreria arrastra ~25 MB de tablas de proyecciones al instalador para esta
    unica cuenta. Verificado contra pyproj sobre el area de Montevideo: el desvio maximo es
    de 0.07 mm, muy por debajo de la precision de las coordenadas de los equipos.

    Parametros:
    - lat: Latitud en grados decimales (negativa en el hemisferio sur).
    - lon: Longitud en grados decimales (negativa al oeste de Greenwich).

    Retorna:
    - Tupla (X, Y) en metros.
    """
    SEMIEJE_MAYOR = 6378137.0            # Semieje mayor del elipsoide WGS 84
    APLANAMIENTO = 1 / 298.257223563     # Aplanamiento del elipsoide WGS 84
    FACTOR_ESCALA = 0.9996               # Factor de escala en el meridiano central UTM
    MERIDIANO_CENTRAL = math.radians(-57.0)  # Meridiano central de la zona 21
    FALSO_ESTE = 500000.0
    FALSO_NORTE = 10000000.0             # Solo aplica en el hemisferio sur

    e2 = APLANAMIENTO * (2 - APLANAMIENTO)   # Excentricidad al cuadrado
    ep2 = e2 / (1 - e2)                      # Segunda excentricidad al cuadrado

    phi = math.radians(lat)
    delta_lon = math.radians(lon) - MERIDIANO_CENTRAL

    N = SEMIEJE_MAYOR / math.sqrt(1 - e2 * math.sin(phi) ** 2)  # Radio de curvatura
    T = math.tan(phi) ** 2
    C = ep2 * math.cos(phi) ** 2
    A = delta_lon * math.cos(phi)

    # Arco de meridiano desde el ecuador hasta la latitud phi
    M = SEMIEJE_MAYOR * (
        (1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256) * phi
        - (3 * e2 / 8 + 3 * e2 ** 2 / 32 + 45 * e2 ** 3 / 1024) * math.sin(2 * phi)
        + (15 * e2 ** 2 / 256 + 45 * e2 ** 3 / 1024) * math.sin(4 * phi)
        - (35 * e2 ** 3 / 3072) * math.sin(6 * phi)
    )

    x = FACTOR_ESCALA * N * (
        A
        + (1 - T + C) * A ** 3 / 6
        + (5 - 18 * T + T ** 2 + 72 * C - 58 * ep2) * A ** 5 / 120
    ) + FALSO_ESTE

    y = FACTOR_ESCALA * (
        M + N * math.tan(phi) * (
            A ** 2 / 2
            + (5 - T + 9 * C + 4 * C ** 2) * A ** 4 / 24
            + (61 - 58 * T + T ** 2 + 600 * C - 330 * ep2) * A ** 6 / 720
        )
    ) + FALSO_NORTE

    return x, y


def detectar_formato_fecha(serie_fechas):
    """
    Detecta si una columna de fechas en texto viene en formato día primero (dd/mm/yyyy) o
    año primero (yyyy/mm/dd o yyyy-mm-dd), inspeccionando el primer valor no nulo de la serie.

    Algunos meses exportan el CSV con un formato y otros con el otro, por lo que no se puede
    fijar un formato único para todos los archivos. No alcanza con pasarle dayfirst=True a
    pandas siempre: si la fecha viene año primero (ej. "2026/07/05") y día y mes son ambos
    <=12, dayfirst=True hace que pandas interprete mal el orden (año-día-mes en vez de
    año-mes-día), por lo que hay que detectar explícitamente cuál de los dos formatos es.

    Parámetros:
    - serie_fechas: Serie de pandas con las fechas en formato texto.

    Retorna:
    - Diccionario con los argumentos ('dayfirst', 'yearfirst') a pasar a pd.to_datetime.
    """
    for valor in serie_fechas.dropna().astype(str):
        parte_fecha = valor.strip().split(' ')[0]
        separador = '/' if '/' in parte_fecha else ('-' if '-' in parte_fecha else None)
        if separador is None:
            continue

        primer_token = parte_fecha.split(separador)[0]
        if len(primer_token) == 4:
            return {'dayfirst': False, 'yearfirst': True}  # yyyy/mm/dd
        return {'dayfirst': True, 'yearfirst': False}  # dd/mm/yyyy

    return {'dayfirst': True, 'yearfirst': False}  # Sin datos: se asume día primero

def leer_archivo_principal(archivo):
    """
    Lee un archivo CSV con datos de precipitación, realiza ajustes en las fechas y las redondea a intervalos de 5 minutos.
    
    Parámetros:
    - archivo: Ruta del archivo CSV con los datos.
    
    Retorna:
    - DataFrame con los datos agrupados por fecha redondeada a 5 minutos.
    """
    df_datos = pd.read_csv(archivo, encoding="utf-8")
    
    df_datos['Time'] = pd.to_datetime(df_datos['Time'], **detectar_formato_fecha(df_datos['Time']))

    
    # Redondear a 5 minutos
    df_datos['Time'] = df_datos['Time'].dt.round('5min')
    
    df_datos = df_datos.groupby('Time').max()  # max() mantiene el valor no nulo más alto por grupo
    
    # Reindexar para asegurar intervalos completos de 5 minutos
    df_datos = df_datos.reindex(pd.date_range(start=df_datos.index.min(), 
                              end=df_datos.index.max(), 
                              freq='5min'))
    

    detectar_vuelta_valor(df_datos)   
    return df_datos

def detectar_vuelta_valor(df_datos):
    # Recorremos cada columna (pluviómetro)
    for col in df_datos.columns:
        for i in range(1, len(df_datos) - 1):  # Evitamos el primer y último índice
            valor_anterior = df_datos[col].iloc[i - 1]
            valor_actual = df_datos[col].iloc[i]
            valor_siguiente = df_datos[col].iloc[i + 1]
            
            # Comprobamos si la secuencia es > 0 -> 0 -> valor_anterior
            if valor_anterior > 0 and valor_actual == 0 and valor_siguiente == valor_anterior:
                # Usamos .loc[] para evitar la advertencia
                df_datos.loc[df_datos.index[i], col] = np.nan

def eliminar_tildes(texto):
    """
    Elimina los acentos de un texto.
    
    Parámetros:
    - texto: Cadena de texto con posibles acentos.
    
    Retorna:
    - Cadena de texto sin acentos.
    """
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn'
    )

def traducir_id_a_lugar(df_config, id_columna):
    lugar = df_config.loc[df_config['ID'] == id_columna, 'Lugar'].values
    
    if lugar.size > 0:
        return lugar[0]
    else:
        return None  
    
def traducir_lugar_a_id(df_config, lugar_columna):
    """
    Traduce un ID de lugar a su nombre de lugar correspondiente.
    
    Parámetros:
    - df_config: DataFrame con la configuración de lugares e IDs.
    - id_columna: ID de la columna que se desea traducir.
    
    Retorna:
    - Nombre del lugar correspondiente al ID, o None si no se encuentra.
    """
    ID = df_config.loc[df_config['Lugar'] == lugar_columna, 'ID'].values
    
    if ID.size > 0:
        return ID[0]
    else:
        return None 

def traducir_columnas_lugar_a_id(df_config, df_acumulados_diarios):
    """
    Traduce el nombre de un lugar a su ID correspondiente.
    
    Parámetros:
    - df_config: DataFrame con la configuración de lugares e IDs.
    - lugar_columna: Nombre del lugar que se desea traducir.
    
    Retorna:
    - ID correspondiente al nombre del lugar, o None si no se encuentra.
    """
    mapa_traduccion = dict(zip(df_config['Lugar'], df_config['ID']))
    
    df_acumulados_diarios.columns = [eliminar_tildes(col) for col in df_acumulados_diarios.columns]
    
    nuevas_columnas = [
        mapa_traduccion.get(col, col) if col != 'INUMET' else col 
        for col in df_acumulados_diarios.columns
    ]
    
    df_acumulados_diarios.columns = nuevas_columnas
    
    return df_acumulados_diarios
    

def leer_archivo_verificador(archivo, df_datos):
    """
    Lee el archivo de validación de datos, realiza las transformaciones necesarias y agrega la columna de precipitaciones crudas.
    
    Parámetros:
    - archivo: Ruta del archivo CSV con los datos de verificación.
    - df_datos: DataFrame con los datos existentes a los que se agregará la columna de precipitaciones crudas.
    
    Retorna:
    - DataFrame con la columna de precipitaciones crudas añadida.
    """
    df_datos_validador = pd.read_csv(archivo, encoding="utf-8", sep=';', decimal=',')
    
    # Renombrar todas las columnas para evitar problemas de caracteres
    df_datos_validador.columns = (df_datos_validador.columns
                                  .str.normalize('NFKD')
                                  .str.encode('ascii', 'ignore')
                                  .str.decode('ascii')
                                  .str.replace(' ', '_')
                                  .str.lower())
    df_datos_validador['fecha'] = pd.to_datetime(df_datos_validador['fecha'], **detectar_formato_fecha(df_datos_validador['fecha']))
    df_datos_validador['fecha'] = df_datos_validador['fecha'].dt.round('5min')
        
    df_seleccionado = df_datos_validador[['fecha', 'precipitacion_-_valor_manual']].copy()
        
    df_seleccionado['precipitacion_-_valor_manual'] = df_seleccionado['precipitacion_-_valor_manual'].fillna(0)
        
    df_seleccionado = df_seleccionado.groupby('fecha').max()  # max() mantiene el valor no nulo más alto por grupo
        
    df_seleccionado.index = df_seleccionado.index.strftime('%Y-%m-%d %H:%M:%S')
    
    
    df_datos.index = pd.to_datetime(df_datos.index)
    
    df_seleccionado.index = pd.to_datetime(df_seleccionado.index, format='%Y-%m-%d %H:%M:%S', dayfirst=True, errors='coerce')
    
    start_date = df_datos.index.min()
    end_date = df_datos.index.max()
    
    df_seleccionado = df_seleccionado[(df_seleccionado.index >= start_date) & (df_seleccionado.index <= end_date)]
    
    df_seleccionado = df_seleccionado.reindex(df_datos.index, method='ffill')  
    
    # Agregar columna con nombre de la estación
    nombre_columna = df_datos_validador['estacion'].iloc[0]  
    nombre_columna = eliminar_tildes(nombre_columna)
    nombre_columna = nombre_columna.replace('Pluviometro - ', '').replace('Estacion Meteorologica - ', '')

    df_datos[nombre_columna] = df_seleccionado['precipitacion_-_valor_manual']

    return df_datos

def leer_archivo_inumet(archivo):   
    """
    Lee el archivo de INUMET en formato CSV o Excel y lo devuelve como un DataFrame.

    Parámetros:
    - archivo: Ruta del archivo (puede ser .csv, .xlsx o .xls).

    Retorna:
    - DataFrame con los datos de INUMET.
    """ 
    # Verificar si el archivo es CSV o Excel
    if archivo.endswith('.csv'):
        with open(archivo, "r", encoding="utf-8") as f:
            primera_linea = f.readline()
        # Contar la cantidad de apariciones de cada separador
        sep_puntoycoma = primera_linea.count(";")
        sep_coma = primera_linea.count(",")

        # Elegir el separador con más ocurrencias
        sep = ";" if sep_puntoycoma > sep_coma else ","

        # Leer el CSV con el separador detectado
        df_inumet = pd.read_csv(archivo, encoding="utf-8", sep=sep)
    elif archivo.endswith('.xlsx') or archivo.endswith('.xls'):
        df_inumet = pd.read_excel(archivo, engine='openpyxl')  # Usa 'openpyxl' para archivos .xlsx
    else:
        raise ValueError("Formato de archivo no soportado. Usa CSV o Excel (.xlsx, .xls).")
    
    # Convertir la columna de fecha a formato estándar
    df_inumet['FECHA'] = pd.to_datetime(df_inumet['FECHA'], **detectar_formato_fecha(df_inumet['FECHA'])).dt.strftime('%Y-%m-%d')
    df_inumet.set_index('FECHA', inplace=True)
    
    return df_inumet

def acumulados(df_5min):
    """
    Acumula la lluvia a lo largo del periodo, para la curva de acumulado de tormenta.

    Recibe la lluvia ya calculada por calcular_tablas_refinadas(), asi que aca solo queda
    sumarla: la diferencia contra el contador del equipo, el descarte de reinicios y el de
    outliers ya se hicieron una sola vez, en el camino de calculo comun.

    Parametros:
    - df_5min: DataFrame de lluvia por rango de 5 minutos.

    Retorna:
    - DataFrame con el acumulado corrido.
    """
    return df_5min.fillna(0).cumsum()

def acumulado_total(acumulados):
    """
    Calcula el total acumulado para cada columna (pluviómetro).
    
    Parámetros:
    - acumulados: DataFrame con los acumulados de precipitación.
    
    Retorna:
    - DataFrame con el total acumulado por pluviómetro.
    """ 
    acumulado_total = acumulados.max()
    acumulado_total.name = 'Total'  
    
    return acumulado_total.to_frame().T  

def acumulado_diarios_total(df_acumulados_diarios):
    """
    Calcula el total acumulado por día para cada estación.
    
    Parámetros:
    - df_acumulados_diarios: DataFrame con los acumulados diarios.
    
    Retorna:
    - DataFrame con los totales por día y la fila 'Total'.
    """
    df = df_acumulados_diarios.copy()
    suma_total = df.sum(axis=0)
    
    df.loc['Total'] = suma_total
    
    return df

def obtener_pluviometros_validos(df_datos):
    """
    Identifica los pluviómetros válidos y no válidos en función de si todos sus valores son NaN.
    
    Parámetros:
    - df_datos: DataFrame con las precipitaciones por pluviómetro.
    
    Retorna:
    - validos: Lista con los pluviómetros válidos.
    - no_validos: Lista con los pluviómetros no válidos.
    """
    validos = []
    no_validos = []

    for col in df_datos.columns:
        if df_datos[col].isna().all():
            no_validos.append(col)
        else:
            validos.append(col)
    
    return validos, no_validos
