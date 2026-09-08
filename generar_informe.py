"""
Genera el informe pluviometrico mensual completo a partir del CSV crudo de Fiware/Grafana.

Uso:
    python generar_informe.py --mes 8 --anio 2026 --version 1
    python generar_informe.py --mes 8 --anio 2026 --crudo "ruta/al/crudo.csv"
    python generar_informe.py --mes 8 --anio 2026 --dry-run

Deja en outputs/{anio}-{mes}/ los dos CSV refinados, las tablas del informe en CSV, las
figuras en PNG y el borrador del informe en Word.
"""
import argparse
import json
import os
import sys

import matplotlib
matplotlib.use('Agg')          # Sin ventana: el pipeline corre fuera de la app.
import pandas as pd
from matplotlib import pyplot as plt

from Codigo.Informe import analisis, documento, eventos, figuras
from Codigo.Informe.datos import cargar_mes, nombre_mes, ruta_plantilla_inumet
from Codigo.Instalador.Funciones_basicas import eliminar_tildes
from Codigo.Instalador.Funciones_exportar import (dia_pluviometrico, escribir_csvs,
                                                  leer_datos_crudos, limpiar_caidas_espurias)

# Carpeta donde vive el pipeline, para poder correrlo desde cualquier directorio.
CARPETA_BASE = os.path.dirname(os.path.abspath(__file__))

ARCHIVO_CONFIG = os.path.join(CARPETA_BASE, 'config_informe.json')

RUTAS_POR_DEFECTO = {
    'crudos': 'data/raw',
    'inumet': 'data/inumet',
    'salida': 'outputs',
}


def cargar_config():
    """
    Lee las rutas de trabajo de config_informe.json.

    Sirve para dejar fijas de una vez las carpetas del equipo (por ejemplo las del drive
    compartido) y no tener que escribirlas en cada corrida. Lo que falte en el archivo toma el
    valor por defecto, y las opciones de linea de comandos siempre mandan por encima.

    Retorna:
    - Diccionario con las claves 'crudos', 'inumet' y 'salida'.
    """
    rutas = dict(RUTAS_POR_DEFECTO)

    if os.path.exists(ARCHIVO_CONFIG):
        with open(ARCHIVO_CONFIG, encoding='utf-8') as archivo:
            rutas.update({k: v for k, v in json.load(archivo).items() if k in rutas and v})

    # Las rutas relativas se resuelven contra la carpeta del pipeline, no contra el directorio
    # desde el que se ejecuta, para que el comando funcione igual desde cualquier lado.
    return {clave: valor if os.path.isabs(valor) else os.path.join(CARPETA_BASE, valor)
            for clave, valor in rutas.items()}


def ruta_crudo_por_defecto(carpeta_crudos, anio, mes):
    return os.path.join(carpeta_crudos, f'{anio}-{mes:02d}.csv')


def validar_contra_crudo(datos):
    """
    Comprueba que el acumulado diario cierre contra el CSV crudo original.

    Recalcula el total de cada equipo directamente sobre las lecturas crudas, sin pasar por la
    grilla de 5 minutos, y lo compara contra la suma de la tabla diaria. Si las dos cuentas no
    coinciden, la logica de diferencias del paso 1 tiene un problema.

    Parametros:
    - datos: Instancia de DatosMes.

    Retorna:
    - DataFrame con la comparacion por equipo.
    """
    crudo = leer_datos_crudos(datos.archivo_crudo)

    inicio = datos.df_5min.index.min()
    fin = datos.df_5min.index.max() + pd.Timedelta('5min')

    descartado_por_equipo = (datos.df_descartes.groupby('ID')['Valor descartado (mm)'].sum()
                             if 'ID' in datos.df_descartes else pd.Series(dtype=float))

    # El catalogo guarda los lugares sin tildes y el CSV crudo los trae con tildes.
    mapa = {eliminar_tildes(lugar): identificador for lugar, identificador
            in zip(datos.equipos['Lugar'], datos.equipos['ID'])}

    filas = []
    for lugar in crudo.columns:
        identificador = mapa.get(eliminar_tildes(lugar), lugar)
        if identificador not in datos.df_diario.columns:
            continue

        serie = crudo[lugar].dropna()
        serie = serie[(serie.index >= inicio) & (serie.index < fin)]
        serie = limpiar_caidas_espurias(serie)

        # Misma cuenta que el paso 1 pero sin la grilla: diferencias positivas dentro del dia.
        crudo_total = (serie.groupby(dia_pluviometrico(serie.index)).diff()
                       .fillna(0).clip(lower=0).sum())

        tabla_total = datos.df_diario[identificador].sum(min_count=1)
        descartado = float(descartado_por_equipo.get(identificador, 0.0))

        filas.append({
            'ID': identificador,
            'Lugar': lugar,
            'Total desde el crudo (mm)': round(crudo_total, 2),
            'Descartado por outlier (mm)': round(descartado, 2),
            'Total tabla diaria (mm)': round(tabla_total, 2),
            'Diferencia (mm)': round(crudo_total - descartado - tabla_total, 2),
        })

    return pd.DataFrame(filas)


