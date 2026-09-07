"""
Deteccion y analisis de los eventos de tormenta del mes (seccion 6.2 del informe).
"""
from dataclasses import dataclass

import pandas as pd

from Codigo.Instalador.Funciones_basicas import duracion_tormenta, precipitacion_tr
from Codigo.Instalador.Funciones_exportar import FRECUENCIA, dia_pluviometrico

# Un dia se considera evento de tormenta si algun equipo (o INUMET) supera este acumulado.
UMBRAL_EVENTO = 20

# Duraciones analizadas en la tabla de acumulados maximos, en minutos.
DURACIONES = [10, 20, 30, 60, 120, 180, 360]

# Periodos de retorno que el informe usa como referencia.
TR_REFERENCIA = ['TR 10 años', 'TR 20 años']

# Corte de lluvia sostenida: un hueco mas largo que esto separa dos eventos distintos.
MINUTOS_CORTE = 60

# Fraccion de la lluvia del evento que la ventana tiene que contener. Se recortan las puntas
# de llovizna: despues de una tormenta suele quedar una cola de horas aportando decimas de
# milimetro, que estira la ventana sin ser parte del evento.
CONCENTRACION = 0.99

# Margen a cada lado del dia donde se busca el inicio y el fin de la tormenta, ya que el
# evento no tiene por que quedar contenido en el dia pluviometrico.
HORAS_MARGEN = 12


@dataclass
class Evento:
    """Una tormenta: su ventana temporal y lo que registro cada equipo durante ella."""
    dia: pd.Timestamp             # dia pluviometrico que la contiene
    inicio: pd.Timestamp
    fin: pd.Timestamp
    acumulados: pd.Series         # mm por equipo durante el evento
    maximo_5min: tuple            # (id_equipo, marca_temporal, valor)
    df_5min: pd.DataFrame         # lluvia cada 5 min recortada al evento

    @property
    def duracion_horas(self):
        return round((self.fin - self.inicio).total_seconds() / 3600, 1)

    @property
    def equipo_mas_alto(self):
        return self.acumulados.idxmax()

    @property
    def acumulado_mas_alto(self):
        return round(self.acumulados.max(), 1)

    def etiqueta(self):
        """Como el informe nombra al evento: por el dia calendario en que llovio."""
        return self.inicio.strftime('%d de %B').lower()


def dias_con_evento(datos, descartados=()):
    """
    Identifica los dias del mes que superan el umbral de tormenta.

    Parametros:
    - datos: Instancia de DatosMes.
    - descartados: IDs de equipos excluidos del analisis.

    Retorna:
    - Lista de dias pluviometricos ordenada.
    """
    conservados = [c for c in datos.df_diario.columns if c not in set(descartados)]

    supera_rhm = datos.df_diario[conservados].max(axis=1) > UMBRAL_EVENTO

    supera = supera_rhm
    if datos.inumet is not None:
        supera = supera | (datos.inumet.reindex(datos.df_diario.index).fillna(0) > UMBRAL_EVENTO)

    return list(datos.df_diario.index[supera])


def _redondear_a_media_hora(marca, hacia_arriba):
    """
    Lleva una marca temporal a la media hora, como declara los horarios el informe.

    El inicio se redondea hacia abajo y el fin hacia arriba, siempre a la media hora siguiente
    aunque ya caiga justo, de manera que la ventana declarada cubra el evento entero.
    """
    base = marca.floor('30min')

    return base + pd.Timedelta(minutes=30) if hacia_arriba else base


