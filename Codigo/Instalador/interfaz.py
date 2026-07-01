from Codigo.Instalador.Funciones_basicas import *
from Codigo.Instalador.Funciones_tormenta import *
from Codigo.Instalador.Funciones_mensual import *
from Codigo.Instalador.Funciones_config import *
from Codigo.Instalador.isoyetas import * 
import os


def resolver_recurso(nombre_archivo):
    """Devuelve una ruta absoluta al recurso si existe en Codigo o en la carpeta raiz."""
    base_dir = os.path.dirname(__file__)
    candidatos = [
        os.path.join(base_dir, nombre_archivo),
        os.path.join(base_dir, "..", nombre_archivo),
    ]

    for ruta in candidatos:
        ruta_abs = os.path.abspath(ruta)
        if os.path.exists(ruta_abs):
            return ruta_abs

    return nombre_archivo


def aplicar_icono(ventana):
    """Configura el icono sin romper la app si el archivo no esta disponible."""
    try:
        ventana.iconbitmap(resolver_recurso("precipitacion.ico"))
    except Exception:
        pass

class Config(tk.Toplevel):  
    # Ventana para la configuración de lugares, coordenadas y ID.

    def __init__(self, ventana_principal):
        """
        Inicializa la ventana de configuración.

        :param ventana_principal: Ventana principal donde se cargan los datos.
        """
        super().__init__(ventana_principal)
        self.ventana_principal = ventana_principal
        
        self.df_datos = self.ventana_principal.df_datos
        self.df_config = self.ventana_principal.df_config
        
        self.ventana_principal.checkbox_config_bool = False        
        
        self.lugares_faltantes_id = detectar_id_faltante_config(self.df_config)
        
        self.title("Ventana configuraciones")
        self.geometry(self.centrar_ventana(800, 650))
        self.config(background="white")
        aplicar_icono(self)
        
        self.protocol("WM_DELETE_WINDOW", self.ventana_principal.cerrar_todo) 
        
        self.crear_interfaz()
    
    def centrar_ventana(self, ancho, alto):
        """
        Calcula la posición para centrar la ventana en la pantalla.

        :param ancho: Ancho de la ventana.
        :param alto: Alto de la ventana.
        :return: Posición de la ventana centrada.
        """
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        position_top = int(screen_height / 2 - alto / 2)
        position_left = int(screen_width / 2 - ancho / 2)
        return f'{ancho}x{alto}+{position_left}+{position_top}'
    
    def crear_interfaz(self):  
        """
        Crea los componentes de la interfaz gráfica.
        """
        self.crear_tabla()
        self.crear_coord()
        self.crear_botonera()
        
    def crear_tabla(self):  
        """
        Crea y configura la tabla para mostrar la configuración de lugares, ID y coordenadas.
        """
        self.frame_config = tk.Frame(self)
        self.frame_config.pack(expand=True, fill="both", padx=10, pady=10)
        self.frame_config.config(background="white")
        
        info_label = tk.Label(self.frame_config, text="Precionar ENTER despues de editar una celda", font=("Arial", 8), background="white")
        info_label.pack(fill="both", padx=10)
        
        style = ttk.Style()
        style.configure("Treeview", rowheight=25)
        
        # Define la tabla de configuración
        self.tabla_config = ttk.Treeview(
            self.frame_config, 
            columns=('Lugar', 'ID', 'X', 'Y'), 
            show='headings', 
            height=16
        )
        self.tabla_config.heading('Lugar', text='Lugar')
        self.tabla_config.heading('ID', text='ID')
        self.tabla_config.heading('X', text='X')
        self.tabla_config.heading('Y', text='Y')

        # Insertar los datos de configuración en la tabla
        for _, row in self.df_config.iterrows():
            lugar = row['Lugar']
            id_valor = row['ID'] if pd.notna(row['ID']) else ''  
            X_valor = row['X'] if pd.notna(row['X']) else ''  
            Y_valor = row['Y'] if pd.notna(row['Y']) else ''  
            
            tag_id = 'sin_id' if lugar in self.lugares_faltantes_id else ''
            tag_X = 'sin_X' if not pd.notna(row['X']) else ''
            tag_Y = 'sin_Y' if not pd.notna(row['Y']) else ''
            
            self.tabla_config.insert('', tk.END, values=(lugar, id_valor, X_valor, Y_valor), tags=(tag_id, tag_X, tag_Y))

        self.tabla_config.tag_configure('sin_id', background='#FFC0C0', foreground='black')
        self.tabla_config.tag_configure('sin_X', background='#FFCCCC', foreground='black') 
        self.tabla_config.tag_configure('sin_Y', background='#FFCCCC', foreground='black')  
        
        # Habilitar la edición al hacer doble clic en una celda
        self.tabla_config.bind('<Double-1>', self.editar_celda)
        
        self.tabla_config.pack()

    def crear_coord(self):
        """
        Crea los campos para introducir coordenadas manualmente o mediante archivo.
        """
        self.coord_frame = tk.Frame(self)
        self.coord_frame.pack(fill="x", expand=True)
        self.coord_frame.config(background="white")
        
        self.traductor_frame = tk.Frame(self.coord_frame)
        self.traductor_frame.pack(side="top", fill="y")
        self.traductor_frame.config(background="white")
        
        # Campos de latitud y longitud
        tk.Label(self.traductor_frame, text="Introducir manualmente las coordenadas: ", font=("Arial", 10, "bold"), background="white").pack()
        
        tk.Label(self.traductor_frame, text="Latitud:", font=("Arial", 10), background="white").pack(side="left", padx=5, pady=5)
        self.latitud = tk.Entry(self.traductor_frame, font=("Arial", 10), width=10)
        self.latitud.pack(side="left", padx=10, pady=5)
        
        tk.Label(self.traductor_frame, text="Longitud:", font=("Arial", 10), background="white").pack(side="left", padx=5, pady=5)
        self.longitud = tk.Entry(self.traductor_frame, font=("Arial", 10), width=10)
        self.longitud.pack(side="left", padx=10, pady=5)
        
        # Combobox para seleccionar el lugar
        self.lugar_seleccionado = ttk.Combobox(self.traductor_frame, values=list(self.df_config['Lugar']))
        self.lugar_seleccionado.pack(side="left", padx=10, pady=5)
        
        # Botón para insertar coordenadas manualmente
        tk.Button(self.traductor_frame, text="Insertar", command=self.insertar_coord_manual, font=("Arial", 10), background="white").pack(side="left", pady=5)
        
        self.archivo_coord_frame = tk.Frame(self.coord_frame)
        self.archivo_coord_frame.pack(side="bottom", fill="y")
        self.archivo_coord_frame.config(background="white")
        
        # Botón para insertar coordenadas desde archivo
        tk.Button(self.archivo_coord_frame, text="Introducir coordenadas con archivo de Grafana", command=self.insertar_coord_archivo, font=("Arial", 10), background="white").pack(pady=20)

    def insertar_coord_archivo(self):
        """
        Permite insertar coordenadas desde un archivo CSV de Grafana.
        """
        try:
            archivo = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
            if archivo:
                self.archivo_seleccionado = archivo 
                df_archivo_coord = leer_archivo_coordenadas_traduccion(archivo)               
                
                for _, row in df_archivo_coord.iterrows():
                    lugar = row['Lugar']
                    index = self.df_config[self.df_config['Lugar'] == lugar].index
                    if not index.empty:
                        self.df_config.at[index[0], 'X'] = row['X']
                        self.df_config.at[index[0], 'Y'] = row['Y']

                self.actualizar_df_config_insertar_coord()
                messagebox.showinfo("Éxito", "Las coordenadas fueron actualizadas correctamente.")
        except:
            messagebox.showerror("Error","Seleccione un archivo valido de Grafana.\n\nRecuerde al descargar el archivo csv hay que desmarcar la opcion Datos formateados.\n\n El archivo debe contener las columnas: Descripción, longitud y latitud")
            
    def insertar_coord_manual(self):
        """
        Inserta coordenadas manualmente en la tabla de configuración.
        """
        lugar = self.lugar_seleccionado.get()
        try:
            lon = float(self.longitud.get())
            lat = float(self.latitud.get())
        except ValueError:
            messagebox.showerror("Error", "Debe ingresar valores numéricos válidos para longitud y latitud.")
            return
        
        if not lugar:
            messagebox.showerror("Error", "Debe seleccionar un lugar antes de insertar coordenadas.")
            return
        
        df_temp = pd.DataFrame({'longitud': [lon], 'latitud': [lat]})
        df_temp = convertir_a_UTM(df_temp)
        
        index = self.df_config[self.df_config['Lugar'] == lugar].index
        if not index.empty:
            self.df_config.at[index[0], 'X'] = df_temp.at[0, 'X']
            self.df_config.at[index[0], 'Y'] = df_temp.at[0, 'Y']
            self.actualizar_df_config_insertar_coord()
            messagebox.showinfo("Exito", "Se insertaron correctamente las coordenadas.")  
        else:
            messagebox.showerror("Error", "El lugar seleccionado no existe en la tabla.")  
        
    def actualizar_df_config_insertar_coord(self):
        """
        Actualiza la tabla con las coordenadas recién insertadas.
        """
        for row in self.tabla_config.get_children():
            self.tabla_config.delete(row)
        
        # Insertar filas de df_config en el Treeview
        for _, row in self.df_config.iterrows():
            self.tabla_config.insert('', 'end', values=(row['Lugar'], row['ID'], row['X'], row['Y']))
 
    def actualizar_df_config_editar_manualmente(self):
        """
        Actualiza el DataFrame df_config con los valores editados manualmente en la tabla.
        """
        lugares_actuales = [self.tabla_config.item(item, 'values')[0] for item in self.tabla_config.get_children()]
        
        # Filtrar df_config para que solo contenga lugares que están en el Treeview
        self.df_config = self.df_config[self.df_config['Lugar'].isin(lugares_actuales)].reset_index(drop=True)

        for i, item in enumerate(self.tabla_config.get_children()):
            values = self.tabla_config.item(item, 'values')
            self.df_config.at[i, 'Lugar'] = values[0]
            self.df_config.at[i, 'ID'] = values[1] if values[1].strip() != '' else None  
            self.df_config.at[i, 'X'] = float(values[2]) if values[2].strip() != '' else None
            self.df_config.at[i, 'Y'] = float(values[3]) if values[3].strip() != '' else None
           
    def editar_celda(self, event):
        """
        Permite editar una celda en la tabla al hacer doble clic.
        Crea un campo de entrada para editar el valor de la celda seleccionada.
        Al presionar Enter, guarda el nuevo valor y actualiza el DataFrame.
        """
        selected_item = self.tabla_config.selection()[0]
        column = self.tabla_config.identify_column(event.x) 
        col_index = int(column[1:]) - 1 
        old_value = self.tabla_config.item(selected_item, 'values')[col_index]

        entry = tk.Entry(self.frame_config)
        entry.insert(0, old_value if old_value != "nan" else "")  
        entry.select_range(0, tk.END)  
        entry.focus()

        bbox = self.tabla_config.bbox(selected_item, column)
        entry.place(x=bbox[0], y=bbox[1], width=bbox[2], height=bbox[3])
        
        # Manejar la actualización del valor al presionar Enter
        def guardar_edicion(event):
            new_value = entry.get()
            
            current_values = list(self.tabla_config.item(selected_item, 'values'))
            current_values[col_index] = new_value
            self.tabla_config.item(selected_item, values=current_values)
            entry.destroy()  
            
            self.actualizar_df_config_editar_manualmente()

        entry.bind('<Return>', guardar_edicion)
        
    def crear_botonera(self):
        """
        Crea la barra de botones en la parte inferior de la ventana de configuración.
        Incluye botones para volver al inicio y para guardar las configuraciones.
        """
        self.botonera_frame = tk.Frame(self)
        self.botonera_frame.pack(side= "bottom", fill="x", expand=True)
        self.botonera_frame.config(background="white")

        botones_frame = tk.Frame(self.botonera_frame)
        botones_frame.pack(side="top", fill="y")
        botones_frame.config(background="white")
        
        Volver_btn = tk.Button(botones_frame, text="Volver", command=lambda: self.volver_inicio(), font=("Arial", 10, "bold"),background="white")
        Volver_btn.pack(side= "left", padx=10, pady=5)   
        
        Guardar_btn = tk.Button(botones_frame, text="Guardar Configuraciones", command=lambda: self.guardar_config(), font=("Arial", 10, "bold"),background="white")
        Guardar_btn.pack(side= "left", padx=10, pady=5)
    
    def guardar_config(self):
        """
        Guarda las configuraciones si todos los campos requeridos están completos.
        Verifica si hay IDs y coordenadas faltantes antes de guardar los datos.
        """
        id_faltante = detectar_id_faltante_config(self.df_config)
        X_faltante = detectar_Coord_X_faltante_config(self.df_config)
        Y_faltante = detectar_Coord_Y_faltante_config(self.df_config)
        if id_faltante:
            messagebox.showwarning("Advertencia", f"Complete todos los IDs.\n\nID faltante en: {id_faltante}")
        elif X_faltante:
            messagebox.showwarning("Advertencia", f"Complete todas las coordenadas.\n\nFaltan completar coordenadas X en:: {X_faltante}")
        elif Y_faltante:
            messagebox.showwarning("Advertencia", f"Complete todas las coordenadas.\n\nFaltan completar coordenadas Y en: {Y_faltante}")
        else:
            guardar_config(self.df_config)
            self.df_datos = actualizar_columnas_datos_config(self.df_config, self.ventana_principal.df_datos)
            self.ventana_principal.df_datos = self.df_datos
            self.cerrar_ventana()
    
    def volver_inicio(self):
        """
        Vuelve a la ventana principal y cierra la ventana de configuración.
        """
        self.destroy()
        self.ventana_principal.deiconify()
    
    def cerrar_ventana(self):
        """
        Cierra la ventana de configuración y guarda los datos antes de proceder a la siguiente etapa.
        """
        self.destroy()
        self.ventana_principal.df_config = self.df_config
        self.siguiente()
    
    def siguiente(self):
        """
        Calcula los acumulados diarios y redirige al siguiente análisis según la selección.
        Dependiendo de la selección ("Tormenta" o "Mensual"), carga la ventana correspondiente.
        """
        self.ventana_principal.df_datos_original = self.ventana_principal.df_datos
        df_instantaneo = calcular_instantaneos(self.df_datos)
        self.df_acumulados_diarios = calcular_acumulados_diarios(df_instantaneo)
        self.ventana_principal.df_acumulados_diarios = self.df_acumulados_diarios
        if self.ventana_principal.analisis_seleccionado.get()== "Tormenta":
            return VentanaLimiteTemporal(self.ventana_principal)
        
        if self.ventana_principal.analisis_seleccionado.get()=="Mensual":
            self.df_acumulados_INUMET = leer_archivo_inumet(self.ventana_principal.archivo_inumet_seleccionado)
            self.ventana_principal.df_acumulados_INUMET = self.df_acumulados_INUMET
            return VentanaPrincipalMensual(self.ventana_principal)        
    
