# Manual de Usuario y Despliegue: AsistPy Desktop GUI 🖥️

La Interfaz Gráfica de Escritorio (Desktop GUI) de **AsistPy** es una aplicación nativa, moderna y multiplataforma (Linux, Windows y macOS) construida sobre **PySide6 (Qt for Python)** y diseñada bajo Arquitectura Hexagonal.

Sigue la filosofía central de AsistPy: **instala solo lo que necesitas**. El usuario puede desplegarla como una estación de trabajo local (SQLite integrado y cero dependencias externas) o conectarla a servidores centrales corporativos (PostgreSQL, MySQL, SQL Server) instalando únicamente el driver correspondiente.

---

## 🎨 Paleta Visual y Experiencia de Usuario (UI/UX)

La aplicación utiliza un diseño oscuro contemporáneo con alto contraste y legibilidad para entornos de control y recursos humanos:

| Elemento | Color Hex | Propósito |
| :--- | :--- | :--- |
| **Fondo Principal** | `#09091A` | Canvas general, barra lateral y barras de herramientas |
| **Superficie de Tarjetas** | `#121229` | Paneles modulares, tarjetas KPI y formularios |
| **Texto de Contraste** | `#FFFFFF` | Tipografía principal, títulos y datos numéricos |
| **Acento Primario** | `#276EF1` | Botones de acción principal, pestañas activas, foco |
| **Neutro / Secundario**| `#6B6B6B` | Bordes, subtítulos, etiquetas secundarias e indicadores |

---

## 📦 Instalación Modular a la Carta

Elige la combinación de dependencias que tu estación de trabajo requiere:

### 1. Puesto de Control Autónomo (Caseta / Monopuesto Local)
Instala únicamente el núcleo, la interfaz gráfica y SQLite:
```bash
pip install "asistpy[desktop,sqlite]"
```

### 2. Puesto Corporativo Conectado a PostgreSQL
Para oficinas centrales o puestos de RRHH conectados a una base de datos central:
```bash
pip install "asistpy[desktop,postgres]"
```

### 3. Puesto Conectado a MySQL / SQL Server
```bash
pip install "asistpy[desktop,mysql]"
# o para SQL Server:
pip install "asistpy[desktop,sqlserver]"
```

### 4. Instalación Completa (Todos los drivers)
```bash
pip install "asistpy[all]"
```

---

## 🚀 Inicio de la Aplicación

Una vez instalada, inicia la aplicación mediante el comando directo:
```bash
asistpy-gui
```
O invocando el módulo Python:
```bash
python -m attendance.adapters.gui
```

---

## 🧙 Asistente de Configuración Inicial (Setup Wizard)

Si es la primera vez que abres la aplicación o si no existe un archivo de configuración `.env`, AsistPy abrirá automáticamente el **Asistente de Bienvenida**:

1. **Paso 1 - Selección de Motor**:
   - Escoge entre **SQLite** (recomendado para uso local sin servidor) o un servidor corporativo (**PostgreSQL**, **MySQL**, **SQL Server**).
2. **Paso 2 - Parámetros de Conexión**:
   - Ingresa host, puerto, nombre de base de datos y credenciales.
   - Presiona **⚡ Probar Conexión** para validar inmediatamente que el driver esté instalado y que el servidor responda.
3. **Paso 3 - Inicialización de Tablas**:
   - Presiona **⚙️ Inicializar Tablas** para estructurar la base de datos y dar de alta la sucursal matriz.
4. **Paso 4 - Primer Reloj Biométrico**:
   - Ingresa el nombre, dirección IP y puerto (4370) de tu reloj ZKTeco.
   - Presiona **📡 Probar Comunicación TCP** para realizar un ping inmediato al hardware.

Al pulsar **Completar y Arrancar**, la configuración se guardará y la ventana principal se abrirá lista para operar.

---

## 🖥️ Módulos de la Aplicación

### 1. Tablero Principal (Dashboard)
- Indicadores en tiempo real (relojes registrados, colaboradores, marcaciones del día, sucursales).
- Botón directo **🔄 Sincronizar Todos los Relojes** que orquesta la lectura de todos los relojes activos en segundo plano (`QThread`) sin congelar la pantalla.

