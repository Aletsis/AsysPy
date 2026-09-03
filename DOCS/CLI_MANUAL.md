# 📖 Manual de Uso: CLI Unificada de AsistPy (`asistpy`)

> **Herramienta de consola oficial de AsistPy para administración, diagnóstico de hardware, sincronización de relojes biométricos, evaluación de jornadas laborales y generación de reportes.**

---

## 📋 Tabla de Contenidos

1. [Introducción y Arquitectura](#-introducción-y-arquitectura)
2. [Instalación y Configuración](#-instalación-y-configuración)
3. [Estructura y Sintaxis General](#-estructura-y-sintaxis-general)
4. [Opciones Globales](#-opciones-globales)
5. [Comandos de Base de Datos (`asistpy db`)](#-comandos-de-base-de-datos-asistpy-db)
   - [`asistpy db init`](#asistpy-db-init)
   - [`asistpy db status`](#asistpy-db-status)
6. [Comandos de Dispositivos Biométricos (`asistpy device`)](#-comandos-de-dispositivos-biométricos-asistpy-device)
   - [`asistpy device probe`](#asistpy-device-probe)
   - [`asistpy device sync`](#asistpy-device-sync)
   - [`asistpy device list`](#asistpy-device-list)
7. [Comandos de Asistencia y Jornadas (`asistpy attendance`)](#-comandos-de-asistencia-y-jornadas-asistpy-attendance)
   - [`asistpy attendance evaluate`](#asistpy-attendance-evaluate)
   - [`asistpy attendance list`](#asistpy-attendance-list)
   - [`asistpy attendance adjust`](#asistpy-attendance-adjust)
8. [Comandos de Reportes y Exportación (`asistpy report`)](#-comandos-de-reportes-y-exportación-asistpy-report)
   - [`asistpy report summary`](#asistpy-report-summary)
9. [Automatización con Crontab / Systemd](#-automatización-con-crontab--systemd)
10. [Códigos de Salida (Exit Codes)](#-códigos-de-salida-exit-codes)

---

## 🌟 Introducción y Arquitectura

La CLI `asistpy` actúa como un **Adaptador Primario o Conductor (Driving Adapter)** dentro de la Arquitectura Hexagonal del sistema. Permite ejecutar directamente todos los casos de uso de la aplicación (`application`) contra cualquier motor de persistencia configurado (SQLite, PostgreSQL, MySQL, SQL Server o memoria) sin necesidad de iniciar servidores web ni interfaces gráficas.

Características clave:
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
- `db`: Inicialización y diagnóstico de la base de datos.
- `device`: Sondeo, catálogo y sincronización de relojes biométricos.
- `attendance`: Evaluación diaria de horarios, consulta y ajustes con auditoría.
- `report`: Consolidación y exportación a formatos de reporte (pantalla, CSV, JSON).

---

## 🌐 Opciones Globales

Puedes especificar estas opciones antes del grupo o después del subcomando:

| Opción | Descripción | Ejemplo |
| :--- | :--- | :--- |
| `--version` | Muestra la versión actual de AsistPy y finaliza. | `asistpy --version` |
| `--help`, `-h` | Muestra la ayuda de la CLI o de cualquier comando. | `asistpy attendance --help` |
| `--env-file` | Carga un archivo `.env` personalizado. | `asistpy --env-file .env.prod db status` |
| `--backend` | Sobrescribe el motor de base de datos (`sqlite`, `postgres`, `mysql`, `sqlserver`, `memory`). | `asistpy db status --backend postgres` |
| `--db-url` | Sobrescribe la cadena de conexión (`DATABASE_URL`). | `asistpy db status --db-url "sqlite:///datos.db"` |
| `-v`, `--verbose`| Habilita la traza completa de excepciones en caso de fallo. | `asistpy -v device probe` |

---

## 🗄 Comandos de Base de Datos (`asistpy db`)

### `asistpy db init`
Crea las tablas y relaciones en la base de datos configurada utilizando los modelos SQLAlchemy de AsistPy.

```bash
# Crear tablas en la base de datos por defecto (.env)
asistpy db init

# Crear tablas en una base de datos SQLite específica
asistpy db init --backend sqlite --db-url "sqlite:///sucursal_norte.db"

# Probar inicialización en memoria
asistpy db init --backend memory
```

**Salida esperada:**
```text
Iniciando esquema de base de datos...
✔ Tablas creadas/verificadas exitosamente en la base de datos:
  • attendance_logs
  • audit_logs
  • daily_attendance
  • devices
  • employees
  • incidences
  • rotation_patterns
  • schedule_assignments
  • shifts
  • sync_states
  • work_sessions

Total de tablas: 11
```

---

### `asistpy db status`
Comprueba la conectividad hacia la base de datos y muestra un inventario resumido de los registros almacenados.

```bash
asistpy db status
```

**Salida esperada:**
```text
Comprobando estado de la base de datos...
┌──────────────────────────┬──────────────────┐
│ Parámetro                │ Valor            │
├──────────────────────────┼──────────────────┤
│ Motor / Backend          │ sqlite           │
│ URL de Conexión          │ sqlite:///asistpy.db │
│ Estado de Conexión       │ Conectado (OK)   │
│ Dispositivos en Catálogo │ 3                │
│ Empleados Registrados    │ 45               │
│ Marcaciones Crudas       │ 12890            │
│ Jornadas Evaluadas       │ 320              │
└──────────────────────────┴──────────────────┘
```

---

## 🕒 Comandos de Dispositivos Biométricos (`asistpy device`)

### `asistpy device probe`
Realiza un diagnóstico de hardware hacia un reloj checador ZKTeco conectándose vía TCP (puerto 4370). Consulta versión de firmware, número de serie y total de registros de asistencia en la memoria física del reloj. Reactiva el dispositivo de forma segura al finalizar.

```bash
# Sondeo usando valores de .env (o 192.168.0.233:4370 por defecto)
asistpy device probe

# Sondeo especificando IP y puerto
asistpy device probe --ip 192.168.1.200 --port 4370 --timeout 30

# Sondeo de un dispositivo registrado en catálogo por su ID
asistpy device probe --device-id 2
```

**Salida esperada:**
```text
Sondeando dispositivo en 192.168.1.200:4370 (timeout=30s)...

✔ Conexión exitosa con el reloj biométrico.

┌───────────────────────────┬───────────────────┐
│ Parámetro                 │ Valor             │
├───────────────────────────┼───────────────────┤
│ Dirección IP              │ 192.168.1.200     │
│ Puerto TCP                │ 4370              │
│ Versión Firmware          │ Ver 6.60 Nov 2021 │
│ Número de Serie           │ CJK9203841029     │
│ Marcaciones en Dispositivo│ 1420              │
└───────────────────────────┴───────────────────┘
```

---

### `asistpy device sync`
Descarga e inserta nuevos registros de marcaciones crudas (`AttendanceLog`) en la base de datos, asegurando sincronización incremental basada en UID (evita registros duplicados).

```bash
# 1. Sincronizar TODOS los dispositivos activos registrados en catálogo:
asistpy device sync

# 2. Sincronizar únicamente los dispositivos de una sucursal:
asistpy device sync --branch-id 1

# 3. Sincronizar un único dispositivo por su ID en el catálogo:
asistpy device sync --device-id 2

# 4. Sincronización directa ad-hoc especificando IP/puerto (sin alta previa en catálogo):
asistpy device sync --ip 192.168.1.200 --port 4370

# 5. Detener inmediatamente si algún dispositivo falla (stop-on-error):
asistpy device sync --stop-on-error
```

**Salida esperada:**
```text
Iniciando sincronización masiva de dispositivos activos...

┌────┬────────────────────┬────────┬───────────────────┬────────────┐
│ ID │ Nombre             │ Estado │ Nuevas Marcaciones│ Detalle    │
├────┼────────────────────┼────────┼───────────────────┼────────────┤
│  1 │ Reloj Planta Baja  │   OK   │                45 │ Completado │
│  2 │ Reloj Almacén      │   OK   │                12 │ Completado │
│  3 │ Reloj Sucursal Sur │ FALLÓ  │                 0 │ Timeout 60s│
└────┴────────────────────┴────────┴───────────────────┴────────────┘

Resumen: Total: 3 | Exitosos: 2 | Fallidos: 1 | Nuevas Marcaciones: 57
```

---

### `asistpy device list`
Muestra la lista de relojes checadores registrados en el catálogo de base de datos.

```bash
# Listar todos los dispositivos
asistpy device list

# Filtrar solo dispositivos activos
asistpy device list --active-only

# Filtrar por sucursal
asistpy device list --branch-id 1
```

**Salida esperada:**
```text
┌────┬───────────────────┬───────────────┬────────┬──────────┬────────┬─────────────────────────┐
│ ID │ Nombre            │ IP            │ Puerto │ Sucursal │ Estado │ Último UID Sincronizado │
├────┼───────────────────┼───────────────┼────────┼──────────┼────────┼─────────────────────────┤
│  1 │ Reloj Recepción   │ 192.168.1.100 │   4370 │        1 │ Activo │                    4521 │
│  2 │ Reloj Comedor     │ 192.168.1.101 │   4370 │        1 │ Activo │                    2103 │
│  3 │ Reloj Puerta 2    │ 192.168.2.50  │   4370 │        2 │ Inactivo│                     890 │
└────┴───────────────────┴───────────────┴────────┴──────────┴────────┴─────────────────────────┘

Total dispositivos: 3
```

---

## ⏱ Comandos de Asistencia y Jornadas (`asistpy attendance`)

### `asistpy attendance evaluate`
Ejecuta el motor de evaluación de jornadas:
1. Resuelve el turno y horario esperado del empleado según su asignación activa.
2. Empareja entradas y salidas (*punch pairing*) aislando rebotes.
3. Evalúa cumplimiento, retardos, salidas anticipadas y horas extras.
4. Almacena el resultado consolidado en `DailyAttendance`.

```bash
# 1. Evaluar a TODOS los empleados activos para el día de hoy:
asistpy attendance evaluate

# 2. Evaluar a TODOS los empleados activos en una fecha específica:
asistpy attendance evaluate --date 2026-09-02

# 3. Evaluar un empleado específico en una fecha:
asistpy attendance evaluate --employee-pin "E001" --date 2026-09-02

# 4. Evaluar un empleado en un rango de fechas:
asistpy attendance evaluate --employee-pin "E001" --start-date 2026-09-01 --end-date 2026-09-15

# 5. Filtrar lote por sucursal y declarar día festivo/feriado:
asistpy attendance evaluate --branch-id 1 --date 2026-09-16 --holiday
```

**Salida esperada:**
```text
Evaluando jornada en lote para empleados activos al 2026-09-02...

┌──────┬────────────┬────────────────┬──────────┬──────────┬───────────┬─────────┬────────────┬─────────────┬───────────┐
│ PIN  │ Fecha      │ Turno Esperado │ Entrada  │ Salida   │ Trabajado │ Retardo │ Salida Ant.│ Horas Extra │ Estado    │
├──────┼────────────┼────────────────┼──────────┼──────────┼───────────┼─────────┼────────────┼─────────────┼───────────┤
│ E001 │ 2026-09-02 │ Matutino 8-16  │ 07:58:12 │ 16:02:40 │ 8h 4m     │      0m │         0m │          0m │ PRESENTE  │
│ E002 │ 2026-09-02 │ Matutino 8-16  │ 08:18:00 │ 16:00:10 │ 7h 42m    │     18m │         0m │          0m │ PRESENTE  │
│ E003 │ 2026-09-02 │ Vespertino     │ --:--:-- │ --:--:-- │ 0m        │      0m │         0m │          0m │ FALTA     │
└──────┴────────────┴────────────────┴──────────┴──────────┴───────────┴─────────┴────────────┴─────────────┴───────────┘

✔ Evaluación completada. Total registros evaluados: 3
```

---

### `asistpy attendance list`
Permite consultar el historial de jornadas evaluadas o las marcaciones crudas almacenadas.

```bash
# Listar las últimas 50 jornadas evaluadas
asistpy attendance list

# Filtrar jornadas de un empleado específico
asistpy attendance list --employee-pin "E001"

# Filtrar jornadas de un rango de fechas
asistpy attendance list --start-date 2026-09-01 --end-date 2026-09-07

# Consultar marcaciones CRUDAS del reloj biométrico (sin evaluar)
asistpy attendance list --raw --limit 20
```

---

### `asistpy attendance adjust`
Permite a supervisores o personal de Recursos Humanos realizar correcciones manuales de marcaciones o insertar marcaciones omitidas, garantizando **trazabilidad inmutable en la bitácora de auditoría (`audit_logs`)**.

```bash
# 1. Crear una marcación manual omitida:
asistpy attendance adjust \
  --employee-pin "E001" \
  --timestamp "2026-09-02 08:00:00" \
  --reason "Olvido de gafete en caseta" \
  --modified-by "jefe_rrhh"

# 2. Modificar una marcación existente por su ID:
asistpy attendance adjust \
  --log-id 1520 \
  --timestamp "2026-09-02 16:00:00" \
  --reason "Corrección autorizada por salida tardía en junta" \
  --modified-by "supervisor_turno"
```

**Salida esperada:**
```text
Creando marcación manual para empleado E001 al 2026-09-02 08:00:00...

✔ Marcación manual creada exitosamente.
  • Marcación ID: 341
  • Empleado: E001
  • Fecha/Hora: 2026-09-02 08:00:00
  • Motivo: Olvido de gafete en caseta
  • Registrado en Auditoría por: jefe_rrhh
```

---

## 📊 Comandos de Reportes y Exportación (`asistpy report`)

### `asistpy report summary`
Genera un informe consolidado del período seleccionado con totales de horas trabajadas, retardos acumulados, horas extras y ausencias.

#### 1. Salida en consola (Formato Tabla)
```bash
asistpy report summary --start-date 2026-09-01 --end-date 2026-09-07
```

**Salida:**
```text
┌──────┬────────────┬──────────┬──────────┬────────────────────┬─────────┬─────────────┬──────────┐
│ PIN  │ Fecha      │ Entrada  │ Salida   │ Minutos Trabajados │ Retardo │ Horas Extra │ Estado   │
├──────┼────────────┼──────────┼──────────┼────────────────────┼─────────┼─────────────┼──────────┤
│ E001 │ 2026-09-01 │ 08:00:00 │ 16:00:00 │                480 │       0 │           0 │ PRESENT  │
│ E001 │ 2026-09-02 │ 08:15:00 │ 16:00:00 │                465 │      15 │           0 │ PRESENT  │
│ E002 │ 2026-09-01 │ --:--:-- │ --:--:-- │                  0 │       0 │           0 │ ABSENT   │
└──────┴────────────┴──────────┴──────────┴────────────────────┴─────────┴─────────────┴──────────┘

Resumen Consolidado:
  • Total registros evaluados: 3
  • Total horas trabajadas: 15h 45m (945 min)
  • Total minutos retardo: 15
  • Total minutos horas extra: 0
  • Total inasistencias/faltas: 1
```

#### 2. Exportación a archivo CSV
Ideal para importar directamente en Excel, sistemas ERP o software de nómina.
```bash
asistpy report summary \
  --start-date 2026-09-01 \
  --end-date 2026-09-15 \
  --format csv \
  --output reportes/asistencia_primera_quincena.csv
```

#### 3. Exportación a archivo o flujo JSON
Ideal para pipelines de datos o integraciones por API:
```bash
asistpy report summary \
  --start-date 2026-09-01 \
  --end-date 2026-09-07 \
  --format json \
  --output reportes/semana36.json
```

---

## 🤖 Automatización con Crontab / Systemd

La CLI de AsistPy está especialmente diseñada para operar en servidores sin interfaz gráfica (*headless*) mediante tareas programadas.

### Ejemplo de configuración en Crontab (`crontab -e`):
```cron
# 1. Sincronizar todos los relojes checadores cada 15 minutos (de 6:00 a 22:00)
*/15 6-22 * * * cd /opt/asistpy && .venv/bin/asistpy device sync >> /var/log/asistpy_sync.log 2>&1

# 2. Evaluar y cerrar asistencias del día a las 23:30 hrs de lunes a sábado
30 23 * * 1-6 cd /opt/asistpy && .venv/bin/asistpy attendance evaluate >> /var/log/asistpy_evaluate.log 2>&1

# 3. Exportar reporte semanal de asistencia cada domingo a las 23:59 hrs
59 23 * * 0 cd /opt/asistpy && .venv/bin/asistpy report summary --start-date $(date -d "6 days ago" +\%Y-\%m-\%d) --end-date $(date +\%Y-\%m-\%d) --format csv --output /srv/reportes/asistencia_semanal.csv
```

---

## 🚦 Códigos de Salida (Exit Codes)

La CLI implementa códigos de salida estándar para scripts de shell:

| Código | Significado | Causa típica |
| :---: | :--- | :--- |
| `0` | **Éxito (Success)** | La operación se completó exitosamente. |
| `1` | **Error Operativo / Excepción** | Fallo de conexión a base de datos, archivo no encontrado o validación de negocio no superada. |
| `2` | **Fallo Parcial de Dispositivos** | En `device sync`, al menos un reloj biométrico activo falló la sincronización. |
| `130` | **Cancelado por Usuario** | El usuario canceló la ejecución mediante `Ctrl+C` (`SIGINT`). |

---

> Para más detalles sobre la arquitectura del dominio y desarrollo de nuevos adaptadores, consulta el documento principal [README.md](../README.md).