class VentanaValidador(tk.Toplevel):
    """
    Ventana secundaria para la validación de archivos de datos.
    Permite al usuario seleccionar archivos CSV de validación y agregarlos a los datos principales.
    
    Parámetros:
    - ventana_principal: Referencia a la ventana principal de la aplicación.
    """
    def __init__(self, ventana_principal):
        super().__init__(ventana_principal)
        
        self.ventana_principal = ventana_principal
        self.df_datos = self.ventana_principal.df_datos
        
        self.title("Ventana de Inicio")
        self.geometry(self.centrar_ventana(500, 150))
        self.config(background="white")
        aplicar_icono(self)
        
        self.altura_ventana = 120  # Altura inicial
        self.incremento_altura = 40  # Incremento en altura por campo
        
        self.archivos_validadores = []  # Lista para almacenar rutas de archivos
        self.frames_archivos = []  # Lista de frames para gestionar dinámicamente
        
        self.crear_interfaz()
        
        self.protocol("WM_DELETE_WINDOW", self.ventana_principal.cerrar_todo) 
    
    def centrar_ventana(self, ancho, alto):
        """
        Centra la ventana en la pantalla.
        
        Parámetros:
        - ancho: Ancho de la ventana.
        - alto: Alto de la ventana.
        
        Retorna:
        - Cadena con las coordenadas de la ventana centrada.
        """
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        position_top = int(screen_height / 2 - alto / 2)
        position_left = int(screen_width / 2 - ancho / 2)
        return f'{ancho}x{alto}+{position_left}+{position_top}'
    
    def crear_interfaz(self):
        """
        Crea la interfaz de usuario con los elementos necesarios.
        """
        self.frame_archivo_validador()
        
        self.crear_botonera()
        
    def frame_archivo_validador(self):
        """
        Crea el marco contenedor para los campos de selección de archivos.
        """
        self.archivo_validador_frame = tk.Frame(self)
        self.archivo_validador_frame.pack(pady=5)
        self.archivo_validador_frame.config(background="white")
        
        # Crear el primer campo de selección
        self.agregar_campo_archivo()
        
        self.agregar_campo_archivo__btn_frame = tk.Frame(self)
        self.agregar_campo_archivo__btn_frame.pack()
        self.agregar_campo_archivo__btn_frame.config(background="white")
        
        self.boton_agregar_archivo = tk.Button(self.agregar_campo_archivo__btn_frame, text="+", command=self.agregar_campo_archivo, font=("Arial", 11, "bold"), width= 5, background="white")
        self.boton_agregar_archivo.pack(pady=5)
    
    def crear_botonera(self):
        """
        Crea la botonera con opciones para volver y agregar datos.
        """
        self.botonera_frame = tk.Frame(self)
        self.botonera_frame.pack(fill="y", expand=True)
        self.botonera_frame.config(background="white")
        
        Volver_btn = tk.Button(self.botonera_frame, text="Volver", command=lambda: self.volver_inicio(), font=("Arial", 10, "bold"), background="white")
        Volver_btn.pack(side="left",padx=10)  
        
        agregar_btn = tk.Button(self.botonera_frame, text="Agregar datos", command=lambda: self.agregar_datos(), font=("Arial", 10, "bold"), background="white")
        agregar_btn.pack(side="left",padx=10)
        
    def agregar_campo_archivo(self):
        """
        Agrega un nuevo campo de entrada para seleccionar un archivo CSV.
        """
        frame = tk.Frame(self.archivo_validador_frame)
        frame.pack(pady=5)
        frame.config(background="white")
        self.frames_archivos.append(frame)
        
        entry = tk.Entry(frame, font=("Arial", 12), width=40)
        entry.pack(side=tk.LEFT, padx=5)
        
        tk.Button(frame, text=" ... ", command=lambda: self.seleccionar_archivo(entry), font=("Arial", 10, "bold"), background="white").pack(side=tk.LEFT)
        
        self.archivos_validadores.append(entry)
        
        self.altura_ventana += self.incremento_altura
        self.geometry(self.centrar_ventana(500, self.altura_ventana))
    
    def seleccionar_archivo(self, entry):
        """
        Abre un cuadro de diálogo para seleccionar un archivo y lo inserta en el campo de entrada.
        
        Parámetros:
        - entry: Campo de entrada donde se mostrará la ruta del archivo seleccionado.
        """
        try:
            archivo = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
            if archivo:
                entry.delete(0, END)
                entry.insert(0, archivo)
        except:
            messagebox.showerror("Error", "Error al abrir el archivo. Seleccione un archivo del validador.")
       
    def agregar_datos(self):
        """
        Agrega los datos de los archivos CSV seleccionados a la base de datos principal.
        """
        rutas_archivos = [entry.get() for entry in self.archivos_validadores if entry.get()]
        if rutas_archivos:
            for archivo in rutas_archivos:
                try:
                    self.df_datos = leer_archivo_verificador(archivo, self.df_datos)  # Asume que existe esta función
                    self.mensaje_exito_agregar()
                except:
                    messagebox.showerror("Error", f"Error al procesar el archivo: {archivo}")
        else:
            messagebox.showinfo("Error", "Debe seleccionar al menos un archivo.")
    
    def mensaje_exito_agregar(self):
        """
        Muestra un mensaje de éxito y vuelve a la pantalla principal.
        """ 
        messagebox.showinfo("Exito", "Se agregaron correctamente los datos del validador.")
        self.volver_inicio()
    
    def volver_inicio(self):
        """
        Cierra la ventana de validación y regresa a la ventana principal.
        """
        self.destroy()
        self.ventana_principal.deiconify()   
        
    def cerrar_ventana(self):
        """
        Cierra la ventana actual y limpia el campo de selección si es necesario.
        """
        if self.archivo_validador_text.get():
            self.archivo_validador_text.delete(0, END)
        self.destroy()

class VentanaInicio(tk.Tk):
    """
    Clase que representa la ventana principal de inicio de la aplicación.
    Se encarga de gestionar la interfaz gráfica y la interacción con el usuario.
    """
    def __init__(self):
        super().__init__()       
        self.title("Ventana de Inicio")
        self.config(background="white")
        self.geometry(self.centrar_ventana(430, 380))
        
        aplicar_icono(self)
        
        # Carga de imágenes de los logos
        self.logo_tau = Image.open(resolver_recurso("Logo_Grupo_Tau.png")) 
        self.logo_tau = self.logo_tau.resize((70, 50))
        self.logo_tau = ImageTk.PhotoImage(self.logo_tau)
        
        self.logo_dica = Image.open(resolver_recurso("Logo_Dica.png")) 
        self.logo_dica = self.logo_dica.resize((55, 55))
        self.logo_dica = ImageTk.PhotoImage(self.logo_dica)
        
        self.logo_imm= Image.open(resolver_recurso("Logo_imm.jpg")) 
        self.logo_imm = self.logo_imm.resize((40, 40))
        self.logo_imm = ImageTk.PhotoImage(self.logo_imm)
        
        # Variables de control para los archivos seleccionados
        self.archivo_seleccionado = ""
        self.archivo_inumet_seleccionado = ""
        
        # Variables de interfaz
        self.archivo_principal_text = None
        self.archivo_inumet_text = None
        
        self.analisis_seleccionado = None
        
        self.comenzar_btn = None
        
        self.checkbox_config = tk.BooleanVar(value=False)
        self.checkbox_config_bool = False
        
        self.checkboxes = {}
        self.checkbox_inicio = True
        
        self.valor_acumulado_inumet_tormenta = None
        
        self.df_acumulados_diarios = None
        
        # Lista de variables de retorno de período de retorno (TR)
        self.lista_tr = [tk.IntVar(value=v) for v in [1, 1, 1, 1, 0, 1, 0]]
        
        # Valores límite predeterminados
        self.limite_precipitacion_valor = 150
        self.limite_tiempo_valor = 1480
        self.limite_precipitacion_valor_ampliada = 80
        self.limite_tiempo_valor_ampliada = 120
        
        self.grilla_temporal_inst = 30
        
        # Selección de período de retorno inicial
        self.tr_seleccionado = list(precipitacion_tr.keys())[0]
           
        self.crear_interfaz()
        
        self.protocol("WM_DELETE_WINDOW", self.cerrar_todo) 
        
        self.mainloop()

    def centrar_ventana(self, ancho, alto):
        """Centra la ventana en la pantalla."""
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        position_top = int(screen_height / 2 - alto / 2)
        position_left = int(screen_width / 2 - ancho / 2)
        return f'{ancho}x{alto}+{position_left}+{position_top}'

    def crear_interfaz(self):
        """Crea los elementos gráficos de la interfaz."""
        self.frame_archivo_principal()
        
        self.frame_seleccion_analisis()
        
        self.frame_archivo_inumet()

        self.frame_botonera()

        self.frame_logos()
        
        self.habilitar_boton_comenzar()

    def frame_logos(self):
        """Crea el marco que muestra los logos de la aplicación."""
        logos_frame = tk.Frame(self)
        logos_frame.config(background="white")
        logos_frame.pack(fill="y")
        
        etiqueta_dica = tk.Label(logos_frame, image=self.logo_dica, background="white")
        etiqueta_dica.pack(side="right", padx=2)

        etiqueta_dica.image = self.logo_dica 
        
        etiqueta_tau = tk.Label(logos_frame, image=self.logo_tau, background="white")
        etiqueta_tau.pack(side="right", padx=2)

        etiqueta_tau.image = self.logo_tau 
        
        etiqueta_tau = tk.Label(logos_frame, image=self.logo_imm, background="white")
        etiqueta_tau.pack(side="right", padx=2)

        etiqueta_tau.image = self.logo_imm 
        
    def frame_archivo_principal(self):
        """Crea el marco para la selección del archivo principal."""
        archivo_frame = tk.Frame(self)
        archivo_frame.pack(pady=5)
        archivo_frame.config(background="white")
        tk.Label(archivo_frame, text="Seleccionar archivo CSV: ", font=("Arial", 10, "bold"), background="white").pack(pady=5)
        
        self.archivo_principal_text = tk.Entry(archivo_frame, font=("Arial", 12), width=40)
        self.archivo_principal_text.pack(side=tk.LEFT, padx=5)
        
        if self.archivo_seleccionado:
            self.archivo_principal_text.insert(0, self.archivo_seleccionado)
        
        tk.Button(archivo_frame, text=" ... ", command=self.seleccionar_archivo_principal, font=("Arial", 10, "bold"), background="white").pack(side=tk.LEFT)
        
        self.archivo_principal_text.bind("<FocusOut>", self.habilitar_boton_comenzar)

    def frame_seleccion_analisis(self):
        """Crea el marco para la selección del tipo de análisis."""
        seleccion = tk.Frame(self)
        seleccion.pack(pady=5)
        seleccion.config(background="white")
        tk.Label(seleccion, text="Seleccionar Tipo de análisis", font=("Arial", 10, "bold"), background="white").pack(pady=5)
        
        self.analisis_seleccionado = ttk.Combobox(seleccion, values=["Tormenta", "Mensual"])
        self.analisis_seleccionado.pack(pady=5)
        self.analisis_seleccionado.set("")
        
        self.analisis_seleccionado.bind("<<ComboboxSelected>>", self.seleccionar_introducir_valores_inumet)

    def seleccionar_introducir_valores_inumet(self, event=None):
        """Habilita los campos de entrada según el tipo de análisis seleccionado."""
        self.inumet_btn.config(state=NORMAL)
        self.archivo_inumet_text.config(state=NORMAL)
        if self.analisis_seleccionado.get() == "Mensual":
            self.label_inumet.config(text="Seleccionar archivo CSV de INUMET: ")
            self.inumet_btn.config(text=" ... ")
        else:
            self.label_inumet.config(text="Introducir Valor Total (en mm) de INUMET en la Tormenta: ")
            self.inumet_btn.config(text=" > ")
        
        self.habilitar_boton_comenzar()

    def frame_archivo_inumet(self):
        """
        Crea un frame para la selección del archivo INUMET.
        """
        archivo_inumet_frame = tk.Frame(self)
        archivo_inumet_frame.pack(pady=5)
        archivo_inumet_frame.config(background="white")
        
        self.label_inumet = tk.Label(archivo_inumet_frame, text="INUMET ", font=("Arial", 10, "bold"), background="white")
        self.label_inumet.pack(pady=5)
        
        self.archivo_inumet_text = tk.Entry(archivo_inumet_frame, font=("Arial", 12), width=40, state=DISABLED, background="white")
        self.archivo_inumet_text.pack(side=tk.LEFT, padx=5)
        
        if self.archivo_inumet_text:
            self.archivo_inumet_text.insert(0, self.archivo_inumet_seleccionado)
        
        self.inumet_btn = tk.Button(archivo_inumet_frame, text="  ", command=self.seleccionar_valores_inumet, font=("Arial", 10, "bold"), state=DISABLED, background="white")
        self.inumet_btn.pack(side=tk.LEFT)
        
        self.archivo_inumet_text.bind("<FocusOut>", self.habilitar_boton_comenzar)

    def frame_botonera(self):
        """
        Crea un frame con un botón para agregar datos validados y otro para iniciar el proceso.
        También contiene un checkbox para configurar parámetros adicionales.
        """
        validador_frame = tk.Frame(self)
        validador_frame.pack(pady=5)
        validador_frame.config(background="white")
        
        self.validador_btn = tk.Button(validador_frame, text="Agregar datos validador", command=self.iniciar_ventana_validador, font=("Arial", 12, "bold"), state=tk.DISABLED, background="white")
        self.validador_btn.pack(pady=5)
        
        opciones_frame = tk.Frame(self)
        opciones_frame.pack(pady=5)
        opciones_frame.config(background="white")
        
        self.checkbox = tk.Checkbutton(opciones_frame, text="Configuraciones", variable=self.checkbox_config, command=lambda: self.actualizar_checkbox_config(), onvalue=True, offvalue=False, font=("Arial", 12), background="white")
        self.checkbox.pack(side= "left", pady=5)
        
        self.comenzar_btn = tk.Button(opciones_frame, text="Siguiente", command=self.iniciar_ventanas, font=("Arial", 12, "bold"), state=tk.DISABLED, background="white")
        self.comenzar_btn.pack(side= "left", padx= 10, pady=5)

    def iniciar_ventana_validador(self):
        """
        Cierra la ventana actual y abre la ventana de validación.
        """
        self.cerrar_ventana()
        return VentanaValidador(self)
        
    def habilitar_boton_validador(self):
        """
        Habilita el botón del validador si hay un archivo principal seleccionado.
        """
        if self.archivo_principal_text.get():
            self.validador_btn.config(state=NORMAL)
        else:
            self.validador_btn.config(state=DISABLED)
    
    def actualizar_checkbox_config(self):
        """
        Actualiza el valor del checkbox de configuraciones.
        """
        self.checkbox_config_bool = self.checkbox_config.get()   

    def seleccionar_archivo_principal(self):
        """Abre un cuadro de diálogo para seleccionar un archivo CSV principal."""
        #try:
        archivo = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if archivo:
            self.archivo_principal_text.delete(0, END)  
            self.archivo_principal_text.insert(0, archivo)  
            self.archivo_seleccionado = archivo  
            self.df_datos = leer_archivo_principal(self.archivo_seleccionado)
            self.habilitar_boton_comenzar() 
        #except:
        #    self.archivo_principal_text.delete(0, END)  # Borrar texto previo
        #    messagebox.showerror("Error","Seleccione un archivo valido de Grafana.\n\nRecuerde al descargar el archivo csv seleccionar en Opciones de datos:\nSeries unidades por el tiempo y no Descargar para Excel")
            
    def seleccionar_valores_inumet(self):
        """
        Permite seleccionar un archivo CSV de INUMET y procesa su contenido si el tipo de análisis es "Mensual".
        Si el análisis es "Tormenta", permite ingresar un valor numérico manualmente.
        """
        if self.archivo_principal_text.get() and self.analisis_seleccionado.get() != "":
            if self.analisis_seleccionado.get() == "Mensual":
                try:
                    archivo = filedialog.askopenfilename( filetypes=[("Archivos CSV", "*.csv"), ("Archivos Excel", "*.xlsx;*.xls"), ("Todos los archivos", "*.*")])
                    if archivo:
                        self.archivo_inumet_text.delete(0, END) 
                        self.archivo_inumet_text.insert(0, archivo) 
                        self.archivo_inumet_seleccionado = archivo  
                        
                        verificador = leer_archivo_inumet(self.archivo_inumet_seleccionado)
                        
                        self.habilitar_boton_comenzar()
                except:
                        self.archivo_inumet_text.delete(0, END)
                        messagebox.showerror("Error", "Error al abrir el archivo. Seleccione un archivo de INUMET valido.\n\nRecuerde que el archivo csv de INUMET debe construirse de la siguiente forma:\n\n- Nombre columnas: FECHA | INUMET\n- Formato columnas: dd/mm/aaaa | valor precipitacion(mm)")
            else:
                try:
                    if self.archivo_inumet_text.get() == "":
                        self.valor_acumulado_inumet_tormenta = None
                    else:
                        self.valor_acumulado_inumet_tormenta = float(self.archivo_inumet_text.get())
                    messagebox.showinfo("Exito", "Valor de INUMET en la Tormenta introducido correctamente")
                    self.habilitar_boton_comenzar()
                except:
                    messagebox.showerror("Error", "El valor ingresado no es un número valido.")
        else:
            messagebox.showinfo("Error", "Seleccione primero el archivo csv de Grafana y el Tipo de Analisis.")

    def habilitar_boton_comenzar(self, event=None):
        """Habilita o deshabilita el botón de 'Comenzar' según las condiciones."""
        if self.archivo_principal_text.get() and self.analisis_seleccionado.get() == "Tormenta": 
            self.comenzar_btn.config(state=NORMAL) 
        else:
            if self.analisis_seleccionado.get() == "Mensual" and self.archivo_principal_text.get() and self.archivo_inumet_text.get():
                self.comenzar_btn.config(state=NORMAL) 
            else:
                self.comenzar_btn.config(state=DISABLED)    
        self.habilitar_boton_validador()
   
    def reiniciar_variables(self):
        """
        Funcion que usan las otras interfaces cuando quieren reiniciar a los valores predeterminados
        """
        self.archivo_principal_text.delete(0, END)
        self.analisis_seleccionado.set("")
        if self.archivo_inumet_text.get():
            self.archivo_inumet_text.delete(0, END)
                
        self.lista_tr = [tk.IntVar(value=v) for v in [1, 1, 1, 1, 0, 1, 0]]
        
        self.limite_precipitacion_valor = 150
        self.limite_tiempo_valor = 1480
        self.limite_precipitacion_valor_ampliada = 80
        self.limite_tiempo_valor_ampliada = 120
        
        self.valor_acumulado_inumet_tormenta = None
        
        self.tr_seleccionado = list(precipitacion_tr.keys())[0]
        
        self.label_inumet.config(text="INUMET ")
        self.inumet_btn.config(text="  ")
        self.inumet_btn.config(state=DISABLED)
        self.archivo_inumet_text.config(state=DISABLED)
        self.grilla_temporal_inst = 30
        
        self.checkboxes = {}

        self.checkbox_config.set(False)
        self.actualizar_checkbox_config()
        
        self.habilitar_boton_validador
        self.habilitar_boton_comenzar()

    def iniciar_ventanas(self):
        """
        Inicia la siguiente ventana dependiendo del análisis seleccionado.
        Verifica configuraciones y actualiza los datos.
        """
                      
        self.checkbox_inicio = True
                                            
        df_config = cargar_config()
        df_config = agregar_equipos_nuevos_config(df_config, self.df_datos)
        self.df_config= eliminar_lugares_no_existentes_config(df_config, self.df_datos)
        
        if detectar_id_faltante_config(self.df_config) or self.checkbox_config_bool or detectar_Coord_X_faltante_config(self.df_config) or detectar_Coord_Y_faltante_config(self.df_config):
            self.checkbox_config.set(False)
            self.actualizar_checkbox_config()
            self.cerrar_ventana()
            Config(self)
        else:
            self.df_datos = actualizar_columnas_datos_config(self.df_config, self.df_datos)
            self.df_datos_original = self.df_datos
            
            df_instantaneo = calcular_instantaneos(self.df_datos)
            self.df_acumulados_diarios = calcular_acumulados_diarios(df_instantaneo)
            
            if self.analisis_seleccionado.get()== "Tormenta":
                self.cerrar_ventana()
                return VentanaLimiteTemporal(self)
            
            if self.analisis_seleccionado.get()=="Mensual":    
                self.df_acumulados_INUMET = leer_archivo_inumet(self.archivo_inumet_seleccionado)
                
                self.cerrar_ventana()
                return VentanaPrincipalMensual(self)
     
    def cerrar_todo(self):
        self.quit()  # Termina el mainloop de Tkinter
        self.destroy()
    
    def cerrar_ventana(self):
        self.withdraw()