def ventana_del_evento(datos, dia, descartados=()):
    """
    Busca el inicio y el fin de la lluvia alrededor de un dia con tormenta.

    El evento no se corta en el borde del dia pluviometrico: se toma la racha continua de
    lluvia en la red, permitiendo huecos de hasta MINUTOS_CORTE, y se extiende hacia atras y
    hacia adelante mientras siga lloviendo.

    Parametros:
    - datos: Instancia de DatosMes.
    - dia: Dia pluviometrico con tormenta.
    - descartados: IDs de equipos excluidos del analisis.

    Retorna:
    - Tupla (inicio, fin) redondeada a la media hora.
    """
    conservados = [c for c in datos.df_diario.columns if c not in set(descartados)]

    margen = pd.Timedelta(hours=HORAS_MARGEN)
    desde, hasta = dia - pd.Timedelta(days=1) - margen, dia + margen

    ventana = datos.df_5min.loc[desde:hasta, conservados]
    llueve = ventana.sum(axis=1) > 0

    if not llueve.any():
        return dia - pd.Timedelta(days=1), dia

    # Se agrupan las rachas de lluvia separadas por huecos largos.
    marcas = llueve[llueve].index
    corte = marcas.to_series().diff() > pd.Timedelta(minutes=MINUTOS_CORTE)
    grupo = corte.cumsum()

    # De las rachas que tocan el dia, se elige la que mas lluvia acumulo.
    del_dia = dia_pluviometrico(marcas) == dia
    candidatos = set(grupo[del_dia])
    if not candidatos:
        candidatos = set(grupo)

    lluvia_por_racha = {g: ventana.loc[marcas[grupo == g]].sum().sum() for g in candidatos}
    elegida = max(lluvia_por_racha, key=lluvia_por_racha.get)

    de_la_racha = marcas[grupo == elegida]

    inicio, fin = _recortar_llovizna(ventana.loc[de_la_racha].sum(axis=1))

    return (_redondear_a_media_hora(inicio, hacia_arriba=False),
            _redondear_a_media_hora(fin + pd.Timedelta(FRECUENCIA), hacia_arriba=True))


def _recortar_llovizna(lluvia_de_la_red):
    """
    Recorta las puntas de la racha hasta quedarse con la ventana mas corta que concentra
    CONCENTRACION de la lluvia del evento.

    Parametros:
    - lluvia_de_la_red: Serie con la lluvia sumada de la red por rango de 5 minutos.

    Retorna:
    - Tupla (primera_marca, ultima_marca) del nucleo del evento.
    """
    total = lluvia_de_la_red.sum()
    if total <= 0:
        return lluvia_de_la_red.index.min(), lluvia_de_la_red.index.max()

    objetivo = total * CONCENTRACION

    # Se busca por fuerza bruta la ventana mas corta que alcanza el objetivo. La racha tiene
    # a lo sumo unos cientos de rangos, asi que recorrerla entera no cuesta nada.
    acumulado = lluvia_de_la_red.cumsum()
    marcas = lluvia_de_la_red.index

    mejor = (0, len(marcas) - 1)
    for i in range(len(marcas)):
        previo = acumulado.iloc[i - 1] if i else 0
        for j in range(i, len(marcas)):
            if acumulado.iloc[j] - previo >= objetivo:
                if j - i < mejor[1] - mejor[0]:
                    mejor = (i, j)
                break

    return marcas[mejor[0]], marcas[mejor[1]]


def construir_evento(datos, dia, descartados=()):
    """
    Arma el objeto Evento para un dia con tormenta.

    Parametros:
    - datos: Instancia de DatosMes.
    - dia: Dia pluviometrico con tormenta.
    - descartados: IDs de equipos excluidos del analisis.

    Retorna:
    - Instancia de Evento.
    """
    conservados = [c for c in datos.df_diario.columns if c not in set(descartados)]

    inicio, fin = ventana_del_evento(datos, dia, descartados)

    del_evento = datos.df_5min.loc[inicio:fin - pd.Timedelta(FRECUENCIA), conservados]

    acumulados = del_evento.sum(min_count=1).round(1)

    plano = del_evento.stack()
    if len(plano) and plano.max() > 0:
        marca, equipo = plano.idxmax()
        maximo = (equipo, marca, round(plano.max(), 2))
    else:
        maximo = (None, None, 0.0)

    return Evento(dia=dia, inicio=inicio, fin=fin, acumulados=acumulados,
                  maximo_5min=maximo, df_5min=del_evento)


