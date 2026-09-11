"""
Armado del borrador en Word del informe pluviometrico mensual.

Reproduce la estructura de los informes de referencia. Las secciones que dependen del trabajo
de campo o de criterio profesional quedan como marcadores [COMPLETAR: ...] para que se
redacten a mano sobre el borrador.
"""
import os

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from Codigo.Informe.datos import nombre_mes
from Codigo.Informe.eventos import resumen_periodos_de_retorno
from Codigo.Instalador.Funciones_mensual import valor_lluvias_historicas

COLOR_PLACEHOLDER = RGBColor(0xC0, 0x00, 0x00)

TEXTO_MANTENIMIENTO = (
    "El mantenimiento de los equipos de medicion es de suma importancia para que los mismos "
    "esten en condiciones de medir con precision todos los eventos de precipitacion y durante "
    "toda la duracion del fenomeno.\n"
    "Las tareas de mantenimiento consisten en la limpieza general del equipo y sus componentes, "
    "y en la verificacion de funcionamiento de cada equipo de medicion, para la cual se vierten "
    "100 mL de agua de forma gradual en un periodo de 5 minutos simulando una lluvia y se toma "
    "la lectura de los valores registrados por el equipo.")

TEXTO_ALCANCE = (
    "El objetivo principal de la Red es obtener datos pluviometricos representativos de todo "
    "Montevideo en tiempo real y de forma confiable.\n"
    "Las estaciones pluviometricas registran datos de lluvias cada 5 minutos; las estaciones "
    "meteorologicas registran lluvia, velocidad y direccion del viento, temperatura, humedad y "
    "presion cada 5 minutos. En este informe solamente se analizaran los registros de lluvia.")

NOTA_DIA_PLUVIOMETRICO = (
    "Los acumulados de la RHM se calculan por dia civil, de 0 a 24 horas. INUMET considera "
    "dias de 7 am a 7 am, por lo que el analisis de precipitacion acumulada (Figura 4-1) y la "
    "tabla de correlacion (Tabla 4-2) usan ese mismo corte para comparar la misma lluvia: alli "
    "el primer dia del mes contiene datos desde las 7 am del ultimo dia del mes anterior.")