class VentanaLimiteTemporal(tk.Toplevel):
    """
    Clase que permite ajustar un límite temporal para filtrar datos de lluvia y visualizar las precipitaciones
    en un gráfico según el intervalo de tiempo seleccionado.

    Parámetros:
    - ventana_principal: Instancia de la ventana principal desde la cual se invoca esta ventana.
    
    Métodos:
    - crear_interfaz: Crea y organiza los elementos de la interfaz gráfica, como los botones y campos de fecha.
    - obtener_fecha_hora: Obtiene las fechas y horas de los límites temporal inferior y superior.
    - actualizar_grafica: Actualiza la gráfica de precipitaciones en función de los límites temporales seleccionados.
    - validar_datos: Valida que las fechas y horas ingresadas estén dentro de los rangos disponibles en los datos.
    - actualizar_df_datos: Actualiza el dataframe con los datos filtrados por los límites temporales seleccionados.
    - regresar_inicio: Reinicia la ventana principal y cierra la ventana actual.
    - proxima_ventana_tormenta: Abre la siguiente ventana para visualizar la tormenta filtrada.
    - cerrar_ventana: Cierra la ventana actual.

    Retorna:
    - None
    """
    def __init__(self, ventana_principal):
        super().__init__(ventana_principal)
        self.ventana_principal = ventana_principal
        
        self.grilla_temporal_inst = self.ventana_principal.grilla_temporal_inst

        
        self.df_datos = self.ventana_principal.df_datos
        self.df_datos_original = self.ventana_principal.df_datos_original
        
        pluvio_validos, pluvio_no_validos = obtener_pluviometros_validos(self.df_datos)
        df_lluvia_instantanea = calcular_instantaneos(self.df_datos_original)

        self.lluvia_filtrada = df_lluvia_instantanea[pluvio_validos]
        
        self.title("Ventana limite temporal")
        self.state('zoomed')
        self.config(background="white")
        aplicar_icono(self)
        
        self.limite_inf_selector = None
        self.limite_sup_selector = None
        self.frame_grafica = None
                
        self.crear_interfaz()
        self.actualizar_grafica()
        
        self.protocol("WM_DELETE_WINDOW", self.ventana_principal.cerrar_todo) 
        
    def crear_interfaz(self):
        self.frame_grafica = tk.Frame(self)
        self.frame_grafica.pack(side="top", expand=True, fill="both", padx=10, pady=20)
        self.frame_grafica.config(background="white")
        
        frame_limites_1 = tk.Frame(self)
        frame_limites_1.pack(side="bottom", expand=True, fill="both")
        frame_limites_1.config(background="white")
        
        frame_limites = tk.Frame(self)
        frame_limites.pack(side="bottom", expand=True, fill="y", padx=10)
        frame_limites.config(background="white")

        Reiniciar_btn = tk.Button(frame_limites, text="Reiniciar", command=self.regresar_inicio, font=("Arial", 10, "bold"),background="white")
        Reiniciar_btn.pack(side="left", padx=10)
        
        tk.Label(frame_limites, text="Seleccionar Grilla Temporal:", background="white").pack(side="left")
        
        lista_tiempo_Grilla =["5", "10", "15", "20", "25", "30", "35", "40", "45", "50", "55", "60", "90", "120"]
        self.Grilla_Temporal_selector = ttk.Combobox(frame_limites, values=lista_tiempo_Grilla, width=5)
        self.Grilla_Temporal_selector.pack(side="left", padx=10)
        self.Grilla_Temporal_selector.set(str(self.grilla_temporal_inst))
        
        fecha_min = str(self.ventana_principal.df_datos.index.min())
        fecha_max = str(self.ventana_principal.df_datos.index.max())
        
        self.fecha_min_date, self.fecha_min_time = fecha_min.split(" ")
        self.fecha_max_date, self.fecha_max_time = fecha_max.split(" ")
        
        tk.Label(frame_limites, text="Inicio:", background="white").pack(side="left")
        
        self.limite_inf_fecha = tk.Entry(frame_limites, width=10)
        self.limite_inf_fecha.pack(side="left", padx=5)
        self.limite_inf_fecha.insert(0, self.fecha_min_date)
        
        self.limite_inf_hora = tk.Entry(frame_limites, width=8)
        self.limite_inf_hora.pack(side="left", padx=5)
        self.limite_inf_hora.insert(0, self.fecha_min_time)
        
        tk.Label(frame_limites, text="Fin:", background="white").pack(side="left")
        
        self.limite_sup_fecha = tk.Entry(frame_limites, width=10)
        self.limite_sup_fecha.pack(side="left", padx=5)
        self.limite_sup_fecha.insert(0, self.fecha_max_date)
        
        self.limite_sup_hora = tk.Entry(frame_limites, width=8)
        self.limite_sup_hora.pack(side="left", padx=5)
        self.limite_sup_hora.insert(0, self.fecha_max_time)
        
        Aplicar_btn = tk.Button(frame_limites, text="Aplicar", command=self.actualizar_grafica, font=("Arial", 10, "bold"), background="white")
        Aplicar_btn.pack(side="left", padx=10)
        
        Siguiente_btn = tk.Button(frame_limites, text="Siguiente", command=self.actualizar_df_datos, font=("Arial", 10, "bold"), background="white")
        Siguiente_btn.pack(side="left", padx=10)
    
    def obtener_fecha_hora(self):
        fecha_inicio = self.limite_inf_fecha.get()
        hora_inicio = self.limite_inf_hora.get()
        fecha_fin = self.limite_sup_fecha.get()
        hora_fin = self.limite_sup_hora.get()
        
        limite_inferior = f"{fecha_inicio} {hora_inicio}"
        limite_superior = f"{fecha_fin} {hora_fin}"
        
        return limite_inferior, limite_superior

    def actualizar_grafica(self):
        if self.validar_datos():
            limite_inferior, limite_superior = self.obtener_fecha_hora()
            
            lluvia_limitada_temp = limitar_df_temporal(self.lluvia_filtrada, limite_inferior, limite_superior)
            
            self.grilla_temporal_inst = self.Grilla_Temporal_selector.get()
            self.grilla_temporal_inst = int(self.grilla_temporal_inst)
            self.ventana_principal.grilla_temporal_inst = self.grilla_temporal_inst
            
            try:
                fig = graficar_lluvia_instantanea_tormenta(lluvia_limitada_temp, self.grilla_temporal_inst)
            except Exception as e:
                messagebox.showerror("Error", f"Ocurrió un error al generar la gráfica:\n\n{str(e)}")
            
            for widget in self.frame_grafica.winfo_children():
                widget.destroy()
            
            canvas = FigureCanvasTkAgg(fig, master=self.frame_grafica)
            canvas.get_tk_widget().pack(fill="both", expand=True)
            canvas.draw()

    def validar_datos(self):
        try:
            limite_inferior, limite_superior = self.obtener_fecha_hora()
            limite_inf = pd.to_datetime(limite_inferior)
            limite_sup = pd.to_datetime(limite_superior)
            
            if limite_inf < self.ventana_principal.df_datos_original.index.min():
                messagebox.showwarning("Advertencia", "La fecha mínima seleccionada excede el límite.")
                self.limite_inf_fecha.delete(0, tk.END)
                self.limite_inf_hora.delete(0, tk.END)
                
                self.limite_inf_fecha.insert(0, self.fecha_min_date)
                self.limite_inf_hora.insert(0, self.fecha_min_time)

                return False

            if limite_sup > self.ventana_principal.df_datos_original.index.max():
                messagebox.showwarning("Advertencia", "La fecha máxima seleccionada excede el límite.")
                self.limite_sup_fecha.delete(0, tk.END)
                self.limite_sup_hora.delete(0, tk.END)
                
                self.limite_sup_fecha.insert(0, self.fecha_max_date)
                self.limite_sup_hora.insert(0, self.fecha_max_time)
                return False
            
            if limite_inf > limite_sup:
                messagebox.showwarning("Advertencia", "La fecha de inicio no puede ser mayor que la fecha de fin.")
                
                self.limite_inf_fecha.delete(0, tk.END)
                self.limite_inf_hora.delete(0, tk.END)
                self.limite_sup_fecha.delete(0, tk.END)
                self.limite_sup_hora.delete(0, tk.END)
                
                self.limite_inf_fecha.insert(0, self.fecha_min_date)
                self.limite_inf_hora.insert(0, self.fecha_min_time)                
                self.limite_sup_fecha.insert(0, self.fecha_max_date)
                self.limite_sup_hora.insert(0, self.fecha_max_time)
                
                self.actualizar_grafica()
                return False
            
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Error validando fechas: {str(e)}")
            
            self.limite_inf_fecha.delete(0, tk.END)
            self.limite_inf_hora.delete(0, tk.END)
            self.limite_sup_fecha.delete(0, tk.END)
            self.limite_sup_hora.delete(0, tk.END)
            
            self.limite_inf_fecha.insert(0, self.fecha_min_date)
            self.limite_inf_hora.insert(0, self.fecha_min_time)                
            self.limite_sup_fecha.insert(0, self.fecha_max_date)
            self.limite_sup_hora.insert(0, self.fecha_max_time)
            
            
            return False

    def actualizar_df_datos(self):
        if self.validar_datos():
            limite_inferior, limite_superior = self.obtener_fecha_hora()
            self.ventana_principal.df_datos = limitar_df_temporal(self.ventana_principal.df_datos_original, limite_inferior, limite_superior)
            self.proxima_ventana_tormenta()

    def regresar_inicio(self):
        self.cerrar_ventana()
        self.ventana_principal.reiniciar_variables()
        self.ventana_principal.deiconify()
        
    def proxima_ventana_tormenta(self):
        self.cerrar_ventana()
        VentanaPrincipalTormenta(self.ventana_principal)
        
    def cerrar_ventana(self):
        self.destroy()

