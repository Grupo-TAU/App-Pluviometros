"""
Carga y preparacion de los datos que alimentan el informe pluviometrico mensual.

Reune en un solo objeto todo lo que las demas etapas necesitan: las dos tablas refinadas
(acumulados cada 5 minutos y acumulado diario), la cobertura real de cada equipo, el catalogo
de equipos y los acumulados diarios de INUMET.
"""
import os
import calendar
from dataclasses import dataclass, field

import pandas as pd

from Codigo.Instalador.Funciones_basicas import eliminar_tildes
from Codigo.Instalador.Funciones_exportar import (
    FRECUENCIA, HORA_CORTE, calcular_acumulados_5min, calcular_acumulados_diarios_corte,
    descartar_outliers, dia_pluviometrico, leer_datos_crudos)

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
         "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

# Equipos que no miden lluvia y por lo tanto no entran en ningun analisis.
TIPO_SENSOR_NIVEL = 'SN'


def nombre_mes(numero_mes):
    """Devuelve el nombre en espanol del mes indicado (1-12)."""
    return MESES[numero_mes - 1]


@dataclass
class DatosMes:
    """Todo lo que el informe necesita saber del mes procesado."""
    anio: int
    mes: int
    archivo_crudo: str
    exportado: str                    # fecha de modificacion del CSV crudo
    df_5min: pd.DataFrame             # acumulados cada 5 min, columnas = ID de equipo
    df_diario: pd.DataFrame           # acumulados diarios, columnas = ID de equipo
    df_cobertura: pd.DataFrame        # True si el rango de 5 min tuvo al menos una lectura
    df_descartes: pd.DataFrame        # rangos descartados por outlier
    equipos: pd.DataFrame             # catalogo Lugar/ID/Tipo/Direccion/X/Y
    inumet: pd.Series = field(default=None)   # acumulado diario de INUMET, indexado por dia

    @property
    def etiqueta(self):
        return f"{nombre_mes(self.mes)} {self.anio}"

    @property
    def etiqueta_archivo(self):
        return f"{self.anio}-{self.mes:02d}"

    def nombre_de(self, identificador):
        """Traduce un ID de equipo a su nombre de lugar."""
        fila = self.equipos[self.equipos['ID'] == identificador]
        return fila['Lugar'].iloc[0] if len(fila) else identificador

    def diario_con_inumet(self):
        """Acumulado diario con la columna INUMET agregada, si esta disponible."""
        df = self.df_diario.copy()
        if self.inumet is not None:
            df['INUMET'] = self.inumet.reindex(df.index)
        return df


def cargar_equipos(carpeta_base='.'):
    """
    Lee el catalogo de equipos (Tabla 1-1 del informe) y le pega las coordenadas UTM.

    Parametros:
    - carpeta_base: Carpeta donde viven Equipos_RHM.csv y Coordenadas_Equipos.csv.

    Retorna:
    - DataFrame con Lugar, ID, Tipo, Direccion, X, Y.
    """
    equipos = pd.read_csv(os.path.join(carpeta_base, 'Equipos_RHM.csv'), encoding='utf-8')
    equipos['Lugar'] = equipos['Lugar'].apply(eliminar_tildes)

    ruta_coord = os.path.join(carpeta_base, 'Coordenadas_Equipos.csv')
    if os.path.exists(ruta_coord):
        coord = pd.read_csv(ruta_coord, encoding='utf-8')
        coord['Lugar'] = coord['Lugar'].apply(eliminar_tildes)
        equipos = equipos.merge(coord, on='Lugar', how='left')
    else:
        equipos['X'] = pd.NA
        equipos['Y'] = pd.NA

    return equipos


def equipos_pluviometricos(equipos):
    """Filtra el catalogo dejando solo los equipos que miden lluvia."""
    return equipos[(equipos['Tipo'] != TIPO_SENSOR_NIVEL) & equipos['ID'].notna()]


def traducir_a_ids(df, equipos):
    """
    Renombra las columnas de lugar a ID de equipo, que es como el informe nombra a los
    pluviometros en todas sus tablas.

    Parametros:
    - df: DataFrame con una columna por pluviometro, nombradas por lugar.
    - equipos: Catalogo de equipos.

    Retorna:
    - DataFrame con las columnas renombradas a ID.
    """
    mapa = {eliminar_tildes(lugar): identificador
            for lugar, identificador in zip(equipos['Lugar'], equipos['ID'])
            if pd.notna(identificador)}

    return df.rename(columns={col: mapa.get(eliminar_tildes(col), col) for col in df.columns})


def calcular_cobertura(df_crudo, grilla):
    """
    Marca, para cada equipo y cada rango de 5 minutos, si hubo al menos una lectura cruda.

    Hace falta como tabla aparte porque en la tabla de acumulados un rango sin lectura vale 0
    igual que un rango con lectura pero sin lluvia. Para medir datos faltantes hay que poder
    distinguirlos.

    Parametros:
    - df_crudo: Lecturas crudas del CSV de Grafana.
    - grilla: DatetimeIndex con los rangos de 5 minutos del mes.

    Retorna:
    - DataFrame booleano con la misma forma que la tabla de acumulados.
    """
    cobertura = pd.DataFrame(False, index=grilla, columns=df_crudo.columns)

    for pluvio in df_crudo.columns:
        marcas = df_crudo[pluvio].dropna().index.floor(FRECUENCIA)
        cobertura.loc[cobertura.index.isin(marcas), pluvio] = True

    return cobertura


