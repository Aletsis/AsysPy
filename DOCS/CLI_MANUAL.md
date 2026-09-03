# 📖 Manual de Uso: CLI Unificada de AsistPy (`asistpy`)

> **Herramienta de consola oficial de AsistPy para administración, gestión CRUD de catálogos maestros, diagnóstico de hardware, sincronización de relojes biométricos, evaluación de jornadas laborales y generación de reportes.**

---

## 📋 Tabla de Contenidos

1. [Introducción y Arquitectura](#-introducción-y-arquitectura)
2. [Instalación y Configuración](#-instalación-y-configuración)
3. [Estructura y Sintaxis General](#-estructura-y-sintaxis-general)
4. [Opciones Globales](#-opciones-globales)
5. [CRUD de Sucursales (`asistpy branch`)](#-crud-de-sucursales-asistpy-branch)
6. [CRUD de Empleados (`asistpy employee`)](#-crud-de-empleados-asistpy-employee)
7. [CRUD de Turnos de Trabajo (`asistpy shift`)](#-crud-de-turnos-de-trabajo-asistpy-shift)
8. [CRUD de Asignaciones de Horario (`asistpy schedule`)](#-crud-de-asignaciones-de-horario-asistpy-schedule)
9. [CRUD y Control de Dispositivos Biométricos (`asistpy device`)](#-crud-y-control-de-dispositivos-biométricos-asistpy-device)
10. [Control de Asistencia y Jornadas (`asistpy attendance`)](#-control-de-asistencia-y-jornadas-asistpy-attendance)
11. [Reportes y Exportación (`asistpy report`)](#-reportes-y-exportación-asistpy-report)
12. [Gestión de Base de Datos (`asistpy db`)](#-gestión-de-base-de-datos-asistpy-db)
13. [Automatización con Crontab / Systemd](#-automatización-con-crontab--systemd)
14. [Códigos de Salida (Exit Codes)](#-códigos-de-salida-exit-codes)

---

## 🌟 Introducción y Arquitectura

La CLI `asistpy` actúa como un **Adaptador Primario o Conductor (Driving Adapter)** dentro de la Arquitectura Hexagonal del sistema. Permite ejecutar directamente todos los casos de uso de la aplicación (`application`) contra cualquier motor de persistencia configurado (SQLite, PostgreSQL, MySQL, SQL Server o memoria) sin necesidad de iniciar servidores web ni interfaces gráficas.

Características clave:
- **CRUD Completo de Catálogos**: Alta, consulta detallada, listado, edición y eliminación de sucursales, empleados, turnos, horarios y dispositivos.
- **Cero dependencias externas forzadas**: Funciona nativamente sobre la biblioteca estándar de Python (`argparse`), con renderizador interno de tablas Unicode/ASCII y soporte de colores ANSI (respetando `NO_COLOR`).
- **Soporte nativo de `.env`**: Lee automáticamente las variables de entorno locales o las provistas por parámetro.
- **Portabilidad**: Ejecutable como comando del sistema (`asistpy`) o como módulo de Python (`python -m attendance.cli` / `python -m attendance.adapters.cli`).

---

## 💻 Instalación y Configuración

### Instalación en el entorno virtual
Si instalas AsistPy en modo editable o en producción:
```bash
# Dentro del entorno virtual de Poetry o pip:
poetry install
# O para instalar el extra liviano de CLI con pip:
pip install "asistpy[cli]"
```

El comando `asistpy` quedará disponible en el `PATH` de tu entorno virtual:
```bash
asistpy --help
```

### Configuración vía `.env`
Copia la plantilla `.env.example` como `.env`:
```bash
cp .env.example .env
```

Variables principales:
```dotenv
PERSISTENCE_BACKEND=sqlite
DATABASE_URL=sqlite:///asistpy.db

# Configuración de Reloj ZKTeco predeterminado
ZK_DEVICE_IP=192.168.0.233
ZK_DEVICE_PORT=4370
ZK_TIMEOUT=60
```

---

## 🛠 Estructura y Sintaxis General

```bash
asistpy [OPCIONES_GLOBALES] <GRUPO> <ACCION> [OPCIONES_ESPECIFICAS]
```

Los grupos principales disponibles son:
- `branch`: Catálogo CRUD de sucursales u oficinas físicas.
- `employee`: Catálogo CRUD de empleados y personal.
- `shift`: Catálogo CRUD de turnos de trabajo y tolerancias.
- `schedule`: Catálogo CRUD y asignación de horarios a empleados.
- `device`: Catálogo CRUD, sondeo y sincronización de relojes biométricos.
- `attendance`: Evaluación diaria de horarios, consulta y ajustes con auditoría.
- `report`: Consolidación y exportación a formatos de reporte (pantalla, CSV, JSON).
- `db`: Inicialización y diagnóstico de la base de datos.

---

## 🌐 Opciones Globales

Puedes especificar estas opciones antes del grupo o después del subcomando:

| Opción | Descripción | Ejemplo |
| :--- | :--- | :--- |
| `--version` | Muestra la versión actual de AsistPy y finaliza. | `asistpy --version` |
| `--help`, `-h` | Muestra la ayuda de la CLI o de cualquier comando. | `asistpy employee --help` |
| `--env-file` | Carga un archivo `.env` personalizado. | `asistpy --env-file .env.prod db status` |
| `--backend` | Sobrescribe el motor de base de datos (`sqlite`, `postgres`, `mysql`, `sqlserver`, `memory`). | `asistpy db status --backend postgres` |
| `--db-url` | Sobrescribe la cadena de conexión (`DATABASE_URL`). | `asistpy db status --db-url "sqlite:///datos.db"` |
| `-v`, `--verbose`| Habilita la traza completa de excepciones en caso de fallo. | `asistpy -v device probe` |

---

## 🏢 CRUD de Sucursales (`asistpy branch`)

Permite registrar y administrar las diferentes sucursales, plantas o ubicaciones físicas de la empresa.

### 1. `asistpy branch add` (Crear)
```bash
# Registrar una sucursal básica
asistpy branch add --name "Sucursal Matriz" --code "MAT-01"

# Registrar con dirección y zona horaria
asistpy branch add \
  --name "Planta Guadalajara" \
  --code "GDL-01" \
  --timezone "America/Mexico_City" \
  --city "Guadalajara" \
  --state "Jalisco" \
  --street "Av. Vallarta 1500" \
  --postal-code "44100"
```

### 2. `asistpy branch show` (Ver Detalle)
```bash
# Por código
asistpy branch show --code "MAT-01"

# Por ID
asistpy branch show --branch-id 1
```

### 3. `asistpy branch list` (Listar)
```bash
# Listar todas
asistpy branch list

# Listar solo activas
asistpy branch list --active-only
```

### 4. `asistpy branch edit` (Modificar)
```bash
asistpy branch edit --code "MAT-01" --name "Sucursal Matriz Renovada" --city "Zapopan"

# Desactivar sucursal
asistpy branch edit --code "MAT-01" --inactive

# Reactivar sucursal
asistpy branch edit --code "MAT-01" --active
```

### 5. `asistpy branch delete` (Eliminar)
```bash
asistpy branch delete --code "MAT-01" --force
# o por ID:
asistpy branch delete --branch-id 1 --force
```

---

## 👥 CRUD de Empleados (`asistpy employee`)

Permite gestionar el padrón de trabajadores y colaboradores que checan asistencia en los relojes biométricos.

### 1. `asistpy employee add` (Crear)
```bash
asistpy employee add \
  --pin "E101" \
  --first-name "Carlos" \
  --paternal-last-name "Gómez" \
  --maternal-last-name "López" \
  --hire-date 2024-03-15 \
  --sex male \
  --position "Operador CNC" \
  --department-id 2 \
  --branch-id 1
```

### 2. `asistpy employee show` (Ver Detalle)
```bash
asistpy employee show --pin "E101"
```

### 3. `asistpy employee list` (Listar)
```bash
# Listar todos los empleados
asistpy employee list

# Filtrar por sucursal
asistpy employee list --branch-id 1

# Filtrar solo empleados activos
asistpy employee list --active-only

# Buscar por coincidencia de PIN
asistpy employee list --pin "101"
```

### 4. `asistpy employee edit` (Modificar)
```bash
# Cambiar de puesto y departamento
asistpy employee edit --pin "E101" --position "Supervisor de Turno" --department-id 1

# Dar de baja (inactivar)
asistpy employee edit --pin "E101" --inactive

# Reactivar empleado
asistpy employee edit --pin "E101" --active
```

### 5. `asistpy employee delete` (Eliminar)
```bash
asistpy employee delete --pin "E101" --force
```

---

## ⏰ CRUD de Turnos de Trabajo (`asistpy shift`)

Permite configurar los horarios laborales, tiempos de tolerancia para retardos y cruce de medianoche (jornadas nocturnas).

### 1. `asistpy shift add` (Crear)
```bash
# Turno regular matutino
asistpy shift add --name "Matutino 8-16" --start-time "08:00" --end-time "16:00" --tolerance 15 --category regular

# Turno nocturno que cruza medianoche
asistpy shift add --name "Nocturno 22-06" --start-time "22:00" --end-time "06:00" --tolerance 10 --crosses-midnight --category nocturno
```

### 2. `asistpy shift show` (Ver Detalle)
```bash
asistpy shift show --shift-id 1
```

### 3. `asistpy shift list` (Listar)
```bash
asistpy shift list
```

### 4. `asistpy shift edit` (Modificar)
```bash
# Ajustar tolerancia y horarios
asistpy shift edit --shift-id 1 --start-time "08:30" --end-time "16:30" --tolerance 10
```

### 5. `asistpy shift delete` (Eliminar)
```bash
asistpy shift delete --shift-id 1 --force
```

---

## 📅 CRUD de Asignaciones de Horario (`asistpy schedule`)

Vincula los turnos a empleados específicos estableciendo fechas de vigencia y esquemas fijos o rotativos.

### 1. `asistpy schedule assign` (Crear / Asignar)
```bash
# Asignar turno fijo desde una fecha inicial
asistpy schedule assign \
  --employee-pin "E101" \
  --shift-id 1 \
  --mode fixed \
  --valid-from 2026-09-01

# Asignar turno con fecha de término definida
asistpy schedule assign \
  --employee-pin "E101" \
  --shift-id 2 \
  --mode fixed \
  --valid-from 2026-09-01 \
  --valid-until 2026-12-31
```

### 2. `asistpy schedule show` (Ver Detalle)
```bash
asistpy schedule show --assignment-id 1
```

### 3. `asistpy schedule list` (Listar)
```bash
# Listar todas las asignaciones
asistpy schedule list

# Filtrar por empleado
asistpy schedule list --employee-pin "E101"
```

### 4. `asistpy schedule edit` (Modificar)
```bash
asistpy schedule edit --assignment-id 1 --shift-id 2 --valid-until 2026-11-30
```

### 5. `asistpy schedule close` (Cerrar Vigencia)
Establece una fecha de fin para el horario actual (por ejemplo, ante un cambio de turno):
```bash
asistpy schedule close --assignment-id 1 --valid-until 2026-09-15
```

### 6. `asistpy schedule delete` (Eliminar)
```bash
asistpy schedule delete --assignment-id 1 --force
```

---

## 🕒 CRUD y Control de Dispositivos Biométricos (`asistpy device`)

Gestiona el catálogo de relojes checadores ZKTeco y efectúa pruebas de comunicación TCP.

### 1. `asistpy device add` (Crear)
```bash
asistpy device add \
  --name "Reloj Recepción" \
  --ip 192.168.1.200 \
  --port 4370 \
  --branch-id 1 \
  --serial "CJK9203841029" \
  --location "Lobby Principal"
```

### 2. `asistpy device show` (Ver Detalle)
```bash
asistpy device show --device-id 1
```

### 3. `asistpy device list` (Listar)
```bash
# Listar todos
asistpy device list

# Filtrar por sucursal
asistpy device list --branch-id 1

# Filtrar solo activos
asistpy device list --active-only
```

### 4. `asistpy device edit` (Modificar)
```bash
asistpy device edit --device-id 1 --ip 192.168.1.205 --location "Puerta 1"

# Desactivar temporalmente
asistpy device edit --device-id 1 --inactive
```

### 5. `asistpy device delete` (Eliminar)
```bash
asistpy device delete --device-id 1 --force
```

### 6. `asistpy device probe` (Diagnóstico de Hardware)
Prueba la conexión TCP (puerto 4370) con el reloj, lee firmware, número de serie y conteo de marcaciones en memoria física.
```bash
# Probar dispositivo en red por IP
asistpy device probe --ip 192.168.1.200 --port 4370

# Probar dispositivo registrado por su ID
asistpy device probe --device-id 1
```

### 7. `asistpy device sync` (Sincronización Incremental)
Descarga e inserta nuevos registros de marcaciones crudas (`AttendanceLog`), evitando duplicados con control de marcas de agua (UID).
```bash
# 1. Sincronizar TODOS los relojes activos del catálogo
asistpy device sync

# 2. Sincronizar relojes de una sucursal específica
asistpy device sync --branch-id 1

# 3. Sincronizar un único reloj por su ID
asistpy device sync --device-id 1
```

---

## ⏱ Control de Asistencia y Jornadas (`asistpy attendance`)

### 1. `asistpy attendance evaluate` (Evaluación de Jornada)
Ejecuta el motor de reglas de asistencia: empareja entradas y salidas, coteja contra el turno asignado y calcula horas trabajadas, retardos y horas extras.
```bash
# Evaluar a todos los empleados activos para la fecha actual
asistpy attendance evaluate

# Evaluar a todos los empleados en una fecha pasada
asistpy attendance evaluate --date 2026-09-02

# Evaluar un empleado específico en una fecha
asistpy attendance evaluate --employee-pin "E101" --date 2026-09-02

# Evaluar un rango de fechas para un empleado
asistpy attendance evaluate --employee-pin "E101" --start-date 2026-09-01 --end-date 2026-09-15
```

### 2. `asistpy attendance list` (Historial de Asistencia)
```bash
# Listar las últimas 50 jornadas evaluadas
asistpy attendance list

# Filtrar por empleado
asistpy attendance list --employee-pin "E101"

# Ver marcaciones CRUDAS del reloj biométrico (sin procesar)
asistpy attendance list --raw --limit 20
```

### 3. `asistpy attendance adjust` (Ajustes Manuales Auditados)
Permite corregir u omitir marcaciones con **bitácora inmutable de auditoría (`audit_logs`)**:
```bash
# Registrar una marcación manual omitida
asistpy attendance adjust \
  --employee-pin "E101" \
  --timestamp "2026-09-02 08:00:00" \
  --reason "Falla en lector biométrico" \
  --modified-by "supervisor_rrhh"
```

---

## 📊 Reportes y Exportación (`asistpy report`)

### `asistpy report summary`
Consolida los totales del período en pantalla o los exporta a formatos estándar.

```bash
# 1. Formato tabla en consola
asistpy report summary --start-date 2026-09-01 --end-date 2026-09-07

# 2. Exportación a archivo CSV (ideal para Excel o nómina)
asistpy report summary \
  --start-date 2026-09-01 \
  --end-date 2026-09-15 \
  --format csv \
  --output reportes/primera_quincena.csv

# 3. Exportación a archivo JSON (integración con APIs)
asistpy report summary \
  --start-date 2026-09-01 \
  --end-date 2026-09-07 \
  --format json \
  --output reportes/semana36.json
```

---

## 🗄 Gestión de Base de Datos (`asistpy db`)

### 1. `asistpy db init`
Crea las tablas en la base de datos configurada (`branches`, `employees`, `shifts`, `devices`, `daily_attendances`, etc.):
```bash
asistpy db init
```

### 2. `asistpy db status`
Verifica la conectividad y muestra un inventario completo de registros:
```bash
asistpy db status
```

**Salida de ejemplo:**
```text
Comprobando estado de la base de datos...
┌──────────────────────────┬────────────────────────┐
│ Parámetro                │ Valor                  │
├──────────────────────────┼────────────────────────┤
│ Motor / Backend          │ sqlite                 │
│ URL de Conexión          │ sqlite:///asistpy.db   │
│ Estado de Conexión       │ Conectado (OK)         │
│ Sucursales Registradas   │ 2                      │
│ Dispositivos en Catálogo │ 3                      │
│ Empleados Registrados    │ 45                     │
│ Turnos en Catálogo       │ 4                      │
│ Marcaciones Crudas       │ 12890                  │
│ Jornadas Evaluadas       │ 320                    │
└──────────────────────────┴────────────────────────┘
```

---

## 🤖 Automatización con Crontab / Systemd

La CLI de AsistPy está optimizada para operar de forma desatendida en servidores:

```cron
# 1. Sincronizar todos los relojes cada 15 minutos (de 6:00 a 22:00)
*/15 6-22 * * * cd /opt/asistpy && .venv/bin/asistpy device sync >> /var/log/asistpy_sync.log 2>&1

# 2. Evaluar asistencias diarias a las 23:30 hrs de lunes a sábado
30 23 * * 1-6 cd /opt/asistpy && .venv/bin/asistpy attendance evaluate >> /var/log/asistpy_evaluate.log 2>&1

# 3. Exportar reporte consolidado cada domingo a las 23:59 hrs
59 23 * * 0 cd /opt/asistpy && .venv/bin/asistpy report summary --start-date $(date -d "6 days ago" +\%Y-\%m-\%d) --end-date $(date +\%Y-\%m-\%d) --format csv --output /srv/reportes/asistencia_semanal.csv
```

---

## 🚦 Códigos de Salida (Exit Codes)

| Código | Significado | Causa típica |
| :---: | :--- | :--- |
| `0` | **Éxito (Success)** | La operación se completó exitosamente. |
| `1` | **Error Operativo / Excepción** | Registro no encontrado, fallo de conexión o validación no superada. |
| `2` | **Fallo Parcial de Dispositivos** | En `device sync`, al menos un reloj activo falló la sincronización. |
| `130` | **Cancelado por Usuario** | Interrupción mediante `Ctrl+C` (`SIGINT`). |

---

> Para más detalles sobre la arquitectura del dominio, consulta el documento principal [README.md](../README.md).