class MostrarGrafica(tk.Toplevel):
    """
    Clase que muestra una gráfica en una ventana emergente.

    Parámetros:
    - grafica: Objeto de la gráfica que se desea mostrar en la ventana emergente.
    
    Métodos:
    - __init__: Inicializa la ventana emergente y configura la interfaz para mostrar la gráfica.
    
    Retorna:
    - None
    """
    def __init__(self, grafica):
        super().__init__()
                
        self.state('zoomed')
        self.config(background="white")
        aplicar_icono(self)
        
        frame_grafica = tk.Frame(self)
        frame_grafica.pack(fill="both", pady=20, expand=True)
        frame_grafica.config(background="white")
        
        canvas = FigureCanvasTkAgg(grafica, master=frame_grafica)
        canvas.get_tk_widget().pack(fill="both", expand=True)
        
        frame_boton = tk.Frame(self)
        frame_boton.pack(side="bottom",fill="y" ,expand=True)
        frame_boton.config(background="white")
        
        volver_btn = Button(frame_boton, text="Regresar", command=self.destroy, font=("Arial", 10, "bold"), background="white")
        volver_btn.pack()

class PluviometrosSeleccionados(Frame):
    """
    Clase que permite seleccionar pluviómetros válidos mediante checkboxes en la interfaz gráfica.

    Parámetros:
    - ventana_principal: Instancia de la ventana principal que contiene la configuración global.
    - ventana_actual: Ventana actual desde donde se invoca la clase, para actualizar los datos.
    - parent: Elemento padre donde se inserta el frame.
    - pluvio_validos: Lista de pluviómetros válidos a mostrar como checkboxes.
    - checkboxes: Diccionario que mantiene el estado de cada checkbox (activo o no).

    Métodos:
    - inicializar_checkboxes: Inicializa los checkboxes con valores predeterminados (todos activados).
    - crear_checkboxes: Crea y organiza los checkboxes para cada pluviómetro válido en la interfaz gráfica.
    - actualizar_checkbox: Actualiza el diccionario de checkboxes y llama a la función para actualizar el acumulado total.

    Retorna:
    - None
    """
    def __init__(self,ventana_principal, ventana_actual ,parent, pluvio_validos, checkboxes):
        super().__init__(parent)
        self.ventana_actual = ventana_actual
        self.ventana_principal = ventana_principal
        
        self.pluvio_validos = pluvio_validos
        self.checkboxes = checkboxes
        self.df_config = self.ventana_principal.df_config
        self.checkbox_inicio = self.ventana_principal.checkbox_inicio
        
        self.config(background="white")

        if self.checkbox_inicio:
            self.inicializar_checkboxes()
            self.ventana_principal.checkbox_inicio = False
        self.crear_checkboxes()
    
    def inicializar_checkboxes(self):
        for pluvio in self.pluvio_validos:
            var = IntVar(value=1)
            self.checkboxes[pluvio] = var
    
    def crear_checkboxes(self):
        row, col = 0, 0
        for pluvio in self.pluvio_validos:
            var = self.checkboxes[pluvio]

            checkbutton = Checkbutton(
                self,  
                text=traducir_id_a_lugar(self.df_config, pluvio),
                variable=var,
                font=("Arial", 10, "bold"),
                onvalue=1,
                offvalue=0,
                command=lambda pluvio=pluvio: self.actualizar_checkbox(),
                background="white"
            )
            checkbutton.grid(row=row, column=col, padx=10, pady=10, sticky="w")
            
            col += 1
            if col > 6:
                col = 0
                row += 1

    def actualizar_checkbox(self):
        self.ventana_principal.checkboxes = self.checkboxes
        self.ventana_actual.actualizar_acumulado_total()

class VentanaTR(tk.Toplevel):
    """
    Clase que representa una ventana emergente para visualizar y analizar
    la relación entre precipitación y duración de tormenta.
    
    Parámetros:
    - ventana_tormenta: Instancia de la ventana principal que contiene datos y métodos compartidos.
    - ventana_principal: Referencia a la ventana principal para mantener la configuración global.
    """
    def __init__(self, ventana_tormenta, ventana_principal):
        super().__init__(ventana_tormenta)
        self.ventana_tormenta = ventana_tormenta
        self.ventana_principal = ventana_principal
        
        self.df_instantaneos = self.ventana_tormenta.df_instantaneos
        self.filtrar_pluvios_seleccionados = self.ventana_tormenta.filtrar_pluvios_seleccionados
        
        self.df_config = self.ventana_tormenta.df_config
        
        self.lluvia_filtrada = self.filtrar_pluvios_seleccionados(self.df_instantaneos)
        
        if self.lluvia_filtrada.empty:
            messagebox.showwarning("Advertencia", "Seleccione al menos un pluviómetro.")
            self.cerrar_ventana()
        
        self.state('zoomed')
        self.title("Precipitación vs. Duración de Tormenta")
        self.config(background="white")
        aplicar_icono(self)
        
        
        self.tr_precipitaciones_totales = calcular_precipitacion_para_tr(self.lluvia_filtrada)
        
        self.lista_tr = self.ventana_principal.lista_tr
        
        self.limite_precipitacion_valor = self.ventana_principal.limite_precipitacion_valor
        self.limite_tiempo_valor = self.ventana_principal.limite_tiempo_valor
        self.limite_precipitacion_valor_ampliada = self.ventana_principal.limite_precipitacion_valor_ampliada
        self.limite_tiempo_valor_ampliada = self.ventana_principal.limite_tiempo_valor_ampliada
        self.tr_seleccionado = self.ventana_principal.tr_seleccionado
        self.duraciones_tabla = list(duracion_tormenta)
        self.figsize_tr = (10, 4.2)
        self.fig_dpi_tr = 100
        
        self.crear_interfaz()
        
    def crear_interfaz(self):
        """
        Método para construir la interfaz gráfica dividiendo la ventana en secciones.
        """
        self.scroll_general = tk.Scrollbar(self, orient="vertical")
        self.scroll_general.pack(side="right", fill="y")

        self.canvas_general = tk.Canvas(
            self,
            background="white",
            highlightthickness=0,
            yscrollcommand=self.scroll_general.set,
        )
        self.canvas_general.pack(side="right", fill="both", expand=True)
        self.scroll_general.config(command=self.canvas_general.yview)

        self.frame_contenido = tk.Frame(self.canvas_general)
        self.frame_contenido.config(background="white")
        self.canvas_contenido_window = self.canvas_general.create_window((0, 0), window=self.frame_contenido, anchor="nw")

        self.frame_contenido.bind(
            "<Configure>",
            lambda event: self.canvas_general.configure(scrollregion=self.canvas_general.bbox("all")),
        )
        self.canvas_general.bind(
            "<Configure>",
            lambda event: self.canvas_general.itemconfigure(self.canvas_contenido_window, width=event.width),
        )

        self.frame_top = tk.Frame(self.frame_contenido)
        self.frame_top.pack(side="top", fill="both", expand=True)
        self.frame_top.config(background="white")
        
        self.frame_bottom = tk.Frame(self.frame_contenido)
        self.frame_bottom.pack(side="bottom", fill="x", expand=False)
        self.frame_bottom.config(background="white")
        
        self.crear_frame_izquierdo()
        
        self.crear_frame_graficas()

        self.crear_frame_tabla()
        
        self.crear_frame_botones()
        
    def crear_frame_izquierdo(self):
        """
        Método para construir el panel izquierdo con opciones de selección y controles.
        """
        self.frame_izq = tk.Frame(self.frame_top)
        self.frame_izq.pack(side="left", fill="y", padx=12, pady=10)
        self.frame_izq.config(background="white")
        
        tr_labels = ["TR 2 años", "TR 5 años", "TR 10 años", "TR 20 años", "TR 25 años", "TR 50 años", "TR 100 años"]
        tk.Label(self.frame_izq, text="Seleccionar TRs", font="bold", background="white").pack(padx=12)
        for i, tr in enumerate(tr_labels):
            tk.Checkbutton(self.frame_izq, text=tr, variable=self.lista_tr[i], command=self.actualizar_limites, background="white").pack(anchor="center")
        
        tk.Label(self.frame_izq, text="Seleccionar Limites", font="bold", background="white").pack(pady=5)
        
        tk.Label(self.frame_izq, text="Precipitacion de al Grafica:", background="white").pack(pady=5)
        self.limite_precipitacion_selector = tk.Entry(self.frame_izq)
        self.limite_precipitacion_selector.pack()   
        self.limite_precipitacion_selector.insert(0, self.limite_precipitacion_valor) 
        
        tk.Label(self.frame_izq, text="Tiempo de la Grafica:", background="white").pack(pady=5)
        self.limite_tiempo_selector = tk.Entry(self.frame_izq)
        self.limite_tiempo_selector.pack()   
        self.limite_tiempo_selector.insert(0, self.limite_tiempo_valor) 

        tk.Label(self.frame_izq, text="Precipitacion de la Grafica Ampliada:",background="white").pack(pady=5)
        self.limite_precipitacion_selector_ampliada = tk.Entry(self.frame_izq)
        self.limite_precipitacion_selector_ampliada.pack()   
        self.limite_precipitacion_selector_ampliada.insert(0, self.limite_precipitacion_valor_ampliada) 
        
        tk.Label(self.frame_izq, text="Tiempo de la Grafica Ampliada:",background="white").pack(pady=5)
        self.limite_tiempo_selector_ampliada = tk.Entry(self.frame_izq)
        self.limite_tiempo_selector_ampliada.pack()   
        self.limite_tiempo_selector_ampliada.insert(0, self.limite_tiempo_valor_ampliada) 
        
        self.ultima_grafica = "ninguna"  
        
        tk.Button(self.frame_izq, text="Actualizar limites", command=self.actualizar_limites, font=("Arial", 10, "bold"), width=15,background="white").pack(pady=10)
        
        tk.Label(self.frame_izq, text="Seleccionar Pluviómetro",background="white").pack()
        self.pluv_selector = ttk.Combobox(self.frame_izq, values=list(self.lluvia_filtrada.columns))
        self.pluv_selector.pack(pady=5)
        self.pluv_selector.set(self.lluvia_filtrada.columns[0])
        
        graficar_todos_btn = tk.Button(self.frame_izq, text="Graficar Todos", command= self.graficar_todos, font=("Arial", 10, "bold"), width=15,background="white")
        graficar_todos_btn.pack(pady=10)
        
        self.pluv_selector.bind("<<ComboboxSelected>>", self.graficar_pluv)

    def crear_frame_tabla(self):
        """
        Crea la tabla TR en la parte inferior para evitar que se superponga con las gráficas.
        """
        frame_tabla_container = tk.Frame(self.frame_bottom)
        frame_tabla_container.pack(side="top", fill="x", expand=False, padx=10, pady=5)
        frame_tabla_container.config(background="white")

        frame_controles_tabla = tk.Frame(frame_tabla_container)
        frame_controles_tabla.pack(side="top", fill="x")
        frame_controles_tabla.config(background="white")

        self.tr_tabla_selector = ttk.Combobox(frame_controles_tabla, values=list(precipitacion_tr.keys()), width=20)
        self.tr_tabla_selector.pack(side="left", padx=5, pady=5)
        self.tr_tabla_selector.set(self.tr_seleccionado)
        self.tr_tabla_selector.bind("<<ComboboxSelected>>", self.actualizar_tr_tabla)

        copiar_tabla_btn = tk.Button(frame_controles_tabla, text="Copiar", command=self.copiar_tabla_portapapeles, font=("Arial", 10, "bold"), background="white")
        copiar_tabla_btn.pack(side="left", padx=5, pady=5)

        frame_tabla = tk.Frame(frame_tabla_container)
        frame_tabla.pack(side="top", fill="x", expand=False)
        frame_tabla.config(background="white")

        self.equipos_tabla_ids = list(self.lluvia_filtrada.columns)
        self.equipos_tabla_nombres = {
            equipo_id: traducir_id_a_lugar(self.df_config, equipo_id)
            for equipo_id in self.equipos_tabla_ids
        }
        self.tr_precipitaciones_dict = self.convertir_tr_a_dict_anidado()

        columns = ("Duración (min)", *self.equipos_tabla_ids, "Referencia")
        self.tabla_tr = ttk.Treeview(frame_tabla, columns=columns, show="headings", height=6)

        self.tabla_tr.heading("Duración (min)", text="Duración (min)")
        self.tabla_tr.column("Duración (min)", width=110, anchor="center", stretch=False)

        for equipo_id in self.equipos_tabla_ids:
            self.tabla_tr.heading(equipo_id, text=self.equipos_tabla_nombres[equipo_id])
            self.tabla_tr.column(equipo_id, width=120, anchor="center", stretch=True)

        self.tabla_tr.heading("Referencia", text=self.tr_seleccionado)
        self.tabla_tr.column("Referencia", width=110, anchor="center", stretch=False)

        scrollbar_y = tk.Scrollbar(frame_tabla, orient="vertical", command=self.tabla_tr.yview)
        scrollbar_x = tk.Scrollbar(frame_tabla, orient="horizontal", command=self.tabla_tr.xview)
        self.tabla_tr.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        frame_tabla.grid_rowconfigure(0, weight=1)
        frame_tabla.grid_columnconfigure(0, weight=1)

        self.tabla_tr.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        style = ttk.Style()
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"))

        self.cargar_filas_tabla_tr()

    def convertir_tr_a_dict_anidado(self):
        """
        Convierte self.tr_precipitaciones_totales a un diccionario anidado.
        Estructura: {duracion: {equipo_id: precipitacion}}
        """
        tr_dict = {
            duracion: {equipo_id: "" for equipo_id in self.equipos_tabla_ids}
            for duracion in self.duraciones_tabla
        }

        for equipo_id in self.equipos_tabla_ids:
            precipitaciones_equipo = calcular_precipitacion_pluvio(self.lluvia_filtrada, equipo_id)

            for duracion, valor_precipitaciones, _ in precipitaciones_equipo:
                if duracion in tr_dict:
                    tr_dict[duracion][equipo_id] = round(valor_precipitaciones, 2)

        return tr_dict

    def obtener_referencias_tr_por_duracion(self):
        """
        Retorna valores de referencia del TR seleccionado indexados por duración.
        """
        referencias = precipitacion_tr[self.tr_seleccionado]
        return {
            duracion: referencias[idx]
            for idx, duracion in enumerate(duracion_tormenta)
            if idx < len(referencias) and duracion in self.duraciones_tabla
        }

    def cargar_filas_tabla_tr(self):
        """
        Carga la tabla en formato ancho: filas por duración y columnas por equipo.
        """
        for item in self.tabla_tr.get_children():
            self.tabla_tr.delete(item)

        referencias_por_duracion = self.obtener_referencias_tr_por_duracion()

        for duracion in self.duraciones_tabla:
            fila = [duracion]
            for equipo_id in self.equipos_tabla_ids:
                fila.append(self.tr_precipitaciones_dict[duracion][equipo_id])
            fila.append(referencias_por_duracion.get(duracion, ""))
            self.tabla_tr.insert("", "end", values=fila)
    
    def copiar_tabla_portapapeles(self):
        """
        Copia el contenido de la tabla en el portapapeles en formato de texto tabulado.
        """
        items = self.tabla_tr.get_children()
        
        datos_tabla = []
        
        encabezados = [self.tabla_tr.heading(col, "text") for col in self.tabla_tr["columns"]]
        datos_tabla.append("\t".join(encabezados))
        
        for item in items:
            valores = self.tabla_tr.item(item, "values")
            datos_tabla.append("\t".join(map(str, valores)))
        
        texto_tabla = "\n".join(datos_tabla)
        
        pyperclip.copy(texto_tabla)

    def actualizar_tr_tabla(self, event):
        """
        Actualiza la tabla de tormentas según el TR seleccionado.
        """
        self.tr_seleccionado = self.tr_tabla_selector.get()
        self.tabla_tr.heading("Referencia", text=self.tr_seleccionado)
        self.cargar_filas_tabla_tr()

    def crear_frame_graficas(self):
        """
        Crea el frame donde se mostrarán las gráficas y lo configura.
        """
        self.frame_graficas = tk.Frame(self.frame_top)
        self.frame_graficas.pack(side="right", expand=True, fill="both", padx=10)
        self.frame_graficas.config(background="white")
        self.frame_graficas.grid_rowconfigure(0, weight=1)
        self.frame_graficas.grid_rowconfigure(1, weight=1)
        self.frame_graficas.grid_columnconfigure(0, weight=1)

        self.frame_grafica_superior = tk.Frame(self.frame_graficas)
        self.frame_grafica_superior.grid(row=0, column=0, sticky="nsew")
        self.frame_grafica_superior.config(background="white")

        self.frame_grafica_inferior = tk.Frame(self.frame_graficas)
        self.frame_grafica_inferior.grid(row=1, column=0, sticky="nsew")
        self.frame_grafica_inferior.config(background="white")
        
        self.graficar_todos()

    def mostrar_graficas_en_paneles(self, fig, fig_ampliada):
        """Muestra ambas figuras en paneles del mismo tamaño para mantener alineación visual."""
        for figura in (fig, fig_ampliada):
            figura.set_size_inches(self.figsize_tr[0], self.figsize_tr[1], forward=True)
            figura.set_dpi(self.fig_dpi_tr)
            # Mantener márgenes idénticos evita que una gráfica se vea más larga que la otra.
            figura.subplots_adjust(left=0.10, right=0.98, bottom=0.20, top=0.88)

        for widget in self.frame_grafica_superior.winfo_children():
            widget.destroy()
        for widget in self.frame_grafica_inferior.winfo_children():
            widget.destroy()

        canvas1 = FigureCanvasTkAgg(fig, master=self.frame_grafica_superior)
        canvas1.get_tk_widget().pack(fill="both", expand=True)
        canvas1.draw()

        canvas2 = FigureCanvasTkAgg(fig_ampliada, master=self.frame_grafica_inferior)
        canvas2.get_tk_widget().pack(fill="both", expand=True)
        canvas2.draw()
        
    def actualizar_limites(self):
        """
        Redibuja las gráficas según el último tipo de visualización utilizado.
        """
        if self.ultima_grafica == "pluviómetro":
            self.graficar_pluv()
        else:
            self.graficar_todos()
        
    def graficar_pluv(self, event=None):
        """
        Método para graficar la relación precipitación-duración para un pluviómetro seleccionado.
        """        
        pluvio = self.pluv_selector.get()
        precipitaciones = calcular_precipitacion_pluvio(self.lluvia_filtrada, pluvio)
        
        valores_precipitaciones = [tup[1] for tup in precipitaciones]
        
        fig = grafica_tr([var.get() for var in self.lista_tr], valores_precipitaciones, float(self.limite_precipitacion_selector.get()), float(self.limite_tiempo_selector.get()), pluvio, "Precipitación vs. Duración de Tormenta", figsize=self.figsize_tr)
        fig_ampliada  = grafica_tr([var.get() for var in self.lista_tr], valores_precipitaciones, float(self.limite_precipitacion_selector_ampliada.get()), float(self.limite_tiempo_selector_ampliada.get()), pluvio, "Grafica ampliada", figsize=self.figsize_tr)

        self.mostrar_graficas_en_paneles(fig, fig_ampliada)
        
        self.ultima_grafica = "pluviómetro"

    def graficar_todos(self):
        """
        Genera y muestra dos gráficos de precipitación vs. duración de tormenta.
        
        Parámetros:
        - No recibe parámetros adicionales más allá de `self`.
        
        Funcionamiento:
        - Extrae los valores de precipitaciones de la variable `tr_precipitaciones_totales`.
        - Genera dos gráficas con diferentes límites de precipitación y tiempo.
        - Elimina cualquier gráfico previo en `frame_graficas` antes de agregar los nuevos.
        - Muestra ambas gráficas en la interfaz utilizando `FigureCanvasTkAgg`.
        
        Retorna:
        - None
        """
        
        valores_precipitaciones = [tup[1] for tup in self.tr_precipitaciones_totales]
        
        fig = grafica_tr([var.get() for var in self.lista_tr], valores_precipitaciones, float(self.limite_precipitacion_selector.get()), float(self.limite_tiempo_selector.get()), "RHM", "Precipitación vs. Duración de Tormenta", figsize=self.figsize_tr)
        fig_ampliada  = grafica_tr([var.get() for var in self.lista_tr],  valores_precipitaciones, float(self.limite_precipitacion_selector_ampliada.get()), float(self.limite_tiempo_selector_ampliada.get()), "RHM", "Grafica ampliada", figsize=self.figsize_tr)

        self.mostrar_graficas_en_paneles(fig, fig_ampliada)
        self.ultima_grafica = "total"

    def crear_frame_botones(self):
        """
        Crea un frame con botones de acción en la parte inferior de la interfaz.
        
        Parámetros:
        - No recibe parámetros adicionales más allá de `self`.
        
        Funcionamiento:
        - Crea un frame dentro de `frame_bottom`.
        - Agrega un botón para regresar y otro para guardar gráficas.
        - Configura estilos y posicionamiento.
        
        Retorna:
        - None
        """
        frame_botto = tk.Frame(self.frame_bottom)
        frame_botto.pack(side="bottom", fill="x")
        frame_botto.config(background="white")

        frame_botones_centrados = tk.Frame(frame_botto)
        frame_botones_centrados.pack(pady=12)
        frame_botones_centrados.config(background="white")
        
        Regresar_btn = tk.Button(frame_botones_centrados, text="Regresar",command= self.cerrar_ventana, font=("Arial", 10, "bold"),background="white")
        Regresar_btn.pack(side="left", padx=30)
        
        Guardar_btn = tk.Button(frame_botones_centrados, text="Guardar graficas", command=self.guardar_graficas, font=("Arial", 10, "bold"),background="white")
        Guardar_btn.pack(side="left", padx=30) 

    def guardar_graficas(self):
        """
        Guarda las gráficas generadas en un directorio seleccionado por el usuario.
        
        Parámetros:
        - No recibe parámetros adicionales más allá de `self`.
        
        Funcionamiento:
        - Solicita un directorio donde guardar las imágenes.
        - Genera las gráficas de precipitación según la última visualización.
        - Guarda los archivos de las gráficas en formato PNG.
        - Muestra un mensaje de confirmación tras la exportación.
        
        Retorna:
        - None
        """
        directorio = filedialog.askdirectory(title="Selecciona un directorio para guardar las gráficas")
        self.lift()
        
        if directorio:
            if self.ultima_grafica == "pluviómetro":
                pluvio = self.pluv_selector.get()
                nombre_archivo = f"grafica_{pluvio}.png"
                nombre_archivo_ampliada = f"grafica_ampliada_{pluvio}.png"
                precipitaciones = calcular_precipitacion_pluvio(self.lluvia_filtrada, pluvio)
                valores_precipitaciones = [tup[1] for tup in precipitaciones]
                fig = grafica_tr([var.get() for var in self.lista_tr], valores_precipitaciones, 
                                float(self.limite_precipitacion_selector.get()), float(self.limite_tiempo_selector.get()), pluvio, "Precipitación vs. Duración de Tormenta", figsize=(8,6))
                fig_ampliada = grafica_tr([var.get() for var in self.lista_tr], valores_precipitaciones, 
                                    float(self.limite_precipitacion_selector_ampliada.get()), float(self.limite_tiempo_selector_ampliada.get()), pluvio, "Grafica ampliada", figsize=(8,6))
            else:
                nombre_archivo = "grafica_total.png"
                nombre_archivo_ampliada = "grafica_ampliada_total.png"
                valores_precipitaciones = [tup[1] for tup in self.tr_precipitaciones_totales]
                fig = grafica_tr([var.get() for var in self.lista_tr], valores_precipitaciones, float(self.limite_precipitacion_selector.get()), float(self.limite_tiempo_selector.get()), "RHM", "Precipitación vs. Duración de Tormenta", figsize=(8,6))
                fig_ampliada  = grafica_tr([var.get() for var in self.lista_tr], valores_precipitaciones, float(self.limite_precipitacion_selector_ampliada.get()), float(self.limite_tiempo_selector_ampliada.get()), "RHM", "Grafica ampliada", figsize=(8,6))

            fig.savefig(f"{directorio}/{nombre_archivo}")
            
            fig_ampliada.savefig(f"{directorio}/{nombre_archivo_ampliada}")
            
            messagebox.showinfo("Éxito", "Las gráficas se han guardado correctamente.")
            self.lift()
                        
    def cerrar_ventana(self):
        """
        Guarda la configuración actual y cierra la ventana.
        """
        self.ventana_principal.lista_tr = self.lista_tr
        
        self.ventana_principal.limite_precipitacion_valor = self.limite_precipitacion_selector.get()
        self.ventana_principal.limite_tiempo_valor = self.limite_tiempo_selector.get()
        self.ventana_principal.limite_precipitacion_valor_ampliada = self.limite_precipitacion_selector_ampliada.get()
        self.ventana_principal.limite_tiempo_valor_ampliada = self.limite_tiempo_selector_ampliada.get()
        
        self.ventana_principal.tr_seleccionado = self.tr_tabla_selector.get()
        
        self.destroy()

