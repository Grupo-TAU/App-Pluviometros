"""
Genera los dos CSV refinados a partir del CSV crudo de Grafana, sin abrir la interfaz.

Uso:
    python exportar_csv.py "Precipitaciones - Acumulado diario-data-07-09-2026 09_22_32.csv" [carpeta_destino]
"""
import os
import sys

from Codigo.Instalador.Funciones_exportar import exportar_csvs

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    archivo = sys.argv[1]
    carpeta_destino = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(os.path.abspath(archivo))

    for ruta in exportar_csvs(archivo, carpeta_destino):
        print(f"Generado: {ruta}")
