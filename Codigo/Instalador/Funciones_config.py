from Codigo.Instalador.Funciones_basicas import *

def cargar_config():
    """
    Carga y fusiona los archivos de configuración de lugares e ID con las coordenadas de los equipos.
    
    Retorna:
    - DataFrame con los lugares, IDs y coordenadas (X, Y) de los equipos.
    """
    if os.path.exists('Lugares-ID.csv'):
        df_config = pd.read_csv('Lugares-ID.csv', encoding="utf-8")
    else:
        df_config = pd.DataFrame(columns=['Lugar', 'ID'])
    df_config["Lugar"] = df_config["Lugar"].apply(eliminar_tildes)
    
    if os.path.exists('Coordenadas_Equipos.csv'):
        df_coord = pd.read_csv('Coordenadas_Equipos.csv', encoding="utf-8")
    else:
        df_coord = pd.DataFrame(columns=['Lugar', 'X', 'Y'])
    
    df_config = pd.merge(df_config, df_coord, on='Lugar', how='outer')
      
    return df_config

def guardar_config(df_config):
    """
    Guarda la configuración actualizada de los equipos (lugares, IDs, coordenadas) en los archivos CSV.
    
    Parámetros:
    - df_config: DataFrame con los lugares, IDs y coordenadas a guardar.
    """
    if os.path.exists('Coordenadas_Equipos.csv'):
        df_coord_archivo = pd.read_csv('Coordenadas_Equipos.csv', encoding="utf-8")
    else:
        df_coord_archivo = pd.DataFrame(columns=["Lugar", "X", "Y"])
        
    df_coord = df_config[["Lugar", "X", "Y"]]
    
    df_coord_actualizado = pd.merge(df_coord_archivo, df_coord, on="Lugar", how="outer", suffixes=('_old', ''))
    for col in ["X", "Y"]:
        df_coord_actualizado[col] = df_coord_actualizado[f"{col}"].combine_first(df_coord_actualizado[f"{col}_old"])
        
    df_coord_actualizado = df_coord_actualizado[["Lugar", "X", "Y"]]
    
    df_coord_actualizado = df_coord_actualizado.dropna(subset=["X", "Y"])
    
    df_coord_actualizado.to_csv('Coordenadas_Equipos.csv', index=False, encoding='utf-8')
        
    df_ID = df_config[["Lugar", "ID"]]
    df_ID.to_csv('Lugares-ID.csv', index=False, encoding='utf-8')

def agregar_equipos_nuevos_config(df_config, df_datos):
    """
    Agrega nuevos equipos al archivo de configuración que no estén presentes en los datos.
    
    Parámetros:
    - df_config: DataFrame con la configuración de los lugares y sus IDs y coordenadas.
    - df_datos: DataFrame con los datos de los equipos.
    
    Retorna:
    - DataFrame actualizado con los nuevos equipos.
    """
    df_datos.columns = [eliminar_tildes(col) for col in df_datos.columns]
    
    for col in df_datos.columns:
        if col not in df_config['Lugar'].values:
            new_row = pd.DataFrame({'Lugar': [col], 'ID': [None], 'X': [None], 'Y': [None]})
            
            new_row = new_row.dropna(axis=1, how='all')  
            df_config = pd.concat([df_config, new_row], ignore_index=True)

    return df_config

def eliminar_lugares_no_existentes_config(df_config, df_datos):
    """
    Elimina los lugares que no están presentes en los datos del archivo de configuración.
    
    Parámetros:
    - df_config: DataFrame con la configuración de lugares.
    - df_datos: DataFrame con los datos de los equipos.
    
    Retorna:
    - DataFrame actualizado con solo los lugares presentes en los datos.
    """
    lugares_existentes = df_datos.columns
    df_config = df_config[df_config['Lugar'].isin(lugares_existentes)]
    return df_config

def detectar_id_faltante_config(df_config):
    """
    Detecta los lugares que no tienen ID asignado en el archivo de configuración.
    
    Parámetros:
    - df_config: DataFrame con la configuración de lugares y sus IDs.
    
    Retorna:
    - Lista de lugares con ID faltante.
    """
    lugares_faltantes_id = df_config[df_config['ID'].isna()]['Lugar'].tolist()
    return lugares_faltantes_id

