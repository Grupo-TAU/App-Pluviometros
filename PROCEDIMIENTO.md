# Informe pluviométrico mensual — procedimiento

Genera el informe mensual de la RHM a partir del CSV crudo de Fiware/Grafana, sin abrir la app.

```bash
python generar_informe.py --mes 8 --anio 2026 --version 1
```

Deja todo en `outputs/2026-08/`: los dos CSV refinados, las tablas del informe en CSV, las
figuras en PNG y el borrador en Word.

---

## Configurar las carpetas de trabajo

Las rutas se fijan una sola vez en `config_informe.json`:

```json
{
  "crudos": "data/raw",
  "inumet": "data/inumet",
  "salida": "G:/Unidades compartidas/GRUPO TAU/.../Informes"
}
```

Las rutas relativas se resuelven contra la carpeta del pipeline, así que el comando funciona
igual desde cualquier directorio. Las absolutas se usan tal cual, que es lo práctico para
apuntar al drive compartido.

Para una corrida puntual se puede pisar cualquiera sin tocar el archivo:

```bash
python generar_informe.py --mes 8 --anio 2026 --salida "D:/pruebas"
```

Si `config_informe.json` no existe, se usan los valores por defecto de arriba.

⚠️ El archivo de descartes (`problemas_{mes}.csv`) vive dentro de la carpeta de salida. Si
cambiás `salida`, la corrida siguiente vuelve a proponer los candidatos automáticos y hay que
rehacer las correcciones.

---

## Instalación en otra máquina

```bash
pip install -r requirements.txt
```

Hace falta Python 3.10 o superior. `tkinter` viene con Python en Windows; si el equipo usa
Linux hay que instalarlo aparte (`python3-tk`).

Además de `generar_informe.py`, hay que copiar:

| Qué | Por qué |
|---|---|
| `Codigo/Informe/` (5 archivos) | El pipeline |
| `Codigo/Instalador/Funciones_basicas.py` | Lectura de CSV, fechas, conversión UTM |
| `Codigo/Instalador/Funciones_exportar.py` | Los dos CSV refinados |
| `Codigo/Instalador/Funciones_mensual.py` | Cuartiles históricos |
| `Codigo/Instalador/isoyetas.py` | Interpolación IDW |
| `Equipos_RHM.csv` | Tabla 1-1 |
| `Coordenadas_Equipos.csv` | Posiciones para las isoyetas |
| `MONTEVIDEO.png` | Mapa de fondo |
| `config_informe.json` | Opcional |

No hacen falta `main.py`, `interfaz.py`, `Funciones_tormenta.py` ni `Funciones_config.py`: son
solo de la app con interfaz gráfica. Lo más simple es clonar el repo entero.

---

## Rutina mes a mes

### 1. Exportar el CSV crudo de Grafana

El rango tiene que ir **desde las 07:00 del último día del mes anterior hasta las 00:00 del día 1
del mes siguiente** (para agosto: del 31/07 07:00 al 01/09 00:00). Cubre las dos cosas que usa el
informe: el mes civil completo, que es la base de todo, y los días de 7 a 7 de INUMET, que solo
se usan para comparar contra INUMET. Lo que sobra de cada lado lo descarta el cálculo solo.

Si el export arranca más tarde, **el primer día de la comparación con INUMET queda incompleto**;
si termina antes de las 00:00 del día 1, **el último día del mes queda incompleto**. En los dos
casos la corrida lo avisa en consola con un `AVISO`.

Guardalo como `data/raw/2026-08.csv`, o pasá la ruta con `--crudo`.

### 2. Primera corrida — validación

```bash
python generar_informe.py --mes 8 --anio 2026 --dry-run
```

Recalcula el total de cada equipo directamente sobre las lecturas crudas, sin pasar por la
grilla de 5 minutos, y lo compara contra la tabla diaria. Las dos cuentas tienen que dar igual
(diferencia máxima < 0.05 mm). Si no dan, hay un problema en la lógica de diferencias y no
conviene seguir.

### 3. Cargar los datos de INUMET

La primera corrida deja la plantilla `data/inumet/INUMET_2026-08.csv` con un renglón por día:

```csv
FECHA,INUMET
31/07/2026,
01/08/2026,
```

Completá la columna `INUMET` con el acumulado diario en mm. Sin esto el informe se genera igual,
pero quedan sin datos la Figura 4-1 (Q-Q), la columna INUMET de la Tabla 4-2 (correlación) y de
las tablas de acumulados.

### 4. Corrida completa

```bash
python generar_informe.py --mes 8 --anio 2026 --version 1
```

### 5. Revisar los descartes

Se genera `outputs/2026-08/problemas_2026-08.csv` con los equipos problemáticos y una sugerencia:

```csv
ID,Lugar,Motivo,Descartar
EBCN,Colon,Sus registros no son consistentes...,True
EBSA,Paso de la Arena,Registro 25.7 mm frente a 96.4 mm...,True
```

**Esto es una sugerencia, no un veredicto.** Editá la columna `Descartar` según el relevamiento
de campo y volvé a correr. El archivo no se pisa nunca: si existe, el pipeline usa tu versión.

El caso típico es Paso de la Arena, que tiene el problema conocido de reiniciar el acumulado
diario intradía y aun así se conserva en el análisis.

### 6. Completar el Word

El borrador sale con placeholders en rojo `[COMPLETAR: ...]` en las secciones que requieren
criterio o trabajo de campo:

- **3.1, 3.2, 3.3** — mantenimiento, relevamiento y sustitución de equipos
- **5** — revisión final de la decisión de descarte
- **6.2.x** — interpretación de la distribución espacial de cada tormenta
- **8** — recomendaciones para el próximo mes
- **Anexo I** — ficha de relevamiento

