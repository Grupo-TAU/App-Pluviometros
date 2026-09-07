# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

BASE_DIR = Path(SPECPATH)

a = Analysis(
    ['main.py'],
    pathex=[str(BASE_DIR)],
    binaries=[],
    datas=[
        (str(BASE_DIR / 'precipitacion.ico'), '.'),
        (str(BASE_DIR / 'MONTEVIDEO.png'), '.'),
        (str(BASE_DIR / 'Logo_Grupo_Tau.png'), '.'),
        (str(BASE_DIR / 'Logo_imm.jpg'), '.'),
        (str(BASE_DIR / 'Logo_Dica.png'), '.'),
        (str(BASE_DIR / 'Coordenadas_Equipos.csv'), '.'),
        (str(BASE_DIR / 'Lugares-ID.csv'), '.'),
    ],
    # pandas importa openpyxl recien cuando lee un Excel, asi que PyInstaller no lo detecta solo.
    hiddenimports=['openpyxl'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # PyInstaller empaqueta todo lo que matplotlib y pandas *podrian* llegar a usar, no solo lo
    # que esta app usa. Sin estos excludes el instalador se lleva ~79 MB de Qt (la app corre
    # sobre tkinter) y ~81 MB de pyarrow con conectores de base de datos, que solo hacen falta
    # para leer Parquet o hablar con un motor SQL. Verificado que la app corre sin todo esto.
    excludes=[
        # Toolkits graficos: la interfaz es tkinter
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
        'matplotlib.backends.backend_qt5agg',
        'matplotlib.backends.backend_qtagg',
        'matplotlib.backends.backend_webagg',
        'PIL.ImageQt',
        # Formatos y motores de datos que la app no abre: solo lee CSV y Excel
        'pyarrow',
        'sqlalchemy',
        'psycopg2',
        'cryptography',
        'PIL.AvifImagePlugin',
        # Librerias cientificas y de desarrollo que no se usan
        'pyproj',          # reemplazado por latlon_a_utm21s en Funciones_basicas
        'scipy',
        'IPython',
        'jupyter',
        'notebook',
        'pytest',
        # Ojo: 'unittest' NO se puede excluir. pyparsing.testing lo importa, y matplotlib
        # importa pyparsing, asi que sacarlo hace que el .exe no arranque.
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(BASE_DIR / 'precipitacion.ico'),
)