def detectar_eventos(datos, descartados=()):
    """
    Detecta todos los eventos de tormenta del mes, fusionando los dias contiguos que en
    realidad son la misma tormenta.

    Parametros:
    - datos: Instancia de DatosMes.
    - descartados: IDs de equipos excluidos del analisis.

    Retorna:
    - Lista de Eventos ordenada cronologicamente.
    """
    eventos = []
    for dia in dias_con_evento(datos, descartados):
        evento = construir_evento(datos, dia, descartados)

        # Dos dias seguidos por encima del umbral pueden caer en la misma racha de lluvia.
        if eventos and evento.inicio == eventos[-1].inicio:
            continue

        eventos.append(evento)

    return eventos


def maximos_por_duracion(evento):
    """
    Tabla 6-4/6-6: acumulado maximo de la red para cada duracion de tormenta, junto a los
    valores de referencia de las curvas IDF del IMFIA.

    Parametros:
    - evento: Instancia de Evento.

    Retorna:
    - DataFrame con Duracion, Equipo, P (mm) y una columna por periodo de retorno.
    """
    rangos_por_minuto = int(pd.Timedelta(FRECUENCIA).total_seconds() // 60)

    filas = []
    for duracion in DURACIONES:
        ventanas = max(duracion // rangos_por_minuto, 1)

        acumulado = evento.df_5min.rolling(ventanas, min_periods=1).sum()

        if acumulado.empty or acumulado.max().max() == 0:
            equipo, valor = None, 0.0
        else:
            equipo = acumulado.max().idxmax()
            valor = round(acumulado[equipo].max(), 2)

        fila = {'Duracion (min)': duracion, 'Equipo': equipo, 'P (mm)': valor}

        posicion = duracion_tormenta.index(duracion)
        for tr in TR_REFERENCIA:
            fila[f"{tr.replace(' años', '').replace(' ', '')} (mm)"] = precipitacion_tr[tr][posicion]

        filas.append(fila)

    return pd.DataFrame(filas)


def periodo_de_retorno(valor, duracion):
    """
    Ubica un acumulado medido entre las curvas IDF para estimar su periodo de retorno.

    Parametros:
    - valor: Acumulado medido en mm.
    - duracion: Duracion de la ventana en minutos.

    Retorna:
    - Texto describiendo el periodo de retorno estimado.
    """
    posicion = duracion_tormenta.index(duracion)

    curvas = [(nombre.replace('TR ', '').replace(' años', ''), valores[posicion])
              for nombre, valores in precipitacion_tr.items()]

    anteriores = [anios for anios, referencia in curvas if valor >= referencia]

    if not anteriores:
        return f"inferior a {curvas[0][0]} años"

    if len(anteriores) == len(curvas):
        return f"superior a {curvas[-1][0]} años"

    siguiente = curvas[len(anteriores)][0]

    return f"entre {anteriores[-1]} y {siguiente} años"


def resumen_periodos_de_retorno(tabla_maximos):
    """
    Agrupa las duraciones que comparten periodo de retorno, para redactar la conclusion del
    evento como lo hace el informe.

    Parametros:
    - tabla_maximos: Salida de maximos_por_duracion.

    Retorna:
    - Lista de tuplas (texto_periodo, [duraciones]).
    """
    agrupado = {}
    for _, fila in tabla_maximos.iterrows():
        texto = periodo_de_retorno(fila['P (mm)'], fila['Duracion (min)'])
        agrupado.setdefault(texto, []).append(int(fila['Duracion (min)']))

    return list(agrupado.items())


def acumulado_inumet_del_evento(datos, evento):
    """
    Acumulado de INUMET correspondiente al evento: la suma de sus dias pluviometricos tocados.

    Parametros:
    - datos: Instancia de DatosMes.
    - evento: Instancia de Evento.

    Retorna:
    - Acumulado en mm, o None si no hay datos de INUMET.
    """
    if datos.inumet is None:
        return None

    marcas = pd.date_range(evento.inicio, evento.fin - pd.Timedelta(FRECUENCIA), freq=FRECUENCIA)
    dias = pd.Index(dia_pluviometrico(marcas)).unique()

    return round(datos.inumet.reindex(dias).sum(min_count=1), 1)