class InformeWord:
    """Constructor del borrador en Word."""

    def __init__(self, datos, version):
        self.datos = datos
        self.version = version
        self.doc = Document()
        self.tablas = 0
        self.figuras = 0
        self._configurar_estilos()

    # ---------------------------------------------------------------- utilidades

    def _configurar_estilos(self):
        estilo = self.doc.styles['Normal']
        estilo.font.name = 'Arial'
        estilo.font.size = Pt(11)

    def _pie_de_pagina(self):
        """Pie con el nombre del informe a la izquierda y el numero de pagina a la derecha."""
        pie = self.doc.sections[0].footer.paragraphs[0]
        pie.text = (f"INFORME PLUVIOMETRICO - {nombre_mes(self.datos.mes).upper()} "
                    f"{self.datos.anio} - V{self.version}\t\tPagina | ")
        pie.alignment = WD_ALIGN_PARAGRAPH.LEFT

        # El numero de pagina es un campo de Word, no un texto fijo.
        corrida = pie.add_run()
        for instruccion, atributo in (('begin', None), (None, 'PAGE'), ('end', None)):
            elemento = OxmlElement('w:fldChar') if instruccion else OxmlElement('w:instrText')
            if instruccion:
                elemento.set(qn('w:fldCharType'), instruccion)
            else:
                elemento.set(qn('xml:space'), 'preserve')
                elemento.text = atributo
            corrida._r.append(elemento)

    def titulo(self, texto, nivel):
        self.doc.add_heading(texto, level=nivel)

    def parrafo(self, texto, cursiva=False, tamanio=None):
        p = self.doc.add_paragraph()
        corrida = p.add_run(texto)
        corrida.italic = cursiva
        if tamanio:
            corrida.font.size = Pt(tamanio)
        return p

    def placeholder(self, texto):
        """Marca en rojo una seccion que hay que completar a mano."""
        p = self.doc.add_paragraph()
        corrida = p.add_run(f"[COMPLETAR: {texto}]")
        corrida.bold = True
        corrida.font.color.rgb = COLOR_PLACEHOLDER
        return p

    def vinietas(self, items):
        for item in items:
            self.doc.add_paragraph(str(item), style='List Bullet')

    def tabla(self, df, titulo, incluir_indice=False, indice_titulo=''):
        """Inserta un DataFrame como tabla numerada."""
        self.tablas += 1
        self.parrafo(f"Tabla {self.seccion_tabla}-{self.tablas}: {titulo}", cursiva=True, tamanio=9)

        columnas = ([indice_titulo] if incluir_indice else []) + [str(c) for c in df.columns]
        tabla = self.doc.add_table(rows=1, cols=len(columnas))
        tabla.style = 'Table Grid'

        for celda, encabezado in zip(tabla.rows[0].cells, columnas):
            celda.text = encabezado
            for parrafo in celda.paragraphs:
                for corrida in parrafo.runs:
                    corrida.bold = True
                    corrida.font.size = Pt(8)

        for indice, fila in df.iterrows():
            celdas = tabla.add_row().cells
            valores = ([str(indice)] if incluir_indice else []) + \
                      ['' if v is None else str(v) for v in fila.tolist()]
            for celda, valor in zip(celdas, valores):
                celda.text = valor
                for parrafo in celda.paragraphs:
                    for corrida in parrafo.runs:
                        corrida.font.size = Pt(8)

        self.doc.add_paragraph()

    def figura(self, ruta, titulo, ancho=6.3):
        """Inserta una imagen numerada, si el archivo existe."""
        if not ruta or not os.path.exists(ruta):
            return
        self.figuras += 1
        self.doc.add_picture(ruta, width=Inches(ancho))
        self.doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        p = self.parrafo(f"Figura {self.seccion_figura}-{self.figuras}: {titulo}",
                         cursiva=True, tamanio=9)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    def nueva_seccion(self, numero):
        """Reinicia la numeracion de tablas y figuras al cambiar de seccion."""
        self.seccion_tabla = numero
        self.seccion_figura = numero
        self.tablas = 0
        self.figuras = 0


def _portada(informe):
    doc = informe.doc
    for _ in range(6):
        doc.add_paragraph()

    for texto, tamanio in [("RED HIDROMETRICA DE MONTEVIDEO", 20),
                           ("INFORME PLUVIOMETRICO", 26),
                           (f"{nombre_mes(informe.datos.mes).upper()} {informe.datos.anio}", 22),
                           (f"VERSION {informe.version}", 16)]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        corrida = p.add_run(texto)
        corrida.bold = True
        corrida.font.size = Pt(tamanio)

    doc.add_page_break()


def _indice(informe):
    informe.titulo('Indice', 1)

    p = informe.doc.add_paragraph()
    corrida = p.add_run()
    for instruccion, texto in (('begin', None), (None, 'TOC \\o "1-3" \\h \\z \\u'), ('end', None)):
        elemento = OxmlElement('w:fldChar') if instruccion else OxmlElement('w:instrText')
        if instruccion:
            elemento.set(qn('w:fldCharType'), instruccion)
        else:
            elemento.set(qn('xml:space'), 'preserve')
            elemento.text = texto
        corrida._r.append(elemento)

    informe.parrafo("(Para completar el indice: abrir en Word, click derecho sobre esta linea "
                    "y elegir 'Actualizar campos'.)", cursiva=True, tamanio=9)
    informe.doc.add_page_break()