def cargar_o_crear(ruta, df_candidato, descripcion):
    """
    Devuelve la version editada por el operario si el archivo ya existe, o crea el candidato.

    Este es el mecanismo de override: el pipeline propone y el operario corrige el CSV antes
    de la corrida final. Nunca se pisa un archivo existente.

    Parametros:
    - ruta: Ruta del CSV editable.
    - df_candidato: Propuesta automatica.
    - descripcion: Texto para el mensaje en consola.

    Retorna:
    - Tupla (DataFrame vigente, fue_editado_a_mano).
    """
    if os.path.exists(ruta):
        print(f"  usando {descripcion} editado a mano: {os.path.basename(ruta)}")
        return pd.read_csv(ruta, encoding='utf-8-sig'), True

    df_candidato.to_csv(ruta, index=False, encoding='utf-8-sig')
    print(f"  {descripcion} sugerido escrito en {os.path.basename(ruta)} (editable)")

    return df_candidato, False


def guardar_figura(fig, carpeta, nombre):
    """Guarda una figura como PNG y la cierra. Devuelve la ruta, o None si no habia figura."""
    if fig is None:
        return None

    ruta = os.path.join(carpeta, f'{nombre}.png')
    fig.savefig(ruta, dpi=200, bbox_inches='tight')
    plt.close(fig)

    return ruta


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--mes', type=int, required=True, help='Numero de mes (1-12)')
    parser.add_argument('--anio', type=int, required=True, help='Anio del informe')
    parser.add_argument('--version', type=int, default=1, help='Version del informe (default 1)')
    parser.add_argument('--crudo', help='CSV crudo. Por defecto <crudos>/{anio}-{mes}.csv')
    parser.add_argument('--inumet', help='Carpeta con los CSV de INUMET')
    parser.add_argument('--salida', help='Carpeta raiz de salida')
    parser.add_argument('--dry-run', action='store_true',
                        help='Solo valida los calculos contra el CSV crudo, no escribe el informe')
    args = parser.parse_args()

    rutas = cargar_config()
    carpeta_inumet = args.inumet or rutas['inumet']
    carpeta_salida = args.salida or rutas['salida']

    archivo = args.crudo or ruta_crudo_por_defecto(rutas['crudos'], args.anio, args.mes)
    if not os.path.exists(archivo):
        sys.exit(f"No se encuentra el CSV crudo: {archivo}\n"
                 f"Pasalo con --crudo, o dejalo en esa ruta, o cambia la carpeta 'crudos' en "
                 f"{os.path.basename(ARCHIVO_CONFIG)}")

    carpeta = os.path.join(carpeta_salida, f'{args.anio}-{args.mes:02d}')
    os.makedirs(carpeta, exist_ok=True)

    print(f"\nInforme pluviometrico de {nombre_mes(args.mes)} {args.anio} (V{args.version})")
    print(f"  crudo:  {archivo}")
    print(f"  salida: {carpeta}")

    datos = cargar_mes(archivo, args.anio, args.mes,
                       carpeta_base=CARPETA_BASE, carpeta_inumet=carpeta_inumet)
    print(f"  exportado de Grafana el {datos.exportado}")
    print(f"  {datos.df_diario.shape[1]} equipos, {len(datos.df_diario)} dias, "
          f"{len(datos.df_5min)} rangos de 5 min")

    # ---------------------------------------------------------------- validacion
    print("\nValidacion del acumulado diario contra el CSV crudo:")
    control = validar_contra_crudo(datos)
    peor = control['Diferencia (mm)'].abs().max()
    print(control.to_string(index=False))
    print(f"\n  diferencia maxima: {peor:.2f} mm", "OK" if peor < 0.05 else "<-- REVISAR")

    if args.dry_run:
        control.to_csv(os.path.join(carpeta, 'validacion_contra_crudo.csv'),
                       index=False, encoding='utf-8-sig')
        print(f"\nDry-run: no se genero el informe. Validacion en {carpeta}")
        return 0 if peor < 0.05 else 1

    if datos.inumet is None:
        print(f"\n  AVISO: falta completar {ruta_plantilla_inumet(carpeta_inumet, args.anio, args.mes)}")
        print("         El informe se genera igual, con las partes de INUMET marcadas.")

    # ---------------------------------------------------------------- CSV refinados
    print("\nCSV refinados:")
    for ruta in escribir_csvs(datos.df_5min, datos.df_diario, carpeta):
        print(f"  {os.path.basename(ruta)}")

    # ---------------------------------------------------------------- analisis
    print("\nAnalisis:")
    faltantes = analisis.datos_faltantes(datos)
    correlacion = analisis.matriz_correlacion(datos)
    anomalos = analisis.outliers(datos)

    problemas, editado = cargar_o_crear(
        os.path.join(carpeta, f'problemas_{datos.etiqueta_archivo}.csv'),
        analisis.problemas_identificados(datos), 'listado de problemas')

    descartados = problemas[problemas['Descartar'].astype(str).str.lower()
                            .isin(['true', 'si', 'sí', '1'])]['ID'].tolist()
    print(f"  equipos descartados: {', '.join(descartados) if descartados else 'ninguno'}")

    acumulados = analisis.acumulados_mensuales(datos, descartados)
    dia_maximo = analisis.dia_de_mayor_precipitacion(datos, descartados)
    evaluacion = analisis.evaluacion_de_la_red(datos, dia_maximo[0])
    indicador = analisis.indicador_de_funcionamiento(evaluacion)
    print(f"  dia de mayor precipitacion: {dia_maximo[0].strftime('%d-%m-%Y')} "
          f"({dia_maximo[2]} mm en {dia_maximo[1]})")
    print(f"  indicador de funcionamiento: {indicador[0]}/{indicador[1]} = {indicador[2]} %")

    detectados = eventos.detectar_eventos(datos, descartados)
    print(f"  eventos de tormenta: {len(detectados)}")

    # ---------------------------------------------------------------- figuras
    print("\nFiguras:")
    rutas = {
        'mapa_red': guardar_figura(figuras.mapa_de_la_red(datos, CARPETA_BASE), carpeta, 'fig_1-1_red'),
        'qq': guardar_figura(figuras.qq_contra_inumet(datos, descartados), carpeta,
                             'fig_4-1_qq_inumet'),
        'acumulado_mensual': guardar_figura(figuras.acumulado_mensual(datos, acumulados),
                                            carpeta, 'fig_6-1_acumulado_mensual'),
        'serie_diaria': guardar_figura(figuras.serie_diaria(datos, descartados), carpeta,
                                       'fig_6-2_serie_diaria'),
        'isoyetas_mes': guardar_figura(figuras.isoyetas_mensuales(datos, acumulados, CARPETA_BASE),
                                       carpeta, 'fig_6-3_isoyetas_mes'),
    }

    resultados_eventos = []
    for numero, evento in enumerate(detectados, 1):
        maximos = eventos.maximos_por_duracion(evento)
        resultados_eventos.append({
            'evento': evento,
            'maximos': maximos,
            'inumet': eventos.acumulado_inumet_del_evento(datos, evento),
        })
        rutas[f'hietograma_{numero}'] = guardar_figura(
            figuras.hietograma(evento), carpeta, f'fig_6-4_hietograma_evento{numero}')
        rutas[f'acumulada_{numero}'] = guardar_figura(
            figuras.acumulada_del_evento(evento), carpeta, f'fig_6-5_acumulada_evento{numero}')
        rutas[f'isoyetas_evento_{numero}'] = guardar_figura(
            figuras.isoyetas_del_evento(datos, evento, CARPETA_BASE), carpeta,
            f'fig_6-6_isoyetas_evento{numero}')
        rutas[f'tr_{numero}'] = guardar_figura(
            figuras.intensidad_vs_tr(maximos), carpeta, f'fig_6-7_tr_evento{numero}')
        maximos.to_csv(os.path.join(carpeta, f'tabla_6-4_maximos_evento{numero}.csv'),
                       index=False, encoding='utf-8-sig')

    for nombre, ruta in rutas.items():
        print(f"  {'OK ' if ruta else '-- '} {nombre}")

    # ---------------------------------------------------------------- tablas
    faltantes.to_csv(os.path.join(carpeta, 'tabla_4-1_datos_faltantes.csv'),
                     index=False, encoding='utf-8-sig')
    correlacion.to_csv(os.path.join(carpeta, 'tabla_4-2_correlacion.csv'), encoding='utf-8-sig')
    anomalos.to_csv(os.path.join(carpeta, 'tabla_4-3_outliers.csv'),
                    index=False, encoding='utf-8-sig')
    acumulados.to_frame('mm').to_csv(os.path.join(carpeta, 'tabla_6-1_acumulados_mensuales.csv'),
                                     encoding='utf-8-sig')
    evaluacion.to_csv(os.path.join(carpeta, 'tabla_7-2_evaluacion_red.csv'),
                      index=False, encoding='utf-8-sig')
    control.to_csv(os.path.join(carpeta, 'validacion_contra_crudo.csv'),
                   index=False, encoding='utf-8-sig')

    # ---------------------------------------------------------------- Word
    resultados = {
        'faltantes': faltantes, 'correlacion': correlacion, 'outliers': anomalos,
        'problemas': problemas, 'acumulados': acumulados, 'eventos': resultados_eventos,
        'dia_maximo': dia_maximo, 'evaluacion': evaluacion, 'indicador': indicador,
    }

    nombre_docx = (f'INFORME PLUVIOMETRICO - {nombre_mes(args.mes).upper()} '
                   f'{args.anio} - V{args.version}.docx')
    ruta_docx = documento.generar(datos, resultados, rutas,
                                  os.path.join(carpeta, nombre_docx), args.version)

    print(f"\nListo. Borrador en:\n  {ruta_docx}")
    print("\nFalta completar a mano: seccion 3 (operativa), la decision final de la seccion 5, "
          "seccion 8 (recomendaciones) y el Anexo I.")

    return 0


if __name__ == '__main__':
    sys.exit(main())