### 2. Relojes Biométricos (Terminales ZKTeco)
- Catálogo completo de terminales con dirección IP y estado activo/inactivo.
- Opciones para registrar nuevo reloj, editar parámetros, probar comunicación TCP y forzar sincronización manual individual.

### 3. Personal y Áreas (Directorio Organizacional)
- Pestaña **Colaboradores**: Directorio con búsqueda rápida por PIN o nombre, alta y edición.
- Pestaña **Departamentos**: Creación y organización por áreas.
- Pestaña **Sucursales**: Administración de ubicaciones y zonas horarias.

### 4. Turnos, Horarios y Rotaciones
El módulo se divide en 4 pestañas especializadas para cubrir la totalidad de esquemas laborales:
- **Catálogo de Turnos**: Creación y edición de turnos fijos, turnos con descanso intermedio y jornadas nocturnas (que cruzan la medianoche), con definición precisa de tolerancias de entrada, retardo y salida anticipada.
- **Asignaciones de Horario**:
  - Vinculación de turnos a cada colaborador con rango de fechas de vigencia.
  - **Días de Descanso Fijo**: Configuración visual mediante selector de esquemas frecuentes (*Lunes a Sábado*, *Lunes a Viernes*, *Personalizado*) y casillas independientes para los 7 días de la semana (Lunes a Domingo), guardando automáticamente los días laborables (`working_weekdays`).
  - **Soporte de Esquemas Rotativos**: Selección directa de patrones cíclicos previamente configurados.
- **Patrones de Rotación**:
  - Catálogo de secuencias cíclicas de trabajo y descanso periódico (ej. 6x1, 4x3, esquemas 24x48).
  - Diálogo interactivo donde se introducen los identificadores de turnos y las palabras clave `OFF`, `DESC` o `REST` para definir los días de descanso dentro del ciclo, con frecuencia (semanal, catorcenal, etc.) y fecha ancla.
- **Excepciones y Eventualidades**:
  - Gestión de incidencias programadas y cambios de calendario puntuales que sobreescriben el horario habitual.
  - Diálogo intuitivo con selector de colaborador, fecha en calendario y opción para **Forzar día de descanso** (por permiso, guardia previa, etc.) o **Sustituir por turno extraordinario**, registrando el motivo de la eventualidad.

### 5. Marcaciones y Asistencia
- **Marcaciones Crudas**: Visor de eventos extraídos directamente del hardware (UID, fecha, hora, método de verificación: huella/rostro/tarjeta).
- **Jornadas Diarias**: Vista de sesiones consolidadas con cálculo de entrada, salida, minutos trabajados, retardos y horas extras.
- Botón **📥 Exportar a CSV** para extraer reportes a hojas de cálculo.

### 6. Cierre y Evaluación
- Procesamiento de asistencias por fecha o rango con un clic (**⚡ Ejecutar Evaluación**).
- **Resolución Inteligente de Descansos**: En días de descanso (semanal fijo, rotativo o forzado por excepción), el sistema no genera faltas injustificadas sino el estado formal `REST_DAY`. Si el colaborador asiste y checa en su descanso, se registra como `PRESENT` indicando la nota *"Laboró en día de descanso"*.
- Detección automática de retardos, salidas tempranas, omisiones y faltas (`ABSENT`).
- Modal para **📝 Justificar Incidencias** con motivo, folio de justificante y registro formal en el sistema.

### 7. Configuración y Diagnóstico
- Visualización de la conexión activa.
- Diagnóstico en vivo de los drivers opcionales instalados (`psycopg`, `pymysql`, `pyodbc`, `pymongo`, `zk`).
- Botón para reabrir el asistente o reparar tablas.

---

## 📦 Generación de Ejecutables Autocontenidos (.exe / AppImage / .dmg)

Para distribuir la aplicación a usuarios finales sin requerir que instalen Python:

### Compilación Local con PyInstaller
```bash
pip install pyinstaller
python scripts/package/build_desktop.py --clean
```
El ejecutable binario se generará en la carpeta `dist/AsistPy`.

### Compilación Multiplataforma con GitHub Actions
El repositorio incluye el pipeline `.github/workflows/build_desktop.yml` que compila automáticamente artefactos para:
- **Windows**: `asistpy-windows-x64.zip` (con `AsistPy.exe`)
- **Linux**: `asistpy-linux-x64.tar.gz` (binario autocontenido)
- **macOS**: `asistpy-macos-x64.tar.gz`