def _introduccion(informe, rutas_figuras):
    datos = informe.datos
    informe.nueva_seccion(1)
    informe.titulo('1. Introduccion', 1)

    pluviometros = datos.equipos[datos.equipos['Tipo'] != 'SN']
    sensores = datos.equipos[datos.equipos['Tipo'] == 'SN']

    informe.parrafo(
        f"La Red Hidrometeorologica de Montevideo (RHM) cuenta con equipos para medicion y "
        f"analisis de lluvias distribuidos espacialmente en el Departamento.\n"
        f"En la actualidad la RHM cuenta con {len(pluviometros)} equipos de medicion para "
        f"proporcionar informacion de lluvias en Montevideo y {len(sensores)} sensores de "
        f"medicion de niveles en colectores de la red de Saneamiento.\n"
        f"Estos equipos transmiten sus registros de forma remota y en tiempo real a la "
        f"Plataforma Fiware de la IM, permitiendo su visualizacion inmediata mediante la "
        f"aplicacion Grafana.")

    informe.figura(rutas_figuras.get('mapa_red'), 'Red Hidrometeorologica de Montevideo.')

    informe.parrafo("En la Tabla 1-1 se observa la direccion especifica correspondiente para "
                    "cada equipo, donde:")
    informe.vinietas(["EM: Estacion Meteorologica", "P: Estacion Pluviometrica",
                      "PA: Estacion Pluviometrica Anemometrica", "SN: Sensor Nivel"])

    catalogo = datos.equipos[['Lugar', 'ID', 'Tipo', 'Direccion']].fillna('-')
    informe.tabla(catalogo, 'Nomenclatura de equipos y ubicacion correspondiente.')


def _alcance(informe):
    informe.nueva_seccion(2)
    informe.titulo('2. Alcance', 1)
    informe.parrafo(TEXTO_ALCANCE)
    informe.parrafo(
        f"El mismo presenta las tareas realizadas en el mes de "
        f"{nombre_mes(informe.datos.mes)} de {informe.datos.anio}.\n"
        f"Junto al analisis de los datos de lluvia de la RHM se incluye la informacion "
        f"pluviometrica de INUMET, de forma de obtener un mejor analisis.")


def _operativa(informe):
    informe.nueva_seccion(3)
    informe.titulo('3. Operativa y mantenimiento', 1)

    informe.titulo('3.1. Tareas de mantenimiento', 2)
    informe.parrafo(TEXTO_MANTENIMIENTO)
    informe.placeholder("detalle de las tareas de mantenimiento realizadas en el mes")

    informe.titulo('3.2. Relevamiento de campo', 2)
    informe.placeholder("equipos relevados en campo durante el mes y observaciones")

    informe.titulo('3.3. Sustitucion de equipos', 2)
    informe.placeholder("equipos sustituidos en el mes, o 'No se realizaron sustituciones'")


def _calidad(informe, resultados, rutas_figuras):
    datos = informe.datos
    informe.nueva_seccion(4)
    informe.titulo('4. Tareas de gabinete - Analisis de calidad', 1)
    informe.parrafo(f"A continuacion se realiza un analisis exploratorio de los datos recabados "
                    f"en el mes de {nombre_mes(datos.mes)} de {datos.anio}.")

    informe.titulo('4.1. Datos faltantes', 2)
    informe.parrafo(
        "Se indican los pluviometros que son descartados del analisis por presentar datos "
        "faltantes en el registro de precipitacion. El equipo se descarta del analisis si el "
        "registro sin datos en el mes representa mas del 50 % del total de datos.")

    faltantes = resultados['faltantes']
    criticos = faltantes[faltantes['Descartar por faltantes']]
    if len(criticos):
        informe.parrafo("En el mes en cuestion presentan mas del 50 % de datos faltantes: " +
                        ", ".join(f"{f['Lugar']} ({f['ID']}) con {f['Datos faltantes (%)']:.2f} %"
                                  for _, f in criticos.iterrows()) + ".")
    else:
        informe.parrafo("En el mes en cuestion ningun equipo supera el 50 % de datos faltantes.")

    informe.tabla(faltantes[['ID', 'Lugar', 'Datos faltantes (%)']],
                  'Porcentaje de datos faltantes por equipo.')

    informe.titulo('4.2. Analisis de precipitacion acumulada', 2)
    informe.parrafo(
        "El siguiente analisis compara la distribucion de cuantiles de precipitacion entre "
        "INUMET y los acumulados diarios de los pluviometros de la RHM. En el eje horizontal se "
        "muestran los cuantiles del acumulado diario registrado por INUMET y en el eje vertical "
        "los de cada pluviometro de la RHM, de forma que los equipos con buena correlacion se "
        "aproximan a una recta de 45 grados. Para que la comparacion sea directa, en este "
        "analisis los acumulados diarios de la RHM se toman de 7 am a 7 am, como los de INUMET.")

    if rutas_figuras.get('qq'):
        informe.figura(rutas_figuras['qq'],
                       'Analisis de precipitacion acumulada respecto a registros de INUMET.')
    else:
        informe.placeholder("Figura 4-1: requiere los datos de INUMET del mes")

    informe.titulo('4.3. Analisis de correlacion entre pluviometros', 2)
    informe.parrafo("En la Tabla 4-2 se muestra la correlacion existente entre pluviometros y "
                    "con INUMET en el periodo de medicion en cuestion, con dias de 7 am a "
                    "7 am como los de INUMET.")
    informe.tabla(resultados['correlacion'], 'Tabla de correlacion entre pluviometros e INUMET.',
                  incluir_indice=True, indice_titulo='INDICES')

    informe.titulo('4.4. Maximos, minimos, diferencia entre registros sucesivos, anomalos', 2)
    informe.parrafo(
        "Se consideran valores maximos/outliers aquellos registros en los que se superen los "
        "25 mm en un intervalo de medicion de 5 minutos y los que superen los 50 mm en un "
        "intervalo de 10 minutos.")

    anomalos = resultados['outliers']
    if len(anomalos):
        equipos = sorted({f"{f['Lugar']} ({f['ID']})" for _, f in anomalos.iterrows()})
        informe.parrafo(f"En el presente mes presentaron registros anomalos: "
                        f"{', '.join(equipos)}.")
        informe.tabla(anomalos.assign(**{'Fecha y hora': anomalos['Fecha y hora'].dt.strftime(
            '%d-%m-%Y %H:%M')}), 'Registros anomalos detectados en el mes.')
    else:
        informe.parrafo("En el presente mes no se detectaron registros anomalos.")