El índice es un campo de Word: abrilo, click derecho sobre él y "Actualizar campos".

---

## Qué hay que mantener a mano

| Archivo | Qué contiene | Cuándo tocarlo |
|---|---|---|
| `Equipos_RHM.csv` | Tabla 1-1: lugar, ID, tipo, dirección | Si se agrega, saca o muda un equipo |
| `Coordenadas_Equipos.csv` | Coordenadas UTM 21S para las isoyetas | Igual que el anterior |
| `Lugares-ID.csv` | Traducción lugar → ID que usa la app | Igual que el anterior |
| `lluvia_historico` en `Funciones_mensual.py` | Cuartiles históricos por mes (Prado 1900-2019) | Si INUMET actualiza la serie |
| `precipitacion_tr` en `Funciones_basicas.py` | Curvas IDF del IMFIA | Si el IMFIA publica curvas nuevas |

---

## Cómo se calcula cada cosa

**Los dos CSV refinados.** El valor que manda Grafana es un contador acumulado que el equipo
reinicia solo, a medianoche. La lluvia de cada rango de 5 minutos es la suma de las diferencias
entre lecturas crudas consecutivas dentro del rango, descartando las negativas (que son
reinicios del contador). En lluvia intensa hay varias lecturas por rango y se suman todas. La
cadena se reinicia en cada día pluviométrico, así que el primer rango de cada día vale 0.

**Dos cálculos de lluvia, con usos distintos.** Las ventanas de análisis de la app (Mensual y
Tormenta) calculan la lluvia con `calcular_instantaneos()`: la diferencia entre lecturas
consecutivas del contador en grilla de 5 minutos, sin bajadas. La exportación de CSV y el
informe usan `calcular_tablas_refinadas()`, que suma todas las lecturas crudas de cada rango y
descarta los outliers. Sobre el mismo archivo pueden dar totales algo distintos: la app no
descarta nada, solo alerta.

**Día civil, salvo contra INUMET.** Todo se calcula por día civil (00:00 a 00:00). El corte de
las 07:00 se usa solo para comparar día a día contra INUMET, que mide de 7 a 7: en la app, la
tabla de correlación y la gráfica respecto a INUMET de la ventana Mensual; en el informe, la
Figura 4-1 y la Tabla 4-2. Los acumulados mensuales, la serie diaria, los eventos, la evaluación
de la red y los CSV van por día civil. Las dos horas están en `HORA_CORTE_CIVIL` y
`HORA_CORTE_INUMET`, en `Funciones_exportar.py`.

**Alertas de la app.** Las ventanas Mensual y Tormenta marcan, sin tocar los datos, los
pluviómetros con más de 25 mm en 5 minutos, más de 50 mm en 10 minutos seguidos, o más de 2
lecturas en un mismo rango de 5 minutos (los equipos reportan una vez cada 5 minutos). Los
umbrales están en `Funciones_basicas.py`.

**Outliers (4.4).** Se descartan los rangos que superan 25 mm en 5 minutos, y se reportan los
que superan 50 mm en 10 minutos. Un rango descartado queda en blanco, no en cero: no se sabe
cuánto llovió realmente. Los descartes se listan en el informe.

**Datos faltantes (4.1).** Porcentaje de rangos de 5 minutos sin ninguna lectura. Se calcula
sobre una tabla de cobertura aparte, porque en la tabla de acumulados un rango sin lectura vale
0 igual que uno con lectura y sin lluvia.

**Eventos de tormenta (6.2).** Días con más de 20 mm en algún equipo (día civil) o en INUMET (de 7 a 7). La ventana del
evento es la racha continua de lluvia de la red, permitiendo huecos de hasta 60 minutos,
recortada hasta quedarse con la ventana más corta que concentra el 99 % de la lluvia, y
redondeada a la media hora.

**Isoyetas (6.1, 6.2).** Interpolación IDW sobre una grilla de 300×300 con el mapa de
Montevideo de fondo. Es numpy puro: no hace falta QGIS ni scipy.

---

## Limitaciones conocidas

**Los números cambian según cuándo exportes.** Fiware sigue rellenando datos hacia atrás. El
informe de agosto 2026 V2 (armado el 3-sep) publica 94.5 mm para Capurro; el mismo mes exportado
el 7-sep da 110.5 mm. No es un error de cálculo. Por eso el informe registra la fecha del export.

**El fin del evento de tormenta es discutible.** Después de una tormenta suele quedar una cola
de llovizna de horas aportando décimas de milímetro. El criterio automático del 99 % reproduce
exacto el evento del 1 de agosto (00:30 a 07:30) y deja el del 6 de agosto 30 minutos corto
(16:30 contra las 17:00 del informe). Los máximos por duración no cambian: la lluvia está
concentrada en el núcleo del evento.

**La lista de descartes sobre-marca.** Sugiere descartar equipos que solo miden por debajo de la
mediana de la red, y en un mes seco eso es ruidoso: en diciembre 2025, con mediana de 13.5 mm,
marca equipos que acumularon 24 mm. Por eso la decisión final es del operario.

**Un equipo con el contador desbocado puede pasar el filtro de outliers.** Capurro en enero 2026
acumuló 715 mm contra 74 mm de mediana de la red, con 633 mm en un solo día, y ningún incremento
individual superó los 25 mm. Lo agarra el criterio de correlación con la red, no el de
intensidad.

**Los meses ya exportados no cubren el rango nuevo.** Hasta agosto 2026 los exports terminan a
las 07:00 del último día del mes, así que con día civil ese día queda incompleto. Además marzo,
abril, mayo, junio y julio 2026 arrancan a las 07:00 del día 1 en vez del último día del mes
anterior, lo que deja incompleto el primer día de la comparación con INUMET. Hay que
re-exportarlos con el rango del paso 1.