class VentanaPrincipalTormenta(tk.Toplevel):
    def __init__(self, ventana_principal):
        super().__init__(ventana_principal)
        self.ventana_principal = ventana_principal
        
        self.checkbox_inicio = self.ventana_principal.checkbox_inicio
        
        
        self.title("Ventana principal")
        self.state('zoomed')
        self.config(background="white")
        aplicar_icono(self)
        
        self.grilla_temporal_inst = self.ventana_principal.grilla_temporal_inst
        
        self.valor_acumulado_inumet_tormenta = self.ventana_principal.valor_acumulado_inumet_tormenta
        
        #self.df_acumulados_diarios = self.ventana_principal.df_acumulados_diarios  
        
        
        self.df_config = self.ventana_principal.df_config
        self.df_datos = self.ventana_principal.df_datos
        self.pluvio_validos, self.pluvio_no_validos = obtener_pluviometros_validos(self.df_datos)
        self.df_acumulados = acumulados(self.df_datos)
        self.df_instantaneos = calcular_instantaneos(self.df_datos)
        
        self.df_acumulados_diarios = calcular_acumulados_diarios(self.df_instantaneos)
        self.df_acumulados_diarios_total = acumulado_diarios_total(self.df_acumulados_diarios).tail(1)
        
        self.df_saltos_maximos, self.df_saltos = detectar_saltos_temporales(self.df_datos[self.pluvio_validos], self.df_config)
        self.df_porcentaje_vacio = calcular_porcentaje_vacios(self.df_datos[self.pluvio_validos], self.df_config)
        

        self.checkboxes = self.ventana_principal.checkboxes
        
        self.protocol("WM_DELETE_WINDOW", self.ventana_principal.cerrar_todo) 
        
        self.crear_interfaz()

    def filtrar_pluvios_seleccionados(self, df):
        # Obtener los pluviómetros seleccionados (los que tienen valor 1 en self.checkboxes)
        pluvios_seleccionados = [pluvio for pluvio, var in self.ventana_principal.checkboxes.items() if var.get() == 1]
        
        # Filtrar las columnas del dataframe self.df_instantaneos para solo mantener las seleccionadas
        df_seleccionados = df[pluvios_seleccionados]
        
        return df_seleccionados 

    def crear_interfaz(self):
        self.crear_info_frame()
        self.crear_checkboxes()
        self.crear_botonera()
    
    def crear_info_frame(self):
        self.info_frame = Frame(self)
        self.info_frame.pack(side="top", expand=True, fill="both", padx=20, pady=10)
        self.info_frame.config(background="white")

        info_label = tk.Label(self.info_frame, text="Información sobre los datos de precipitación:", font=("Arial", 14, "bold"),background="white")
        info_label.pack(fill="both", padx=10, pady=10)

        self.mostrar_saltos_temporales()
        self.mostrar_porcentaje_nulos()
        self.mostrar_acumulados_totales()
        self.mostrar_pluvio_no_validos()
 
    def mostrar_grafica_saltos(self, event):
        # Obtener el ítem que se seleccionó
        item = self.tabla.selection()  # Obtiene el ítem seleccionado
        if item:
            # Obtener los valores de la fila seleccionada
            item_values = self.tabla.item(item)["values"]
            grafica_value = item_values[-1]  # "Mostrar grafica" es la última columna
            if grafica_value == " ... ":
                ventana_grafica_saltos = tk.Toplevel()
                ventana_grafica_saltos.config(background="white")
                ventana_grafica_saltos.state('zoomed')
                ventana_grafica_saltos.title("Gráfico de Lluvia Acumulada")
                aplicar_icono(ventana_grafica_saltos)
                
                frame_combobox = tk.Frame(ventana_grafica_saltos)
                frame_combobox.pack(fill="x", pady=10)
                frame_combobox.config(background="white")
                
                tk.Label(frame_combobox, text=f"Saltos detectados en el pluviometro {item_values[0]}", font=("Arial", 10, "bold"), background="white").pack()
                pluv_selector = ttk.Combobox(frame_combobox, values=["Todos los pluviometros", item_values[0]], width=30)
                pluv_selector.pack(pady=5)
                pluv_selector.configure(font=("Arial", 10))
                pluv_selector.set("Todos los pluviometros")
                
                # Frame derecho para gráfica
                frame_grafica = tk.Frame(ventana_grafica_saltos)
                frame_grafica.pack(expand=True, fill="both")
                frame_grafica.config(background="white")

                def actualizar_grafica(event=None):
                    if pluv_selector.get()=="Todos los pluviometros":
                        fig = graficar_lluvia_con_saltos_tormenta(self.df_instantaneos, self.df_saltos, self.df_saltos_maximos, item_values[0], self.df_config, True)
                    else:
                        fig = graficar_lluvia_con_saltos_tormenta(self.df_instantaneos, self.df_saltos, self.df_saltos_maximos, item_values[0], self.df_config, False)
                        
                    for widget in frame_grafica.winfo_children():
                        widget.destroy()

                    canvas = FigureCanvasTkAgg(fig, master=frame_grafica)
                    canvas.get_tk_widget().pack(fill="both", expand=True)
                    canvas.draw()

                actualizar_grafica()
                
                pluv_selector.bind("<<ComboboxSelected>>", actualizar_grafica)

                volver_btn = Button(ventana_grafica_saltos, text="Regresar", command=ventana_grafica_saltos.destroy, font=("Arial", 10, "bold"), background="white")
                volver_btn.pack(pady=10)

    def mostrar_pluvio_no_validos(self):
        self.no_validos_frame = Frame(self.info_frame)
        self.no_validos_frame.pack(pady=5)
        self.no_validos_frame.config(background="white")
        
        tk.Label(self.no_validos_frame, text="Pluviómetros no válidos:", font=("Arial", 10, "bold"), background="white").pack(side= "left")
        # Convertir cada ID en 'pluvio_no_validos' a su nombre de lugar
        lugares_no_validos = [traducir_id_a_lugar(self.df_config, id_pluvio) for id_pluvio in self.pluvio_no_validos]
        # Crear una cadena de texto con los lugares no válidos, separada por comas
        lugares_no_validos = ", ".join(lugares_no_validos)
        pluvios_no_validos_label = tk.Label(self.no_validos_frame, text=lugares_no_validos, font=("Arial", 10), justify="left", background="white")
        pluvios_no_validos_label.pack(side="left", fill="both", padx=5)

    def mostrar_saltos_temporales(self):
        tk.Label(self.info_frame, text="Saltos temporales", font=("Arial", 10, "bold"),background="white").pack(pady=5)

        frame_tabla_saltos = tk.Frame(self.info_frame)
        frame_tabla_saltos.pack(fill="both", expand=True, pady=10)
        frame_tabla_saltos.config(background="white")

        self.tabla = ttk.Treeview(frame_tabla_saltos, columns=("Pluviómetro", "Cantidad de saltos", "Duración total (min)", "Duración máx (min)", "Inicio máx", "Fin máx", "Grafica"), show="headings", height= 8)
        self.tabla.heading("Pluviómetro", text="Pluviómetro")
        self.tabla.heading("Cantidad de saltos", text="Cantidad de saltos")
        self.tabla.heading("Duración total (min)", text="Duración total de saltos (min)")
        self.tabla.heading("Duración máx (min)", text="Duración salto mas largo (min)")
        self.tabla.heading("Inicio máx", text="Inicio")
        self.tabla.heading("Fin máx", text="Fin")
        self.tabla.heading("Grafica", text="Mostrar saltos en la grafica")

        self.tabla.column("Pluviómetro", width=150, anchor="center")
        self.tabla.column("Cantidad de saltos", width=100, anchor="center")
        self.tabla.column("Duración total (min)", width=150, anchor="center")
        self.tabla.column("Duración máx (min)", width=150, anchor="center")
        self.tabla.column("Inicio máx", width=150, anchor="center")
        self.tabla.column("Fin máx", width=150, anchor="center")
        self.tabla.column("Grafica", width=150, anchor="center")

        scrollbar = tk.Scrollbar(frame_tabla_saltos, orient="vertical", command=self.tabla.yview)
        scrollbar.pack(side="right", fill="y")
        self.tabla.configure(yscrollcommand=scrollbar.set)

        data = []
        if not self.df_saltos_maximos.empty:
            for index, row in self.df_saltos_maximos.iterrows():
                data.append((row["Pluviómetro"], row["Cantidad de saltos"], row["Duración total (min)"], row["Duración máx (min)"], row["Inicio máx"], row["Fin máx"], " ... "))
            
            data.sort(key=lambda x: x[2], reverse=True)
            for row in data:
                self.tabla.insert("", "end", values=row)
        else:
            self.tabla.insert("", "end", values=("No se detectaron saltos temporales", "", "", "", "", "",""))

        self.tabla.pack(fill="both", expand=True)
        self.tabla.bind("<Double-1>", self.mostrar_grafica_saltos)

    def mostrar_porcentaje_nulos(self):
        tk.Label(self.info_frame, text="Porcentaje de nulos por pluviómetro", font=("Arial", 10, "bold"), background="white").pack()
        frame_tabla_porcentaje_nulos = tk.Frame(self.info_frame)
        frame_tabla_porcentaje_nulos.pack(fill="both", expand=True)
        frame_tabla_porcentaje_nulos.config(background="white")

        tabla_nulos = ttk.Treeview(frame_tabla_porcentaje_nulos, columns=("Pluviómetro", "Porcentaje_Nulos"), show="headings", height= 8)
        tabla_nulos.heading("Pluviómetro", text="Pluviómetro")
        tabla_nulos.heading("Porcentaje_Nulos", text="Porcentaje Nulos (%)")
        tabla_nulos.column("Pluviómetro", width=150, anchor="center")
        tabla_nulos.column("Porcentaje_Nulos", width=150, anchor="center")

        scrollbar_nulos = tk.Scrollbar(frame_tabla_porcentaje_nulos, orient="vertical", command=tabla_nulos.yview)
        scrollbar_nulos.pack(side="right", fill="y")
        tabla_nulos.configure(yscrollcommand=scrollbar_nulos.set)

        self.df_porcentaje_vacio = self.df_porcentaje_vacio.sort_values(by="Porcentaje_Nulos", ascending=False)
        for index, row in self.df_porcentaje_vacio.iterrows():
            tabla_nulos.insert("", "end", values=(row["Pluviómetro"], round(row["Porcentaje_Nulos"], 2)))

        tabla_nulos.pack(fill="both", expand=True, pady=5)

    def mostrar_acumulados_totales(self):
        tk.Label(self.info_frame, text="Acumulados totales:", font=("Arial", 10, "bold"),background="white").pack(pady=5)

        # Crear un Frame para contener tanto el Treeview como el botón
        frame_contenedor = tk.Frame(self.info_frame)
        frame_contenedor.pack(fill="both", expand=True)
        frame_contenedor.config(background="white")

        # Crear un Frame para el botón
        frame_boton = tk.Frame(frame_contenedor)
        frame_boton.pack(side="left")
        frame_boton.config(background="white")

        # Crear un botón en el frame_boton
        copiar_btn = tk.Button(frame_boton, text="Copiar", command=self.copiar_tabla_acumulado_al_portapapeles, background="white")
        copiar_btn.pack(side="left")
        
        # Crear un Frame para la tabla (Treeview)
        frame_tabla_acumulado_total = tk.Frame(frame_contenedor)
        frame_tabla_acumulado_total.pack(side="right", fill="both", expand=True, padx=10)
        
        # Crear un Treeview con columnas dinámicas
        self.tabla_acumulado_total = ttk.Treeview(frame_tabla_acumulado_total, show="headings", height=1)
        
        if self.checkbox_inicio:
            df_acumulados_filtrado = self.df_acumulados[self.pluvio_validos]
        else:   
            # Agregar columnas
            df_acumulados_filtrado = self.filtrar_pluvios_seleccionados(self.df_acumulados)
        
        self.df_acumulados_total = acumulado_total(df_acumulados_filtrado)
        self.df_acumulados_total = self.df_acumulados_total.round(1)
        
        if self.valor_acumulado_inumet_tormenta:
            self.df_acumulados_total["INUMET"] = self.valor_acumulado_inumet_tormenta
        else:
            self.df_acumulados_total["INUMET"] = ""
        
        self.tabla_acumulado_total["columns"] = self.df_acumulados_total.columns.tolist()
        
        # Configurar los encabezados de las columnas
        for col in self.df_acumulados_total.columns:
            self.tabla_acumulado_total.heading(col, text=col)
            self.tabla_acumulado_total.column(col, width=50, anchor="center")  # Ajustar ancho y alineación

        # Insertar los datos
        for i, row in self.df_acumulados_total.iterrows():
            self.tabla_acumulado_total.insert("", "end", values=row.tolist())
            
        # Vincular eventos para editar la columna "INUMET"
        self.tabla_acumulado_total.bind("<Double-1>", self.editar_celda_inumet) 

        # Crear un Scrollbar horizontal
        scrollbar = tk.Scrollbar(frame_tabla_acumulado_total, orient="horizontal", command=self.tabla_acumulado_total.xview, background="white")
        self.tabla_acumulado_total.config(xscrollcommand=scrollbar.set)
        scrollbar.pack(side="bottom", fill="x")

        # Empaquetar el Treeview
        self.tabla_acumulado_total.pack(fill="both", expand=True)

    def editar_celda_inumet(self, event):
        # Obtener la celda seleccionada
        item_id = self.tabla_acumulado_total.identify_row(event.y)
        column_id = self.tabla_acumulado_total.identify_column(event.x)

        # Obtener las columnas como lista
        columnas = list(self.tabla_acumulado_total["columns"])

        # Verificar si la columna es "INUMET"
        if column_id == f"#{columnas.index('INUMET') + 1}":
            # Obtener el valor actual
            valores = self.tabla_acumulado_total.item(item_id, "values")
            valor_actual = valores[columnas.index("INUMET")]

            # Crear un Entry temporal
            x, y, width, height = self.tabla_acumulado_total.bbox(item_id, column_id)
            entry = tk.Entry(self.tabla_acumulado_total)
            entry.place(x=x, y=y, width=width, height=height)
            entry.insert(0, valor_actual)

            # Función para guardar el nuevo valor
            def guardar_valor(event=None):
                try:
                    nuevo_valor = entry.get()
                    if nuevo_valor == "":
                        self.tabla_acumulado_total.set(item_id, column="INUMET", value="")
                        self.valor_acumulado_inumet_tormenta = None
                        self.ventana_principal.valor_acumulado_inumet_tormenta =None
                    else:
                        self.tabla_acumulado_total.set(item_id, column="INUMET", value=float(nuevo_valor))
                        self.valor_acumulado_inumet_tormenta = float(nuevo_valor)
                        self.ventana_principal.valor_acumulado_inumet_tormenta = float(nuevo_valor)
                    entry.destroy()
                except:
                    self.tabla_acumulado_total.set(item_id, column="INUMET", value=self.valor_acumulado_inumet_tormenta)
                    messagebox.showerror("Error", "El valor ingresado no es un número valido.")
                    entry.destroy()

            entry.bind("<Return>", guardar_valor)  # Guardar valor al presionar Enter
            entry.bind("<FocusOut>", lambda e: entry.destroy())  # Destruir el Entry si pierde el foco
            entry.focus()

    def actualizar_acumulado_total(self):
        # Elimina todos los elementos existentes
        for item in self.tabla_acumulado_total.get_children():
            self.tabla_acumulado_total.delete(item)
        df_acumulados_filtrado = self.filtrar_pluvios_seleccionados(self.df_acumulados)
        
        self.df_acumulados_total = acumulado_total(df_acumulados_filtrado)
        self.df_acumulados_total = self.df_acumulados_total.round(1)
        
        if self.valor_acumulado_inumet_tormenta:
            self.df_acumulados_total["INUMET"] = self.valor_acumulado_inumet_tormenta
        else:
            self.df_acumulados_total["INUMET"] = ""
        
        self.tabla_acumulado_total["columns"] = self.df_acumulados_total.columns.tolist()
        
        # Configurar los encabezados de las columnas
        for col in self.df_acumulados_total.columns:
            self.tabla_acumulado_total.heading(col, text=col)
            self.tabla_acumulado_total.column(col, width=50, anchor="center")  # Ajustar ancho y alineación

        # Insertar los datos
        for i, row in self.df_acumulados_total.iterrows():
            self.tabla_acumulado_total.insert("", "end", values=row.tolist())
          
    def copiar_tabla_acumulado_al_portapapeles(self):
        # Extraer los datos de la tabla (celdas) y convertirlo en un formato adecuado para copiar
        table_data = []

        # Agregar encabezados de columna
        headers = self.df_acumulados_total.columns.tolist()
        table_data.append("\t".join(headers))
        
        # Agregar filas de datos
        for row_id in self.tabla_acumulado_total.get_children():
            row_values = self.tabla_acumulado_total.item(row_id)["values"]
            table_data.append("\t".join(map(str, row_values)))
        
        # Convertir la lista de filas en un string con saltos de línea
        table_str = "\n".join(table_data)
        
        # Copiar el texto al portapapeles usando pyperclip
        pyperclip.copy(table_str)
            
    def crear_checkboxes(self):
        frame_checkboxes = tk.Frame(self)
        frame_checkboxes.pack(fill="both", expand=True)
        frame_checkboxes.config(background="white")
        
        frame_pluvios = PluviometrosSeleccionados(self.ventana_principal, self, frame_checkboxes, self.pluvio_validos, self.checkboxes)
        frame_pluvios.pack()
     
    def crear_botonera(self):
        botonera_1_frame = Frame(self)
        botonera_1_frame.pack(side="bottom", expand=True, fill="both")
        botonera_1_frame.config(background="white")
        
        botonera_frame = Frame(botonera_1_frame)
        botonera_frame.pack(side="bottom", expand=True, fill="y", padx=10, pady=10)
        botonera_frame.config(background="white")
        
        volver_btn = tk.Button(botonera_frame, text="Volver", command=lambda: [self.cerrar_ventana(), VentanaLimiteTemporal(self.ventana_principal)],background="white" ,font=("Arial", 10, "bold"))
        volver_btn.pack(side="left", padx=10, pady=10)

        
        def mostrar_grafica_instantanea_segura():
            try:
                datos_filtrados = self.filtrar_pluvios_seleccionados(self.df_instantaneos)
                fig = graficar_lluvia_instantanea_tormenta(datos_filtrados, self.grilla_temporal_inst)
                MostrarGrafica(fig)
            except Exception as e:
                messagebox.showerror("Error", f"Ocurrió un error al generar la gráfica:\n\n{str(e)}")
        
        grafica_instantanea_btn = Button(botonera_frame, text="Ver Gráfico Lluvia Instantánea", 
                                         command=mostrar_grafica_instantanea_segura,
                                         font=("Arial", 10, "bold"), background="white")
        grafica_instantanea_btn.pack(side="left", padx=10, pady=10)

        def mostrar_grafica_acumulada_segura():
            try:
                fig = graficar_lluvia_acumulado_tormenta((self.filtrar_pluvios_seleccionados(self.df_acumulados)), self.grilla_temporal_inst)
                MostrarGrafica(fig)
            except Exception as e:
                messagebox.showerror("Error", f"Ocurrió un error al generar la gráfica:\n\n{str(e)}")
        
        grafica_acumulada_btn = Button(botonera_frame, text="Ver Gráfico Lluvia Acumulada", 
                                       command=mostrar_grafica_acumulada_segura,
                                       font=("Arial", 10, "bold"),background="white")
        grafica_acumulada_btn.pack(side="left", padx=10, pady=10)
        
        def mostrar_grafica_isoyetas_segura():
            try:
                fig = graficar_isoyetas(self.nombres_config_isoyetas(), self.seleccionar_pluv_isoyetas())
                MostrarGrafica(fig)
            except Exception as e:
                messagebox.showerror("Error", f"Ocurrió un error al generar la gráfica:\n\n{str(e)}")
        
        grafica_isoyetas_btn = Button(botonera_frame, text="Ver Gráfico Isoyetas", 
                                         command=lambda: mostrar_grafica_isoyetas_segura(), font=("Arial", 10, "bold"),background="white")
        grafica_isoyetas_btn.pack(side="left", padx=10, pady=10)
        
        grafica_tr_btn = Button(botonera_frame, text="Ver Gráfico Tr", 
                                       command=lambda: VentanaTR(self, self.ventana_principal),
                                       font=("Arial", 10, "bold"),background="white")
        grafica_tr_btn.pack(side="left", padx=10, pady=10)
        
        grafica_isoyetas_x_duracion_btn = Button(botonera_frame, text="Ver Gráfico Isoyetas x duracion de tormenta", 
                                         command=lambda: self.mostrar_grafica_isoyetas_tr(), font=("Arial", 10, "bold"),background="white")
        grafica_isoyetas_x_duracion_btn.pack(side="left", padx=10, pady=10)

        Guardar_btn = tk.Button(botonera_frame, text="Guardar Graficas", command=lambda: self.guardar_graficas(), font=("Arial", 10, "bold"),background="white")
        Guardar_btn.pack(side="left", padx=10, pady=10)       
    
    def seleccionar_pluv_isoyetas(self):
        acumulado_isoyetas = self.filtrar_pluvios_seleccionados(self.df_acumulados_diarios_total)
        return acumulado_isoyetas
    
    def nombres_config_isoyetas(self):
        acumulado_isoyetas = self.filtrar_pluvios_seleccionados(self.df_acumulados_diarios_total)
        df_config_filtrado = self.df_config[self.df_config['ID'].isin(acumulado_isoyetas.columns)]
        return df_config_filtrado

    def mostrar_grafica_isoyetas_tr(self):
        ventana_grafica_isoyetas_tiempo = tk.Toplevel()
        ventana_grafica_isoyetas_tiempo.config(background="white")
        ventana_grafica_isoyetas_tiempo.state('zoomed')
        ventana_grafica_isoyetas_tiempo.title("Gráfico isoyetas x Duracion de Tormenta")
        aplicar_icono(ventana_grafica_isoyetas_tiempo)
         
        frame_combobox = tk.Frame(ventana_grafica_isoyetas_tiempo)
        frame_combobox.pack(fill="x", pady=10)
        frame_combobox.config(background="white")
        
        titulo = tk.Label(frame_combobox, text=f"Grafico isoyetas para una duracion de tormenta {list(precipitacion_tr_x_duracion.keys())[0]}", font=("Arial", 10, "bold"), background="white")
        titulo.pack()
        duracion_selector = ttk.Combobox(frame_combobox, values=list(precipitacion_tr_x_duracion.keys()), width=30)
        duracion_selector.pack(pady=5)
        duracion_selector.configure(font=("Arial", 10))
        duracion_selector.set(list(precipitacion_tr_x_duracion.keys())[0])
        
        # Frame derecho para gráfica
        frame_grafica = tk.Frame(ventana_grafica_isoyetas_tiempo)
        frame_grafica.pack(expand=True, fill="both")
        frame_grafica.config(background="white")

        def actualizar_grafica(event=None):
            duracion_a_buscar = duracion_selector.get()
            df_lluvia_filtrada = self.filtrar_pluvios_seleccionados(self.df_instantaneos)
            df_acumulado_isoyetas = self.seleccionar_pluv_isoyetas()   
            df_acumulado_isoyetas = df_acumulado_isoyetas.copy()
            
            duracion_numero = int(duracion_a_buscar.split()[0])
            
            # Creamos un diccionario para actualizar los valores de precipitación
            nueva_precipitacion_dict = {}
                        
            for pluvio in df_lluvia_filtrada.columns:
                # Obtener la lista de tormentas para un pluviómetro específico
                tormentas_pluvio = calcular_precipitacion_pluvio(df_lluvia_filtrada, pluvio)
                
                # Buscar el valor de precipitación correspondiente a la duración seleccionada
                for t in tormentas_pluvio:
                    if t[0] == duracion_numero:
                        nueva_precipitacion_dict[pluvio] = t[1]  # Asignamos el valor de precipitación al diccionario
                        break  # Ya encontramos la tormenta, no necesitamos seguir buscando
                                
            # Actualizamos la primera fila de df_acumulado_isoyetas con los nuevos valores de precipitación
            for pluvio, precipitacion in nueva_precipitacion_dict.items():
                df_acumulado_isoyetas.loc["Total", pluvio] = precipitacion  # Actualizamos el valor en la fila 0
            
            try:
                self.fig_isoyeta_tr = graficar_isoyetas_tr(self.nombres_config_isoyetas(), df_acumulado_isoyetas, precipitacion_tr_x_duracion[duracion_a_buscar])
            except Exception as e:
                messagebox.showerror("Error", f"Ocurrió un error al generar la gráfica:\n\n{str(e)}")
                
            for widget in frame_grafica.winfo_children():
                widget.destroy()

            canvas = FigureCanvasTkAgg(self.fig_isoyeta_tr, master=frame_grafica)
            canvas.get_tk_widget().pack(fill="both", expand=True)
            canvas.draw()
            titulo.config(text=f"Grafico isoyetas para una duracion de tormenta {duracion_a_buscar}")
                        
        actualizar_grafica()
        duracion_selector.bind("<<ComboboxSelected>>", actualizar_grafica)
        
        def guardar_grafica():
            # Cuadro de diálogo para seleccionar directorio y nombre del archivo
            directorio = filedialog.askdirectory(title="Selecciona un directorio para guardar las gráficas")
            
            duracion = duracion_selector.get()
            
            self.fig_isoyeta_tr.savefig(f"{directorio}/Grafico isoyetas para una duracion de tormenta {duracion}.png")
            messagebox.showinfo("Exito", "Procesado correctamente.")
        
        frame_botones = tk.Frame(ventana_grafica_isoyetas_tiempo)
        frame_botones.pack(fill="y", pady=10)
        frame_botones.config(background="white")
        
        volver_btn = Button(frame_botones, text="Regresar", command=ventana_grafica_isoyetas_tiempo.destroy, font=("Arial", 10, "bold"), background="white")
        volver_btn.pack(side= "left", padx=10, pady=10)
        
        guardar_btn = Button(frame_botones, text="Guardar grafica", command=lambda: guardar_grafica(), font=("Arial", 10, "bold"), background="white")
        guardar_btn.pack(side= "left", padx=10, pady=10)
          
    def guardar_graficas(self):       
        lluvia_filtrada_inst = self.filtrar_pluvios_seleccionados(self.df_instantaneos)

        if lluvia_filtrada_inst.empty:
            messagebox.showwarning("Advertencia", "Seleccione al menos un pluviómetro.")
            return

        # Cuadro de diálogo para seleccionar directorio
        directorio = filedialog.askdirectory(title="Selecciona un directorio para guardar las gráficas")
        if not directorio:
            return  # El usuario canceló

        errores = []

        # Gráfico de lluvia instantánea
        try:
            fig_inst = graficar_lluvia_instantanea_tormenta(lluvia_filtrada_inst, self.grilla_temporal_inst)
            fig_inst.savefig(f"{directorio}/grafica instantaneas.png")
        except Exception as e:
            errores.append(f"Gráfica lluvia instantánea: {str(e)}")

        # Gráfico acumulado
        try:
            lluvia_filtrada_acum = self.filtrar_pluvios_seleccionados(self.df_acumulados)
            fig_acum = graficar_lluvia_acumulado_tormenta(lluvia_filtrada_acum, self.grilla_temporal_inst)
            fig_acum.savefig(f"{directorio}/grafica acumulado.png")
        except Exception as e:
            errores.append(f"Gráfica lluvia acumulada: {str(e)}")

        # Gráfico isoyetas
        try:
            fig_isoyetas = graficar_isoyetas(self.nombres_config_isoyetas(), self.seleccionar_pluv_isoyetas())
            fig_isoyetas.savefig(f"{directorio}/grafica mensual isoyetas.png")
        except Exception as e:
            errores.append(f"Gráfica isoyetas: {str(e)}")

        if errores:
            messagebox.showwarning("Finalizado con errores", "Se completó el guardado, pero ocurrieron errores:\n\n" + "\n".join(errores))
        else:
            messagebox.showinfo("Éxito", "Gráficas guardadas correctamente.")
   

    def cerrar_ventana(self):
        self.destroy()