def _problemas(informe, resultados):
    informe.nueva_seccion(5)
    informe.titulo('5. Problemas identificados', 1)
    informe.parrafo(
        "A partir del analisis de datos anteriormente presentado y del relevamiento realizado "
        "en campo se identifican los siguientes problemas con los equipos, indicando los que "
        "son descartados del analisis de resultados del mes:")

    problemas = resultados['problemas']
    if len(problemas):
        informe.vinietas([
            f"{fila['Lugar']} ({fila['ID']}): {fila['Motivo']} "
            f"{'Se descarta del analisis.' if fila['Descartar'] else 'No se descarta del analisis.'}"
            for _, fila in problemas.iterrows()])

        descartados = problemas[problemas['Descartar']]['Lugar'].tolist()
        if descartados:
            informe.parrafo("En resumen, se descartan de la presentacion de resultados los "
                            "pluviometros " + ", ".join(descartados) + ".")
    else:
        informe.parrafo("No se identificaron problemas en los equipos durante el mes.")

    informe.placeholder("revisar la lista contra el relevamiento de campo y ajustar la decision "
                        "de descarte donde corresponda")


def _resultados(informe, resultados, rutas_figuras):
    datos = informe.datos
    informe.nueva_seccion(6)
    informe.titulo('6. Otros resultados obtenidos', 1)
    informe.parrafo("Para los siguientes analisis de datos se excluyen los equipos mencionados "
                    "en el acapite anterior.")

    informe.titulo('6.1. Acumulados mensuales y diarios', 2)
    informe.parrafo(
        f"En la Tabla 6-1 se muestran los valores de precipitacion acumulada mensual para el mes "
        f"de {nombre_mes(datos.mes)} y en la Figura 6-2 un grafico de barras que representa este "
        f"valor, tanto para RHM como para INUMET. A los efectos de evaluar la magnitud de las "
        f"lluvias acumuladas registradas en el mes, se grafican junto a ellas los cuartiles de "
        f"los valores acumulados historicos de la Estacion del INUMET Prado en el periodo "
        f"1900-2019 (ver Tabla 6-2).")

    acumulados = resultados['acumulados'].to_frame().T.reset_index(drop=True)
    informe.tabla(acumulados, 'Acumulados mensuales en mm, para los equipos de RHM e INUMET.')

    cuartiles = valor_lluvias_historicas(datos.mes)
    import pandas as pd
    informe.tabla(pd.DataFrame([cuartiles], columns=['Primer cuartil', 'Mediana',
                                                     'Tercer cuartil', 'Maximo']),
                  f'Cuartiles precipitacion mes de {nombre_mes(datos.mes)} periodo 1900-2019.')

    informe.parrafo(NOTA_DIA_PLUVIOMETRICO, cursiva=True, tamanio=8)

    informe.figura(rutas_figuras.get('acumulado_mensual'),
                   f'Acumulado mensual correspondiente al mes de {nombre_mes(datos.mes)}.')
    informe.figura(rutas_figuras.get('serie_diaria'),
                   f'Serie temporal de precipitacion acumulada diaria para el mes de '
                   f'{nombre_mes(datos.mes)}.')
    informe.figura(rutas_figuras.get('isoyetas_mes'),
                   f'Isoyetas de precipitacion acumulada para el mes de {nombre_mes(datos.mes)}.')

    informe.titulo('6.2. Eventos de tormenta', 2)

    eventos = resultados['eventos']
    if not eventos:
        informe.parrafo("En el mes no se registraron eventos que superaran los 20 mm de lluvia "
                        "acumulada.")
        return

    dias = " y ".join(str(e['evento'].inicio.day) for e in eventos)
    informe.parrafo(
        f"Tomando como referencia los valores diarios publicados por INUMET y los propios de la "
        f"RHM, en el mes de {nombre_mes(datos.mes)} de {datos.anio} se presentaron "
        f"{len(eventos)} evento(s) los dias {dias}, que superaron los 20 mm de lluvia acumulada.")

    for numero, resultado in enumerate(eventos, 1):
        _evento(informe, numero, resultado, rutas_figuras)