def ruta_plantilla_inumet(carpeta_inumet, anio, mes):
    """Ruta del CSV de INUMET correspondiente al mes."""
    return os.path.join(carpeta_inumet, f'INUMET_{anio}-{mes:02d}.csv')


def crear_plantilla_inumet(carpeta_inumet, anio, mes, dias):
    """
    Deja un CSV vacio con un renglon por dia para que se complete a mano con los datos que
    publica INUMET.

    Parametros:
    - carpeta_inumet: Carpeta donde se guardan los CSV de INUMET.
    - anio, mes: Mes del informe.
    - dias: DatetimeIndex con los dias pluviometricos del mes.

    Retorna:
    - Ruta del archivo creado.
    """
    os.makedirs(carpeta_inumet, exist_ok=True)
    ruta = ruta_plantilla_inumet(carpeta_inumet, anio, mes)

    plantilla = pd.DataFrame({'FECHA': [d.strftime('%d/%m/%Y') for d in dias], 'INUMET': ''})
    plantilla.to_csv(ruta, index=False, encoding='utf-8-sig')

    return ruta


def leer_inumet(ruta, dias):
    """
    Lee el CSV de INUMET del mes.

    Parametros:
    - ruta: Ruta del CSV con columnas FECHA e INUMET.
    - dias: DatetimeIndex de los dias pluviometricos del mes.

    Retorna:
    - Serie de acumulados diarios indexada por dia, o None si el archivo esta sin completar.
    """
    df = pd.read_csv(ruta, encoding='utf-8-sig')

    columnas = {c.strip().upper(): c for c in df.columns}
    if 'FECHA' not in columnas or 'INUMET' not in columnas:
        raise ValueError(f"{ruta} debe tener las columnas FECHA e INUMET.")

    df = df.rename(columns={columnas['FECHA']: 'FECHA', columnas['INUMET']: 'INUMET'})
    df['INUMET'] = pd.to_numeric(df['INUMET'], errors='coerce')

    if df['INUMET'].isna().all():
        return None  # Plantilla sin completar.

    df['FECHA'] = pd.to_datetime(df['FECHA'], dayfirst=True, errors='coerce')

    return df.dropna(subset=['FECHA']).set_index('FECHA')['INUMET'].reindex(dias)


def cargar_mes(archivo_crudo, anio, mes, carpeta_base='.', carpeta_inumet=None):
    """
    Procesa el CSV crudo del mes y arma el objeto DatosMes con todo lo necesario.

    Parametros:
    - archivo_crudo: Ruta del CSV exportado de Fiware/Grafana.
    - anio, mes: Mes del informe.
    - carpeta_base: Carpeta con los catalogos (Equipos_RHM.csv, Coordenadas_Equipos.csv).
    - carpeta_inumet: Carpeta con los CSV de INUMET. Si es None no se carga INUMET.

    Retorna:
    - Instancia de DatosMes.
    """
    df_crudo = leer_datos_crudos(archivo_crudo)

    df_5min, df_descartes = descartar_outliers(calcular_acumulados_5min(df_crudo))
    df_diario = calcular_acumulados_diarios_corte(df_5min)

    detectado = df_diario.index[0]
    if (detectado.year, detectado.month) != (anio, mes):
        raise ValueError(
            f"El archivo contiene datos de {nombre_mes(detectado.month)} {detectado.year} "
            f"pero se pidio el informe de {nombre_mes(mes)} {anio}.")

    df_cobertura = calcular_cobertura(df_crudo, df_5min.index)

    equipos = cargar_equipos(carpeta_base)

    df_5min = traducir_a_ids(df_5min, equipos)
    df_diario = traducir_a_ids(df_diario, equipos)
    df_cobertura = traducir_a_ids(df_cobertura, equipos)
    if not df_descartes.empty:
        mapa = dict(zip(equipos['Lugar'].apply(eliminar_tildes), equipos['ID']))
        df_descartes = df_descartes.assign(
            ID=df_descartes['Pluviometro'].apply(lambda p: mapa.get(eliminar_tildes(p), p)))

    datos = DatosMes(
        anio=anio, mes=mes,
        archivo_crudo=archivo_crudo,
        exportado=pd.Timestamp(os.path.getmtime(archivo_crudo), unit='s').strftime('%d-%m-%Y %H:%M'),
        df_5min=df_5min, df_diario=df_diario, df_cobertura=df_cobertura,
        df_descartes=df_descartes, equipos=equipos)

    if carpeta_inumet is not None:
        ruta = ruta_plantilla_inumet(carpeta_inumet, anio, mes)
        if not os.path.exists(ruta):
            crear_plantilla_inumet(carpeta_inumet, anio, mes, df_diario.index)
        else:
            datos.inumet = leer_inumet(ruta, df_diario.index)

    return datos