def detectar_Coord_X_faltante_config(df_config):
    """
    Detecta los lugares que no tienen coordenada X asignada en el archivo de configuración.
    
    Parámetros:
    - df_config: DataFrame con la configuración de lugares y sus coordenadas.
    
    Retorna:
    - Lista de lugares con coordenada X faltante.
    """
    lugares_faltantes_X = df_config[df_config['X'].isna()]['Lugar'].tolist()
    return lugares_faltantes_X

def detectar_Coord_Y_faltante_config(df_config):
    """
    Detecta los lugares que no tienen coordenada Y asignada en el archivo de configuración.
    
    Parámetros:
    - df_config: DataFrame con la configuración de lugares y sus coordenadas.
    
    Retorna:
    - Lista de lugares con coordenada Y faltante.
    """
    lugares_faltantes_Y = df_config[df_config['Y'].isna()]['Lugar'].tolist()
    return lugares_faltantes_Y

def actualizar_columnas_datos_config(df_config, df_datos):
    """
    Actualiza los nombres de las columnas en los datos con los nuevos IDs asignados en el archivo de configuración.
    
    Parámetros:
    - df_config: DataFrame con la configuración de lugares y sus nuevos IDs.
    - df_datos: DataFrame con los datos de los equipos.
    
    Retorna:
    - DataFrame actualizado con los nombres de columnas correspondientes a los IDs.
    """
    for _, row in df_config.iterrows():
        lugar = row['Lugar']
        nuevo_id = row['ID']
        
        if lugar in df_datos.columns:
            df_datos = df_datos.rename(columns={lugar: nuevo_id})
    
    return df_datos

def convertir_a_UTM(df_coord):
    """
    Convierte las coordenadas geográficas (latitud/longitud) a coordenadas UTM (EPSG:32721).
    
    Parámetros:
    - df_coord: DataFrame con las coordenadas geográficas (latitud, longitud).
    
    Retorna:
    - DataFrame con las coordenadas UTM (X, Y).
    """
    coordenadas_UTM_X = []
    coordenadas_UTM_Y = []
    
    for _, row in df_coord.iterrows():
        lat = row['latitud']
        lon = row['longitud']
        
        # Convertir de Latitud/Longitud (EPSG:4326) a UTM (EPSG:32721)
        x, y = transformer.transform(lon, lat)
        
        # Almacenar los resultados
        coordenadas_UTM_X.append(x)
        coordenadas_UTM_Y.append(y)
    
    df_coord = df_coord.drop('latitud', axis=1)
    df_coord = df_coord.drop('longitud', axis=1)
    
    df_coord['X'] = coordenadas_UTM_X
    df_coord['Y'] = coordenadas_UTM_Y
    
    return df_coord

def leer_archivo_coordenadas_traduccion(archivo):
    """
    Lee un archivo CSV con coordenadas geográficas y las convierte a UTM (EPSG:32721).
    
    Parámetros:
    - archivo: Ruta del archivo CSV con las coordenadas.
    
    Retorna:
    - DataFrame con las coordenadas convertidas a UTM y los lugares correspondientes.
    """    
    df_coord = pd.read_csv(archivo, encoding="utf-8")
    df_coord.columns = [eliminar_tildes(col) for col in df_coord.columns]
    df_coord.index = [eliminar_tildes(row) for row in df_coord["descripcion"]]
    df_coord = df_coord[["lon", "lat"]]
    
    df_coord.rename(columns={'lon': 'longitud', 'lat': 'latitud'}, inplace=True)
    
    
    df_coord.index = df_coord.index.str.replace('Pluviometro - ', '').str.replace('Estacion Meteorologica - ', '')
    
    df_convertido = convertir_a_UTM(df_coord)
    
    df_convertido = df_convertido.reset_index()

    df_convertido.rename(columns={'index': 'Lugar'}, inplace=True)
    
    return df_convertido