def _evento(informe, numero, resultado, rutas_figuras):
    evento = resultado['evento']
    maximos = resultado['maximos']
    mes_evento = nombre_mes(evento.inicio.month)

    informe.titulo(f'6.2.{numero}. Evento del {evento.inicio.day} de {mes_evento}', 3)

    informe.parrafo(
        f"El evento de tormenta tuvo lugar el {evento.inicio.strftime('%d de ')}{mes_evento} de "
        f"{evento.inicio.year}, inicio a las {evento.inicio.strftime('%H:%M')} culminando a las "
        f"{evento.fin.strftime('%H:%M')}, teniendo una duracion de {evento.duracion_horas} horas.")

    equipo, marca, valor = evento.maximo_5min
    if equipo:
        # El informe nombra el rango de 5 minutos por su hora de cierre.
        import pandas as pd
        cierre = (marca + pd.Timedelta(minutes=5)).strftime('%H:%M')
        informe.parrafo(
            f"El valor maximo registrado en un intervalo de 5 minutos de medicion se dio en el "
            f"pluviometro {informe.datos.nombre_de(equipo)} ({equipo}) a las {cierre}, cuyo "
            f"valor es de {valor} mm.")

    informe.figura(rutas_figuras.get(f'hietograma_{numero}'), 'Hietograma de tormenta.')

    acumulados = evento.acumulados.to_frame().T.reset_index(drop=True)
    if resultado.get('inumet') is not None:
        acumulados['INUMET'] = resultado['inumet']
    informe.tabla(acumulados, 'Acumulados de la tormenta para la RHM e INUMET. Valores en mm.')

    informe.parrafo(
        f"El valor maximo alcanzado se registro en el pluviometro "
        f"{informe.datos.nombre_de(evento.equipo_mas_alto)} ({evento.equipo_mas_alto}), tomando "
        f"un valor de {evento.acumulado_mas_alto} mm.")

    informe.figura(rutas_figuras.get(f'acumulada_{numero}'),
                   'Precipitacion acumulada de la tormenta.')
    informe.figura(rutas_figuras.get(f'isoyetas_evento_{numero}'),
                   f'Distribucion espacial de la tormenta del dia {evento.inicio.day} de '
                   f'{mes_evento}.')

    informe.parrafo(
        "La siguiente tabla muestra los maximos registrados para distintas duraciones de "
        "tormenta y en que equipo se registro este valor, considerando todos los pluviometros "
        "de la red. A su vez, se muestran los valores de referencia de las Curvas de "
        "Intensidad - Duracion - Frecuencia del Instituto de Mecanica de los Fluidos e "
        "Ingenieria Ambiental (IMFIA).")

    con_nombre = maximos.copy()
    con_nombre['Equipo'] = con_nombre['Equipo'].map(
        lambda e: informe.datos.nombre_de(e) if e else '-')
    informe.tabla(con_nombre, 'Acumulados maximos para distintas duraciones de la tormenta.')

    informe.figura(rutas_figuras.get(f'tr_{numero}'),
                   'Intensidad de precipitacion para distintos periodos de retorno.')

    partes = [f"{texto} para duraciones de {', '.join(str(d) for d in duraciones)} minutos"
              for texto, duraciones in resumen_periodos_de_retorno(maximos)]
    informe.parrafo(f"El periodo de retorno de la tormenta es {'; '.join(partes)}.")

    informe.placeholder("interpretacion de la distribucion espacial del evento (en que zona del "
                        "departamento se concentro)")