class VentanaPrincipalMensual(tk.Toplevel):
    def __init__(self, ventana_principal):
        super().__init__(ventana_principal)
        self.ventana_principal = ventana_principal
        
        df_datos_sin_cortar = self.ventana_principal.df_datos
        self.df_instantaneo_sin_cortar = calcular_instantaneos(df_datos_sin_cortar) 
        
        self.mes = obtener_mes(df_datos_sin_cortar)  
        
        self.df_acumulados_INUMET = self.ventana_principal.df_acumulados_INUMET
              
        # Datos mes INUMET
        self.df_instantaneo_mes_inumet = cortar_datos_mes_inumet(self.mes, self.df_instantaneo_sin_cortar)
        self.df_instantaneo_mes_inumet = cortar_datos_mes_real(self.mes, self.df_instantaneo_mes_inumet)
        
        self.df_acumulados_diarios_mes_inumet = calcular_acumulados_diarios(self.df_instantaneo_mes_inumet)
        
        self.df_acumulados_diarios_mes_inumet.index = pd.to_datetime(self.df_acumulados_diarios_mes_inumet.index).strftime('%Y-%m-%d')
    
        self.df_acumulados_diarios_mes_inumet = self.df_acumulados_diarios_mes_inumet.join(self.df_acumulados_INUMET, how='left')
    
        self.df_acumulados_diarios_mes_inumet.fillna(0, inplace=True)

        self.df_correlacion = tabla_correlacion(self.df_acumulados_diarios_mes_inumet)

        # Datos mes Real
        self.df_instantaneo_mes_real = cortar_datos_mes_real(self.mes, self.df_instantaneo_sin_cortar)
            
        self.checkbox_inicio = self.ventana_principal.checkbox_inicio
        
        self.df_config = self.ventana_principal.df_config      
        
        self.pluvio_validos, self.pluvio_no_validos = obtener_pluviometros_validos(df_datos_sin_cortar)
        
        self.df_acumulados_diarios_mes_real = calcular_acumulados_diarios(self.df_instantaneo_mes_real)
        
        self.df_acumulados_diarios_mes_real.index = pd.to_datetime(self.df_acumulados_diarios_mes_real.index).strftime('%Y-%m-%d')
    
        self.df_acumulados_diarios_mes_real = self.df_acumulados_diarios_mes_real.join(self.df_acumulados_INUMET, how='left')
    
        self.df_acumulados_diarios_mes_real.fillna(0, inplace=True)
                
        self.df_acumulados_diarios_total_mes_real = acumulado_diarios_total(self.df_acumulados_diarios_mes_real).tail(1)
        
        
        df_datos_mes_real = cortar_datos_mes_real(self.mes, df_datos_sin_cortar)
        self.df_porcentaje_vacio = calcular_porcentaje_vacios(df_datos_mes_real[self.pluvio_validos], self.df_config)
        
        self.checkboxes = self.ventana_principal.checkboxes

        self.title("Ventana principal")
        self.state('zoomed')
        self.config(background="white")
        aplicar_icono(self)
        
        self.protocol("WM_DELETE_WINDOW", self.ventana_principal.cerrar_todo) 
        
        self.crear_interfaz()

    def filtrar_pluvios_seleccionados(self, df):
        # Obtener los pluviómetros seleccionados (los que tienen valor 1 en self.checkboxes)
        pluvios_seleccionados = [pluvio for pluvio, var in self.ventana_principal.checkboxes.items() if var.get() == 1]
                
        # Asegurar que INUMET siempre esté incluido
        pluvios_seleccionados.append("INUMET")

        # Filtrar las columnas del dataframe self.df_instantaneos para solo mantener las seleccionadas
        df_seleccionados = df[pluvios_seleccionados]
        return df_seleccionados

    def crear_interfaz(self):
        self.crear_info_frame()
        self.crear_checkboxes()
        self.crear_botonera()
    
    def crear_info_frame(self):
        self.info_frame = Frame(self)
        self.info_frame.pack(side="top", expand=True, fill="both", padx=20, pady=20)
        self.info_frame.config(background="white")

        info_label = tk.Label(self.info_frame, text="Información sobre los datos mensuales:", font=("Arial", 14, "bold"),background="white")
        info_label.pack(fill="both", padx=10, pady=10)
        
        self.mostrar_tabla_correlacion()
        
        self.mostrar_porcentaje_faltantes()
        
        self.mostrar_acumulados_totales()
        
        self.mostrar_tabla_percentiles()
        
    def mostrar_porcentaje_faltantes(self):
        tk.Label(
            self.info_frame, text="Porcentaje de nulos por pluviómetro",
            font=("Arial", 10, "bold"), background="white"
        ).pack()

        frame_tabla_porcentaje_nulos = tk.Frame(self.info_frame)
        frame_tabla_porcentaje_nulos.pack(fill="both", expand=True)
        frame_tabla_porcentaje_nulos.config(background="white")

        # Crear columnas dinámicamente
        columnas = list(self.df_porcentaje_vacio["Pluviómetro"])

        tabla_nulos = ttk.Treeview(frame_tabla_porcentaje_nulos, columns=columnas, show="headings", height=1)

        # Encabezados
        for col in columnas:
            tabla_nulos.heading(col, text=col)
            tabla_nulos.column(col, width=100, anchor="center")

        # Insertar filas (Nombre y porcentaje)
        valores_porcentajes = [f"{round(valor, 2)}%" for valor in self.df_porcentaje_vacio["Porcentaje_Nulos"]]

        tabla_nulos.insert("", "end", values=valores_porcentajes)

        # Scroll horizontal
        scrollbar_x = tk.Scrollbar(frame_tabla_porcentaje_nulos, orient="horizontal", command=tabla_nulos.xview)
        scrollbar_x.pack(side="bottom", fill="x")
        tabla_nulos.configure(xscrollcommand=scrollbar_x.set)

        tabla_nulos.pack(fill="both", expand=True, pady=5)

    
    def mostrar_tabla_correlacion(self):
        
        tk.Label(self.info_frame, text="Tabla correlacion:", font=("Arial", 10, "bold"),background="white").pack(pady=5)
        
        # Crear un Frame para contener tanto el Treeview como el botón
        frame_contenedor = tk.Frame(self.info_frame)
        frame_contenedor.pack(fill="both", expand=True)
        frame_contenedor.config(background="white")
        
        # Crear un Frame para el botón
        frame_boton = tk.Frame(frame_contenedor)
        frame_boton.pack(side="left", padx=10)
        frame_boton.config(background="white")
        
        # Crear un botón en el frame_boton
        copiar_btn = tk.Button(frame_boton, text="Copiar", command=self.copiar_tabla_al_portapapeles_correlacion, background="white")
        copiar_btn.pack(side="left")
        
        # Crear un Frame para la tabla (Treeview)
        frame_tabla_correlacion = tk.Frame(frame_contenedor)
        frame_tabla_correlacion.pack(side="right", fill="both", expand=True, pady=10)
        frame_tabla_correlacion.config(background="white")

        # Crear el widget Treeview con una columna extra para los índices de las filas
        self.tree = ttk.Treeview(frame_tabla_correlacion, show="headings")
        
        # Crear las columnas del Treeview, incluyendo una para los índices
        self.tree["columns"] = ["index"] + list(self.df_correlacion.columns)
        
        # Configurar la primera columna para los índices de las filas
        self.tree.heading("index", text="Índices")
        self.tree.column("index", anchor="center", width=50)  # Puedes ajustar el ancho
        
        # Configurar las otras columnas para las variables, ajustando el ancho
        for col in self.df_correlacion.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=50)  # Ajusta el ancho a 100 o lo que consideres adecuado

        # Insertar las filas de datos, incluyendo los índices de las filas en la primera columna
        for idx, row in self.df_correlacion.iterrows():
            self.tree.insert("", "end", values=[idx] + list(row))
        
        # Crear un Scrollbar para la tabla
        scrollbar = tk.Scrollbar(frame_tabla_correlacion, orient="vertical", command=self.tree.yview, background="white")
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # Mostrar el Treeview en la interfaz
        self.tree.pack(fill="both", expand=True) 
            
    def copiar_tabla_al_portapapeles_correlacion(self):
        # Extraer los datos de la tabla (celdas) y convertirlo en un formato adecuado para Excel
        table_data = []
        
        # Agregar encabezados de columna
        headers = ["Índices"] + list(self.df_correlacion.columns)
        table_data.append("\t".join(headers))
        
        # Agregar filas de datos
        for idx, row in self.df_correlacion.iterrows():
            row_values = [str(idx)] + list(map(str, row))
            table_data.append("\t".join(row_values))
        
        # Convertir la lista de filas en un string con saltos de línea
        table_str = "\n".join(table_data)
        
        # Copiar el texto al portapapeles usando pyperclip
        pyperclip.copy(table_str)

    def mostrar_acumulados_totales(self):
        tk.Label(self.info_frame, text="Acumulados totales:", font=("Arial", 10, "bold"), background="white").pack(pady=5)

        # Crear un Frame para contener tanto el Treeview como el botón
        frame_contenedor = tk.Frame(self.info_frame)
        frame_contenedor.pack(fill="both", expand=True)
        frame_contenedor.config(background="white")

        # Crear un Frame para el botón
        frame_boton = tk.Frame(frame_contenedor)
        frame_boton.pack(side="left")
        frame_boton.config(background="white")

        # Crear un botón en el frame_boton
        copiar_btn = tk.Button(frame_boton, text="Copiar", command=self.copiar_tabla_al_portapapeles_acumulado_total, background="white")
        copiar_btn.pack(side="left")
        
        # Crear un Frame para la tabla (Treeview)
        frame_tabla_acumulado_total = tk.Frame(frame_contenedor)
        frame_tabla_acumulado_total.pack(side="right", fill="both", expand=True, padx= 10)


        # Crear un Treeview con columnas dinámicas
        self.tabla_acumulado_total = ttk.Treeview(frame_tabla_acumulado_total, show="headings", height=1)
        
        df_acumulados_diarios_traducido = traducir_columnas_lugar_a_id(self.df_config, self.df_acumulados_diarios_mes_real)
        
        if self.checkbox_inicio:
            pluv_validos = self.pluvio_validos.copy()
            pluv_validos.append("INUMET")
            df_acumulados_filtrado = df_acumulados_diarios_traducido[pluv_validos]
        else:   
            # Agregar columnas
            df_acumulados_filtrado = self.filtrar_pluvios_seleccionados(df_acumulados_diarios_traducido)
            
        df_acumulados_total = acumulado_diarios_total(df_acumulados_filtrado)
        df_acumulados_total = acumulado_total(df_acumulados_total)
            
        
        df_acumulados_total = df_acumulados_total.round(1)
        
        self.tabla_acumulado_total["columns"] = df_acumulados_total.columns.tolist()
        
        # Configurar los encabezados de las columnas
        for col in df_acumulados_total.columns:
            self.tabla_acumulado_total.heading(col, text=col)
            self.tabla_acumulado_total.column(col, width=50, anchor="center")  # Ajustar ancho y alineación

        # Insertar los datos
        for i, row in df_acumulados_total.iterrows():
            self.tabla_acumulado_total.insert("", "end", values=row.tolist())

        # Crear un Scrollbar horizontal
        scrollbar = tk.Scrollbar(frame_tabla_acumulado_total, orient="horizontal", command=self.tabla_acumulado_total.xview, background="white")
        self.tabla_acumulado_total.config(xscrollcommand=scrollbar.set)
        scrollbar.pack(side="bottom", fill="x")

        # Empaquetar el Treeview
        self.tabla_acumulado_total.pack(fill="both", expand=True)

    def actualizar_acumulado_total(self):
        # Elimina todos los elementos existentes
        for item in self.tabla_acumulado_total.get_children():
            self.tabla_acumulado_total.delete(item)
            
        df_acumulados_diarios_traducido = traducir_columnas_lugar_a_id(self.df_config, self.df_acumulados_diarios_mes_real)
        df_acumulados_filtrado = self.filtrar_pluvios_seleccionados(df_acumulados_diarios_traducido)

        df_acumulados_total = acumulado_diarios_total(df_acumulados_filtrado)

        df_acumulados_total = acumulado_total(df_acumulados_total)
        df_acumulados_total = df_acumulados_total.round(1)
        
        self.tabla_acumulado_total["columns"] = df_acumulados_total.columns.tolist()
        
        # Configurar los encabezados de las columnas
        for col in df_acumulados_total.columns:
            self.tabla_acumulado_total.heading(col, text=col)
            self.tabla_acumulado_total.column(col, width=50, anchor="center")  # Ajustar ancho y alineación

        # Insertar los datos
        for i, row in df_acumulados_total.iterrows():
            self.tabla_acumulado_total.insert("", "end", values=row.tolist())

    def copiar_tabla_al_portapapeles_acumulado_total(self):
        # Extraer los datos de la tabla (celdas) y convertirlo en un formato adecuado para copiar
        table_data = []

        df_acumulados_diarios_traducido = traducir_columnas_lugar_a_id(self.df_config, self.df_acumulados_diarios_mes_real)
        df_acumulados_filtrado = self.filtrar_pluvios_seleccionados(df_acumulados_diarios_traducido)

        df_acumulados_total = acumulado_diarios_total(df_acumulados_filtrado)

        df_acumulados_total = acumulado_total(df_acumulados_total)
        df_acumulados_total = df_acumulados_total.round(1)
        
        # Agregar encabezados de columna
        headers = df_acumulados_total.columns.tolist()
        table_data.append("\t".join(headers))
        
        # Agregar filas de datos
        for row_id in self.tabla_acumulado_total.get_children():
            row_values = self.tabla_acumulado_total.item(row_id)["values"]
            table_data.append("\t".join(map(str, row_values)))
        
        # Convertir la lista de filas en un string con saltos de línea
        table_str = "\n".join(table_data)
        
        # Copiar el texto al portapapeles usando pyperclip
        pyperclip.copy(table_str)

    def mostrar_tabla_percentiles(self):
        mes_str = numero_a_mes(self.mes)
        lista_percentil = valor_lluvias_historicas(self.mes)
        
        tk.Label(self.info_frame, text=f"Tabla cuantiles precipitacion del mes de {mes_str}:", font=("Arial", 10, "bold"), background="white").pack(pady=5)

        # Crear un Frame para contener tanto el Treeview como el botón
        frame_contenedor = tk.Frame(self.info_frame)
        frame_contenedor.pack(fill="both", expand=True)
        frame_contenedor.config(background="white")

        # Crear un Frame para el botón
        frame_boton = tk.Frame(frame_contenedor)
        frame_boton.pack(side="left")
        frame_boton.config(background="white")

        # Crear un botón en el frame_boton
        copiar_btn = tk.Button(frame_boton, text="Copiar", command=self.copiar_tabla_al_portapapeles_percentil,background="white")
        copiar_btn.pack(side="left")
        
        # Crear un Frame para la tabla (Treeview)
        frame_tabla_percentil = tk.Frame(frame_contenedor)
        frame_tabla_percentil.pack(side="right", fill="both", expand=True, padx=10)
        frame_tabla_percentil.config(background="white")
        
        # Crear un Treeview con columnas dinámicas
        self.tabla_percentiles = ttk.Treeview(frame_tabla_percentil, show="headings", height=1)
        
        self.nombre_percentil = ["Primer cuartil", "Mediana", "Tercer cuartil", "Maximo"]
        self.tabla_percentiles["columns"] = self.nombre_percentil
        
        # Configurar los encabezados de las columnas
        for col in self.nombre_percentil:
            self.tabla_percentiles.heading(col, text=col)
            self.tabla_percentiles.column(col, width=100, anchor="center") 

        self.tabla_percentiles.insert("", "end", values=lista_percentil)

        # Empaquetar el Treeview
        self.tabla_percentiles.pack(fill="both", expand=True)
                 
    def copiar_tabla_al_portapapeles_percentil(self):
        # Extraer los encabezados de las columnas
        headers = [self.tabla_percentiles.heading(col)["text"] for col in self.tabla_percentiles["columns"]]
        table_data = ["\t".join(headers)]  # Crear la primera fila con los encabezados

        # Extraer los datos de las filas
        for row in self.tabla_percentiles.get_children():
            values = self.tabla_percentiles.item(row)["values"]
            table_data.append("\t".join(map(str, values)))

        # Unir todas las filas con saltos de línea
        table_str = "\n".join(table_data)

        # Copiar al portapapeles
        try:
            pyperclip.copy(table_str)
        except Exception as e:
            tk.messagebox.showerror("Error", f"No se pudo copiar al portapapeles: {e}")
    
    def crear_checkboxes(self):
            frame_checkboxes = tk.Frame(self)
            frame_checkboxes.pack(fill="both", expand=True)
            frame_checkboxes.config(background="white")
            
            frame_pluvios = PluviometrosSeleccionados(self.ventana_principal,self, frame_checkboxes, self.pluvio_validos, self.checkboxes)
            frame_pluvios.pack()    

    def crear_botonera(self):
        botonera_1_frame = Frame(self)
        botonera_1_frame.pack(side="bottom", expand=True, fill="both")
        botonera_1_frame.config(background="white")
        
        botonera_frame = Frame(botonera_1_frame)
        botonera_frame.pack(side="bottom", expand=True, fill="y", padx=10, pady=10)
        botonera_frame.config(background="white")
        
        tk.Button(botonera_frame, text="Reiniciar", command=self.regresar_inicio, font=("Arial", 10, "bold"),background="white").pack(side="left", pady=10, padx=10)
        def mostrar_grafica_acumulados_barras_segura():
            try:
                fig = graficar_acumulados_barras((self.filtrar_pluvios_seleccionados(self.df_acumulados_diarios_mes_real)))
                MostrarGrafica(fig)
            except Exception as e:
                messagebox.showerror("Error", f"Ocurrió un error al generar la gráfica:\n\n{str(e)}")
                
        graficar_acumulados_barras_btn = Button(botonera_frame, text="Ver Gráfico Acumulado Mensual", 
                                         command=mostrar_grafica_acumulados_barras_segura,
                                         font=("Arial", 10, "bold"),background="white")
        graficar_acumulados_barras_btn.pack(side="left", padx=10, pady=10)

        def mostrar_grafica_acumulados_diarios_segura():
            try:
                fig = graficar_acumulados_diarios(self.seleccionar_pluv_sin_INUMET(self.df_acumulados_diarios_mes_real))
                MostrarGrafica(fig)
            except Exception as e:
                messagebox.showerror("Error", f"Ocurrió un error al generar la gráfica:\n\n{str(e)}")
        
        graficar_acumulados_diarios_btn = Button(botonera_frame, text="Ver Gráfico Acumulado Diario", 
                                         command=mostrar_grafica_acumulados_diarios_segura,
                                         font=("Arial", 10, "bold"),background="white")
        graficar_acumulados_diarios_btn.pack(side="left", padx=10, pady=10)
        
        grafica_lluvias_respecto_inumet_btn = Button(botonera_frame, text="Ver Gráfico Acumulado Respecto a INUMET", 
                                         command=lambda: MostrarGrafica(grafica_lluvias_respecto_inumet(self.df_acumulados_diarios_mes_inumet)), font=("Arial", 10, "bold"),background="white")
        grafica_lluvias_respecto_inumet_btn.pack(side="left", padx=10, pady=10)
        
        def mostrar_grafica_isoyetas_segura():
            try:
                fig = graficar_isoyetas(self.nombres_config_isoyetas(), self.seleccionar_pluv_sin_INUMET(self.df_acumulados_diarios_total_mes_real))
                MostrarGrafica(fig)
            except Exception as e:
                messagebox.showerror("Error", f"Ocurrió un error al generar la gráfica:\n\n{str(e)}")
        
        grafica_isoyetas_btn = Button(botonera_frame, text="Ver Gráfico Isoyetas", 
                                         command=mostrar_grafica_isoyetas_segura, font=("Arial", 10, "bold"),background="white")
        grafica_isoyetas_btn.pack(side="left", padx=10, pady=10)
        
        Guardar_btn = tk.Button(botonera_frame, text="Guardar Graficas", command=lambda: self.guardar_graficas(), font=("Arial", 10, "bold"),background="white")
        Guardar_btn.pack(side="left", padx=10, pady=10)

    def seleccionar_pluv_sin_INUMET(self, df):
        
        df_sin_INUMET = self.filtrar_pluvios_seleccionados(df)
        df_sin_INUMET = df_sin_INUMET.drop(columns = ["INUMET"])
        return df_sin_INUMET
    
    def nombres_config_isoyetas(self):
        acumulado_isoyetas = self.filtrar_pluvios_seleccionados(self.df_acumulados_diarios_total_mes_real)
        acumulado_isoyetas = acumulado_isoyetas.drop(columns = ["INUMET"])
        df_config_filtrado = self.df_config[self.df_config['ID'].isin(acumulado_isoyetas.columns)]
        return df_config_filtrado
    
    def guardar_graficas(self):       
        
        # Aquí puedes llamar a la función que procesa los pluviómetros seleccionados
        # por ejemplo: guardar las graficas y esas manos
        #lluvia_filtrada_inst = self.df_instantaneos[self.seleccionados]
        lluvia_filtrada_barras = self.filtrar_pluvios_seleccionados(self.df_acumulados_diarios_mes_real)
        
        if lluvia_filtrada_barras.empty:
            messagebox.showwarning("Advertencia", "Seleccione al menos un pluviómetro.")
            return
        
        # Cuadro de diálogo para seleccionar directorio y nombre del archivo
        directorio = filedialog.askdirectory(title="Selecciona un directorio para guardar las gráficas")
        errores = []

        # Gráfica de barras
        try:
            fig_barras = graficar_acumulados_barras(lluvia_filtrada_barras)
            fig_barras.savefig(f"{directorio}/grafica acumulado mensual.png", dpi=300)
        except Exception as e:
            errores.append(f"Gráfica de acumulado mensual: {e}")

        # Gráfica de acumulado diario
        try:
            lluvia_filtrada_acum_diario = self.seleccionar_pluv_sin_INUMET(self.df_acumulados_diarios_mes_real)
            fig_acum = graficar_acumulados_diarios(lluvia_filtrada_acum_diario)
            fig_acum.savefig(f"{directorio}/grafica acumulado diario.png", dpi=300)
        except Exception as e:
            errores.append(f"Gráfica de acumulado diario: {e}")
        
        # Gráfica respecto INUMET
        try:
            fig_inumet = grafica_lluvias_respecto_inumet(self.df_acumulados_diarios_mes_real)
            fig_inumet.savefig(f"{directorio}/grafica acumulado respecto INUMET.png", dpi=300)
        except Exception as e:
            errores.append(f"Gráfica respecto INUMET: {e}")
        
        # Gráfica de isoyetas
        try:
            fig_isoyetas = graficar_isoyetas(
                self.nombres_config_isoyetas(),
                self.seleccionar_pluv_sin_INUMET(self.df_acumulados_diarios_total_mes_real)
            )
            fig_isoyetas.savefig(f"{directorio}/grafica mensual isoyetas.png", dpi=300)
        except Exception as e:
            errores.append(f"Gráfica de isoyetas: {e}")
        
        if errores:
            mensaje_error = "Algunas gráficas no se pudieron generar:\n\n" + "\n".join(errores)
            messagebox.showwarning("Finalizado con errores", mensaje_error)
        else:
            messagebox.showinfo("Éxito", "Todas las gráficas fueron generadas correctamente.")
  
    def regresar_inicio(self):
        self.cerrar_ventana()
        self.ventana_principal.reiniciar_variables()
        self.ventana_principal.deiconify()
    
    def cerrar_ventana(self):
        self.destroy()
    