def _evaluacion(informe, resultados):
    informe.nueva_seccion(7)
    informe.titulo('7. Evaluacion del funcionamiento de la red', 1)

    dia, equipo, valor = resultados['dia_maximo']
    bien, total, porcentaje = resultados['indicador']
    evaluacion = resultados['evaluacion']
    mes_dia = nombre_mes(dia.month)

    informe.parrafo(
        f"Con el fin de evaluar el funcionamiento de los equipos de medicion de la RHM se "
        f"considera el dia de {nombre_mes(informe.datos.mes)} con mayor precipitacion y el "
        f"porcentaje de equipos que reportaron de forma optima durante ese dia.")

    informe.parrafo(
        f"El dia con mayor precipitacion acumulada en el mes se registro el {dia.day} de "
        f"{mes_dia} ({valor} mm en {informe.datos.nombre_de(equipo)}), por lo tanto el presente "
        f"analisis se realiza en base a este dia.")

    informe.parrafo(
        f"De los {total} equipos que componen la RHM, {bien} presentaron un registro de datos "
        f"completo y confiable de precipitacion durante el evento. Por lo tanto, el indicador de "
        f"evaluacion de funcionamiento para el dia de mayor precipitacion es de {bien} equipos "
        f"con datos completos sobre {total} equipos disponibles, es decir un {porcentaje} %.")

    correctos = evaluacion[evaluacion['Lectura'] == 'Bien'][['Lugar']].reset_index(drop=True)
    correctos.insert(0, 'Numero', range(1, len(correctos) + 1))
    informe.tabla(correctos, f'Listado de estaciones que registraron correctamente la '
                             f'precipitacion del {dia.day} de {mes_dia}.')
    informe.parrafo("(*) La numeracion es solamente para facilitar el recuento de las "
                    "estaciones, no corresponde al ID de cada una.", cursiva=True, tamanio=8)

    informe.tabla(evaluacion, 'Analisis del registro de medicion de cada uno de los equipos.')


def _cierre(informe):
    informe.nueva_seccion(8)
    informe.titulo('8. Recomendaciones para el proximo mes', 1)
    informe.placeholder("recomendaciones a partir de los problemas identificados y del "
                        "relevamiento de campo")

    informe.doc.add_page_break()
    informe.nueva_seccion(9)
    informe.titulo('9. Anexo I', 1)
    informe.placeholder("ficha de inspeccion de relevamiento de campo por equipo")


def generar(datos, resultados, rutas_figuras, ruta_salida, version=1):
    """
    Arma el borrador del informe en Word.

    Parametros:
    - datos: Instancia de DatosMes.
    - resultados: Diccionario con las tablas calculadas por generar_informe.py.
    - rutas_figuras: Diccionario nombre -> ruta del PNG de cada figura.
    - ruta_salida: Ruta del .docx a escribir.
    - version: Numero de version del informe.

    Retorna:
    - Ruta del archivo generado.
    """
    informe = InformeWord(datos, version)
    informe._pie_de_pagina()

    _portada(informe)
    _indice(informe)
    _introduccion(informe, rutas_figuras)
    _alcance(informe)
    _operativa(informe)
    _calidad(informe, resultados, rutas_figuras)
    _problemas(informe, resultados)
    _resultados(informe, resultados, rutas_figuras)
    _evaluacion(informe, resultados)
    _cierre(informe)

    informe.doc.save(ruta_salida)

    return ruta_salida
