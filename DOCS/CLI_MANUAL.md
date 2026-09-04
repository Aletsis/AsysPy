# 📖 Manual de Uso: CLI Unificada de AsistPy (`asistpy`)

> **Herramienta de consola oficial de AsistPy para administración, gestión CRUD de catálogos maestros, diagnóstico de hardware, sincronización de relojes biométricos, evaluación de jornadas laborales y generación de reportes.**

---

## 📋 Tabla de Contenidos

1. [Introducción y Arquitectura](#-introducción-y-arquitectura)
2. [Instalación y Configuración](#-instalación-y-configuración)
3. [Estructura y Sintaxis General](#-estructura-y-sintaxis-general)
4. [Opciones Globales](#-opciones-globales)
5. [CRUD de Sucursales (`asistpy branch`)](#-crud-de-sucursales-asistpy-branch)
6. [CRUD de Departamentos (`asistpy department`)](#-crud-de-departamentos-asistpy-department)
7. [CRUD de Puestos de Trabajo (`asistpy position`)](#-crud-de-puestos-de-trabajo-asistpy-position)
8. [CRUD de Empleados (`asistpy employee`)](#-crud-de-empleados-asistpy-employee)
9. [CRUD de Turnos de Trabajo (`asistpy shift`)](#-crud-de-turnos-de-trabajo-asistpy-shift)
10. [CRUD de Asignaciones de Horario (`asistpy schedule`)](#-crud-de-asignaciones-de-horario-asistpy-schedule)
11. [CRUD y Control de Dispositivos Biométricos (`asistpy device`)](#-crud-y-control-de-dispositivos-biométricos-asistpy-device)
12. [Control de Asistencia y Jornadas (`asistpy attendance`)](#-control-de-asistencia-y-jornadas-asistpy-attendance)
13. [Reportes y Exportación (`asistpy report`)](#-reportes-y-exportación-asistpy-report)
14. [Gestión de Base de Datos (`asistpy db`)](#-gestión-de-base-de-datos-asistpy-db)
15. [Demonio en Segundo Plano (`asistpy worker`)](#-demonio-en-segundo-plano-asistpy-worker)
16. [Despliegue con Docker y Docker Compose](#-despliegue-con-docker-y-docker-compose)
17. [Automatización con Crontab / Systemd](#-automatización-con-crontab--systemd)
18. [Códigos de Salida (Exit Codes)](#-códigos-de-salida-exit-codes)

---

## 🌟 Introducción y Arquitectura

La CLI `asistpy` actúa como un **Adaptador Primario o Conductor (Driving Adapter)** dentro de la Arquitectura Hexagonal del sistema. Permite ejecutar directamente todos los casos de uso de la aplicación (`application`) contra cualquier motor de persistencia configurado (SQLite, PostgreSQL, MySQL, SQL Server o memoria) sin necesidad de iniciar servidores web ni interfaces gráficas.

Características clave:
- **CRUD Completo de Catálogos**: Alta, consulta detallada, listado, edición y eliminación de sucursales, departamentos, puestos, empleados, turnos, horarios y dispositivos.
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
- `department`: Catálogo CRUD de departamentos u áreas operativas.
- `position`: Catálogo CRUD de puestos o cargos laborales y vinculación con departamentos.
- `employee`: Catálogo CRUD de empleados y personal con atributos biométricos y fiscales.
- `shift`: Catálogo CRUD de turnos de trabajo y tolerancias.
- `schedule`: Catálogo CRUD y asignación de horarios a empleados.
- `device`: Catálogo CRUD, sondeo y sincronización de relojes biométricos.
- `attendance`: Evaluación diaria de horarios, consulta y ajustes con auditoría.
- `report`: Consolidación y exportación a formatos de reporte (pantalla, CSV, JSON).
- `db`: Inicialización y diagnóstico de la base de datos.
- `worker`: Demonio en segundo plano para sincronización automática 24/7.

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

**Salida de ejemplo:**
```text
✔ Sucursal Sucursal Matriz (Código: MAT-01) registrada exitosamente con ID 1.
┌────┬────────┬─────────────────┬─────────────────────┬────────┐
│ ID │ Código │ Nombre          │ Zona Horaria        │ Estado │
├────┼────────┼─────────────────┼─────────────────────┼────────┤
│  1 │ MAT-01 │ Sucursal Matriz │ America/Mexico_City │ Activo │
└────┴────────┴─────────────────┴─────────────────────┴────────┘
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

**Salida de ejemplo:**
```text
┌────┬────────┬────────────────────┬─────────────────────┬─────────────────┬────────┐
│ ID │ Código │ Nombre             │ Zona Horaria        │ Ciudad / Estado │ Estado │
├────┼────────┼────────────────────┼─────────────────────┼─────────────────┼────────┤
│  1 │ MAT-01 │ Sucursal Matriz    │ America/Mexico_City │ -               │ Activo │
│  2 │ GDL-01 │ Planta Guadalajara │ America/Mexico_City │ Guadalajara     │ Activo │
└────┴────────┴────────────────────┴─────────────────────┴─────────────────┴────────┘

Total sucursales: 2
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

## 📂 CRUD de Departamentos (`asistpy department`)

Permite registrar y organizar los departamentos, gerencias o áreas funcionales de la empresa.

### 1. `asistpy department add` (Crear)
```bash
# Registrar un departamento general (aplica a toda la empresa)
asistpy department add --name "Recursos Humanos" --code "RH-01"

# Registrar un departamento vinculado a una sucursal específica
asistpy department add --name "Mantenimiento Planta" --code "MNT-01" --branch-id 1

# Registrar departamento directamente inactivo
asistpy department add --name "Área Temporal" --code "TMP-01" --inactive
```

**Salida de ejemplo:**
```text
✔ Departamento Recursos Humanos registrado exitosamente con ID 1.
┌────┬────────┬──────────────────┬─────────────┬────────┐
│ ID │ Código │ Nombre           │ Sucursal ID │ Estado │
├────┼────────┼──────────────────┼─────────────┼────────┤
│  1 │ RH-01  │ Recursos Humanos │      1      │ Activo │
└────┴────────┴──────────────────┴─────────────┴────────┘
```

### 2. `asistpy department show` (Ver Detalle)
```bash
# Consultar por código
asistpy department show --code "RH-01"

# Consultar por ID
asistpy department show --department-id 1
```

### 3. `asistpy department list` (Listar)
```bash
# Listar todos los departamentos
asistpy department list

# Filtrar por sucursal
asistpy department list --branch-id 1

# Filtrar solo activos
asistpy department list --active-only
```

**Salida de ejemplo:**
```text
┌────┬────────┬──────────────────────┬─────────────┬────────┐
│ ID │ Código │ Nombre               │ Sucursal ID │ Estado │
├────┼────────┼──────────────────────┼─────────────┼────────┤
│  1 │ RH-01  │ Recursos Humanos     │      1      │ Activo │
│  2 │ MNT-01 │ Mantenimiento Planta │      1      │ Activo │
└────┴────────┴──────────────────────┴─────────────┴────────┘

Total departamentos: 2
```

### 4. `asistpy department edit` (Modificar)
```bash
# Modificar nombre y código
asistpy department edit --code "RH-01" --name "Capital Humano" --new-code "CH-01"

# Desactivar departamento
asistpy department edit --code "CH-01" --inactive

# Reactivar departamento
asistpy department edit --code "CH-01" --active
```

### 5. `asistpy department delete` (Eliminar)
```bash
# Eliminar por código
asistpy department delete --code "CH-01" --force

# Eliminar por ID
asistpy department delete --department-id 1 --force
```

### 6. `asistpy department assign-position` (Vincular Puesto)
```bash
# Asociar un puesto al departamento
asistpy department assign-position --department-id 1 --position-id 2
# o por código:
asistpy department assign-position --code "RH-01" --position-id 2
```

### 7. `asistpy department remove-position` (Desvincular Puesto)
```bash
asistpy department remove-position --department-id 1 --position-id 2
```

---

## 💼 CRUD de Puestos de Trabajo (`asistpy position`)

Permite administrar el catálogo canónico de puestos o cargos de la empresa y gestionar su vinculación N:M con los departamentos organizacionales.

### 1. `asistpy position add` (Crear)
```bash
# Registrar un puesto básico
asistpy position add --name "Operador CNC" --code "CNC-01"

# Registrar con descripción completa
asistpy position add \
  --name "Desarrollador Senior" \
  --code "DEV-01" \
  --description "Desarrollo y arquitectura backend de sistemas de control"

# Registrar puesto directamente inactivo
asistpy position add --name "Puesto Temporal" --code "TMP-01" --inactive
```

**Salida de ejemplo:**
```text
✔ Puesto Desarrollador Senior registrado exitosamente con ID 1.
┌────┬────────┬──────────────────────┬──────────────────────────────────────────┬────────┐
│ ID │ Código │ Nombre               │ Descripción                              │ Estado │
├────┼────────┼──────────────────────┼──────────────────────────────────────────┼────────┤
│  1 │ DEV-01 │ Desarrollador Senior │ Desarrollo y arquitectura backend ...    │ Activo │
└────┴────────┴──────────────────────┴──────────────────────────────────────────┴────────┘
```

### 2. `asistpy position show` (Ver Detalle)
```bash
# Consultar por código
asistpy position show --code "DEV-01"

# Consultar por ID
asistpy position show --id 1

# Consultar por nombre
asistpy position show --name "Desarrollador Senior"
```

**Salida de ejemplo:**
```text
Detalle de Puesto:
┌─────────────────────────┬────────────────────────────────────────────────────────┐
│ Propiedad               │ Valor                                                  │
├─────────────────────────┼────────────────────────────────────────────────────────┤
│ ID                      │ 1                                                      │
│ Código                  │ DEV-01                                                 │
│ Nombre                  │ Desarrollador Senior                                   │
│ Descripción             │ Desarrollo y arquitectura backend de sistemas...      │
│ Departamentos Asociados │ Sistemas (#1), Innovación (#3)                         │
│ Estado                  │ Activo                                                 │
└─────────────────────────┴────────────────────────────────────────────────────────┘
```

### 3. `asistpy position list` (Listar)
```bash
# Listar todos los puestos
asistpy position list

# Filtrar por departamento asociado
asistpy position list --department-id 1

# Filtrar solo activos
asistpy position list --active-only
```

### 4. `asistpy position edit` (Modificar)
```bash
# Modificar nombre y descripción
asistpy position edit --code "DEV-01" --name "Líder Técnico Backend" --new-code "TL-01"

# Desactivar puesto
asistpy position edit --code "TL-01" --inactive

# Reactivar puesto
asistpy position edit --code "TL-01" --active
```

### 5. `asistpy position delete` (Eliminar)
```bash
asistpy position delete --code "TL-01" --force
# o por ID:
asistpy position delete --id 1 --force
```

### 6. `asistpy position assign-department` / `remove-department` (Relación N:M)
```bash
# Asociar a departamento
asistpy position assign-department --position-id 1 --department-id 2

# Desasociar de departamento
asistpy position remove-department --position-id 1 --department-id 2
```

---

## 👥 CRUD de Empleados (`asistpy employee`)

Permite gestionar el padrón de trabajadores y colaboradores que checan asistencia en los relojes biométricos, incluyendo datos de contacto, fiscales, llaves de acceso en dispositivos y credenciales RFID.

### 1. `asistpy employee add` (Crear)
```bash
# Alta completa con atributos de contacto, fiscales y credenciales de checador
asistpy employee add \
  --pin "E101" \
  --first-name "Carlos" \
  --paternal-last-name "Gómez" \
  --maternal-last-name "López" \
  --hire-date 2024-03-15 \
  --sex male \
  --position-id 1 \
  --department-id 2 \
  --branch-id 1 \
  --email "carlos.gomez@empresa.com" \
  --phone "+52 33 1234 5678" \
  --curp "GOLC880315HDFMNR01" \
  --rfc "GOLC880315ABC" \
  --password "1234" \
  --card-number "CARD-1001"
```

**Salida de ejemplo:**
```text
✔ Empleado Carlos Gómez (PIN: E101) registrado exitosamente con ID 1.
┌────┬──────┬─────────────────┬──────────────────────┬──────────┬─────────────┬────────────────────┬───────────┬────────┐
│ ID │ PIN  │ Nombre Completo │ Puesto               │ Depto ID │ Sucursal ID │ CURP               │ Tarjeta   │ Estado │
├────┼──────┼─────────────────┼──────────────────────┼──────────┼─────────────┼────────────────────┼───────────┼────────┤
│  1 │ E101 │ Carlos Gómez    │ Operador CNC (ID:1)  │        2 │           1 │ GOLC880315HDFMNR01 │ CARD-1001 │ Activo │
└────┴──────┴─────────────────┴──────────────────────┴──────────┴─────────────┴────────────────────┴───────────┴────────┘
```

### 2. `asistpy employee show` (Ver Detalle)
```bash
# Por PIN
asistpy employee show --pin "E101"

# Por ID interno
asistpy employee show --id 1
```

**Salida de ejemplo:**
```text
Detalle de Empleado:
┌───────────────────────────┬───────────────────────────┐
│ Propiedad                 │ Valor                     │
├───────────────────────────┼───────────────────────────┤
│ ID                        │ 1                         │
│ PIN / Identificador       │ E101                      │
│ Nombre Completo           │ Carlos Gómez              │
│ Nombre                    │ Carlos                    │
│ Apellido Paterno          │ Gómez                     │
│ Apellido Materno          │ López                     │
│ Fecha de Contratación     │ 2024-03-15                │
│ Sexo                      │ male                      │
│ Puesto / Cargo            │ Operador CNC              │
│ Puesto ID                 │ 1                         │
│ Departamento ID           │ 2                         │
│ Sucursal Base ID          │ 1                         │
│ Correo Electrónico        │ carlos.gomez@empresa.com  │
│ Teléfono                  │ +52 33 1234 5678          │
│ CURP                      │ GOLC880315HDFMNR01        │
│ RFC                       │ GOLC880315ABC             │
│ Contraseña / Clave        │ ********                  │
│ Tarjeta RFID / Proximidad │ CARD-1001                 │
│ Huellas Biométricas       │ 2 registrada(s)           │
│ Estado                    │ Activo                    │
└───────────────────────────┴───────────────────────────┘
```

### 3. `asistpy employee list` (Listar)
```bash
# Listar todos los empleados
asistpy employee list

# Filtrar por sucursal
asistpy employee list --branch-id 1

# Filtrar por departamento
asistpy employee list --department-id 2

# Filtrar por puesto laboral
asistpy employee list --position-id 1

# Filtrar solo empleados activos
asistpy employee list --active-only

# Buscar por coincidencia de PIN
asistpy employee list --pin "101"
```

**Salida de ejemplo:**
```text
┌────┬──────┬─────────────────┬──────────────────────┬───────┬──────────┬───────────────┬────────┐
│ ID │ PIN  │ Nombre Completo │ Puesto               │ Depto │ Sucursal │ Fecha Ingreso │ Estado │
├────┼──────┼─────────────────┼──────────────────────┼───────┼──────────┼───────────────┼────────┤
│  1 │ E101 │ Carlos Gómez    │ Operador CNC (#1)    │     2 │        1 │  2024-03-15   │ Activo │
│  2 │ E102 │ Ana Martínez    │ RRHH General (#2)    │     1 │        1 │  2023-01-10   │ Activo │
└────┴──────┴─────────────────┴──────────────────────┴───────┴──────────┴───────────────┴────────┘

Total empleados: 2
```

### 4. `asistpy employee edit` (Modificar)
```bash
# Modificar datos personales y de contacto
asistpy employee edit \
  --pin "E101" \
  --email "carlos.gomez.nuevo@empresa.com" \
  --phone "+52 33 9999 8888" \
  --card-number "CARD-2002"

# Cambiar de puesto y departamento
asistpy employee edit --pin "E101" --position-id 2 --department-id 1

# Dar de baja (inactivar)
asistpy employee edit --pin "E101" --inactive

# Reactivar empleado
asistpy employee edit --pin "E101" --active
```

### 5. `asistpy employee delete` (Eliminar)
```bash
# Eliminar por PIN
asistpy employee delete --pin "E101" --force

# Eliminar por ID interno
asistpy employee delete --id 1 --force
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

**Salida de ejemplo:**
```text
✔ Turno Matutino 8-16 registrado exitosamente con ID 1.
┌────┬───────────────┬───────────┬─────────┬────────┬────────────┬──────────────────┐
│ ID │ Nombre        │ Categoría │ Entrada │ Salida │ Tolerancia │ Cruza Medianoche │
├────┼───────────────┼───────────┼─────────┼────────┼────────────┼──────────────────┤
│  1 │ Matutino 8-16 │ regular   │  08:00  │ 16:00  │     15 min │        No        │
└────┴───────────────┴───────────┴─────────┴────────┴────────────┴──────────────────┘
```

### 2. `asistpy shift show` (Ver Detalle)
```bash
asistpy shift show --shift-id 1
```

### 3. `asistpy shift list` (Listar)
```bash
asistpy shift list
```

**Salida de ejemplo:**
```text
┌────┬────────────────┬───────────┬─────────┬────────┬────────────┬──────────────────┐
│ ID │ Nombre         │ Categoría │ Entrada │ Salida │ Tolerancia │ Cruza Medianoche │
├────┼────────────────┼───────────┼─────────┼────────┼────────────┼──────────────────┤
│  1 │ Matutino 8-16  │ regular   │  08:00  │ 16:00  │     15 min │        No        │
│  2 │ Nocturno 22-06 │ nocturno  │  22:00  │ 06:00  │     10 min │        Sí        │
└────┴────────────────┴───────────┴─────────┴────────┴────────────┴──────────────────┘

Total turnos: 2
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

**Salida de ejemplo:**
```text
✔ Horario asignado exitosamente con ID 1.
┌────┬──────────────┬──────────────┬───────────────┬───────┬──────────────┬──────────────┐
│ ID │ PIN Empleado │ Empleado     │ Turno         │ Modo  │ Válido Desde │ Válido Hasta │
├────┼──────────────┼──────────────┼───────────────┼───────┼──────────────┼──────────────┤
│  1 │ E101         │ Carlos Gómez │ Matutino 8-16 │ fixed │  2026-09-01  │  Indefinido  │
└────┴──────────────┴──────────────┴───────────────┴───────┴──────────────┴──────────────┘
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

**Salida de ejemplo:**
```text
┌────┬──────────────┬───────┬──────────┬──────────────┬──────────────┐
│ ID │ PIN Empleado │ Modo  │ Turno ID │ Válido Desde │ Válido Hasta │
├────┼──────────────┼───────┼──────────┼──────────────┼──────────────┤
│  1 │ E101         │ fixed │        1 │  2026-09-01  │  Indefinido  │
└────┴──────────────┴───────┴──────────┴──────────────┴──────────────┘

Total asignaciones: 1
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

**Salida de ejemplo:**
```text
✔ Dispositivo registrado exitosamente con ID 1.
┌────┬─────────────────┬───────────────┬────────┬──────────┬───────────────┬────────┐
│ ID │ Nombre          │ IP            │ Puerto │ Sucursal │ Serie         │ Estado │
├────┼─────────────────┼───────────────┼────────┼──────────┼───────────────┼────────┤
│  1 │ Reloj Recepción │ 192.168.1.200 │   4370 │        1 │ CJK9203841029 │ Activo │
└────┴─────────────────┴───────────────┴────────┴──────────┴───────────────┴────────┘
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

**Salida de ejemplo:**
```text
┌────┬─────────────────┬───────────────┬────────┬──────────┬────────┬─────────────────────────┐
│ ID │ Nombre          │ IP            │ Puerto │ Sucursal │ Estado │ Último UID Sincronizado │
├────┼─────────────────┼───────────────┼────────┼──────────┼────────┼─────────────────────────┤
│  1 │ Reloj Recepción │ 192.168.1.200 │   4370 │        1 │ Activo │                    4820 │
│  2 │ Reloj Comedor   │ 192.168.1.201 │   4370 │        1 │ Activo │                    1540 │
└────┴─────────────────┴───────────────┴────────┴──────────┴────────┴─────────────────────────┘

Total dispositivos: 2
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

**Salida de ejemplo:**
```text
Sondeando dispositivo en 192.168.1.200:4370 (timeout=60s)...

✔ Conexión exitosa con el reloj biométrico.

┌────────────────────────────┬───────────────────┐
│ Parámetro                  │ Valor             │
├────────────────────────────┼───────────────────┤
│ Dirección IP               │ 192.168.1.200     │
│ Puerto TCP                 │ 4370              │
│ Versión Firmware           │ Ver 6.60 Nov 2021 │
│ Número de Serie            │ CJK9203841029     │
│ Marcaciones en Dispositivo │ 4820              │
└────────────────────────────┴───────────────────┘
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

**Salida de ejemplo:**
```text
Iniciando sincronización masiva de dispositivos activos...
✔ Sincronización finalizada para 'Reloj Recepción': 14 nuevas marcaciones almacenadas.
✔ Sincronización finalizada para 'Reloj Comedor': 5 nuevas marcaciones almacenadas.

Resumen de sincronización:
┌───────────────────────────┬───────┐
│ Métrica                   │ Valor │
├───────────────────────────┼───────┤
│ Dispositivos Procesados   │ 2     │
│ Sincronizados con Éxito   │ 2     │
│ Fallidos                  │ 0     │
│ Total Nuevas Marcaciones  │ 19    │
└───────────────────────────┴───────┘
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

**Salida de ejemplo:**
```text
Evaluando jornada en lote para empleados activos al 2026-09-02...

┌──────┬────────────┬────────────────┬──────────┬──────────┬───────────┬─────────┬─────────────┬─────────────┬──────────┐
│ PIN  │   Fecha    │ Turno Esperado │ Entrada  │  Salida  │ Trabajado │ Retardo │ Salida Ant. │ Horas Extra │ Estado   │
├──────┼────────────┼────────────────┼──────────┼──────────┼───────────┼─────────┼─────────────┼─────────────┼──────────┤
│ E101 │ 2026-09-02 │ Matutino 8-16  │ 07:58:12 │ 16:05:30 │    8h  7m │      0m │          0m │          0m │ PRESENTE │
│ E102 │ 2026-09-02 │ Matutino 8-16  │ 08:18:45 │ 16:01:10 │    7h 42m │     18m │          0m │          0m │ PRESENTE │
│ E103 │ 2026-09-02 │ Matutino 8-16  │ --:--:-- │ --:--:-- │        0m │      0m │          0m │          0m │ FALTA    │
└──────┴────────────┴────────────────┴──────────┴──────────┴───────────┴─────────┴─────────────┴─────────────┴──────────┘

✔ Evaluación completada. Total registros evaluados: 3
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

**Salida de ejemplo:**
```text
┌──────┬────────────┬──────────┬──────────┬───────────┬─────────┬─────────────┬─────────────┬──────────┐
│ PIN  │ Fecha      │ Entrada  │ Salida   │ Trabajado │ Retardo │ Salida Ant. │ Horas Extra │ Estado   │
├──────┼────────────┼──────────┼──────────┼───────────┼─────────┼─────────────┼─────────────┼──────────┤
│ E101 │ 2026-09-02 │ 07:58:12 │ 16:05:30 │    8h  7m │      0m │          0m │          0m │ PRESENTE │
│ E102 │ 2026-09-02 │ 08:18:45 │ 16:01:10 │    7h 42m │     18m │          0m │          0m │ PRESENTE │
│ E103 │ 2026-09-02 │ --:--:-- │ --:--:-- │        0m │      0m │          0m │          0m │ FALTA    │
└──────┴────────────┴──────────┴──────────┴───────────┴─────────┴─────────────┴─────────────┴──────────┘

Total jornadas evaluadas: 3
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

**Salida de ejemplo:**
```text
┌──────┬────────────┬──────────┬──────────┬────────────────────┬─────────┬─────────────┬──────────┐
│ PIN  │   Fecha    │ Entrada  │  Salida  │ Minutos Trabajados │ Retardo │ Horas Extra │ Estado   │
├──────┼────────────┼──────────┼──────────┼────────────────────┼─────────┼─────────────┼──────────┤
│ E101 │ 2026-09-02 │ 07:58:12 │ 16:05:30 │                487 │       0 │           0 │ present  │
│ E102 │ 2026-09-02 │ 08:18:45 │ 16:01:10 │                462 │      18 │           0 │ present  │
│ E103 │ 2026-09-02 │ --:--:-- │ --:--:-- │                  0 │       0 │           0 │ absent   │
└──────┴────────────┴──────────┴──────────┴────────────────────┴─────────┴─────────────┴──────────┘

Resumen Consolidado:
  • Total registros evaluados: 3
  • Total horas trabajadas: 15h 49m (949 min)
  • Total minutos retardo: 18
  • Total minutos horas extra: 0
  • Total inasistencias/faltas: 1
```

---

## 🗄 Gestión de Base de Datos (`asistpy db`)

### 1. `asistpy db init`
Crea las tablas en la base de datos configurada (`branches`, `employees`, `shifts`, `devices`, `daily_attendances`, etc.):
```bash
asistpy db init
```

**Salida de ejemplo:**
```text
Iniciando esquema de base de datos...
✔ Tablas creadas/verificadas exitosamente en la base de datos:
  • attendance_logs
  • audit_logs
  • branches
  • daily_attendances
  • departments
  • devices
  • employees
  • justifications
  • rotation_patterns
  • schedule_assignments
  • shifts
  • sync_states
  • work_sessions

Total de tablas: 13
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

## ⚙️ Demonio en Segundo Plano (`asistpy worker`)

El comando `asistpy worker` convierte a AsistPy en un servicio autónomo y desatendido 24/7. Está diseñado para operar sin intervención manual en servidores dedicados, contenedores Docker y dispositivos móviles (Android/Termux).

### Responsabilidades del Worker:
1. **Sincronización Periódica**: Ejecuta automáticamente `SyncAllActiveDevices` cada $N$ segundos (configurable vía `--interval` o `SYNC_INTERVAL_SECONDS`, por defecto 300 s / 5 minutos).
2. **Corte y Evaluación Nocturna**: Ejecuta automáticamente `ProcessDailyAttendanceBatch` a la hora configurada (vía `--nightly-time` o `NIGHTLY_PROCESSING_TIME`, por defecto `23:59`) para cerrar las asistencias de todo el personal activo. Si se programa durante la madrugada (ej. `00:30`), evalúa inteligentemente la jornada del día operativo anterior.
3. **Apagado Limpio (Graceful Shutdown)**: Captura señales del sistema (`SIGINT`, `SIGTERM` y `SIGBREAK` en Windows). Si se recibe una señal durante la lectura de un reloj, garantiza la finalización del flujo, la reconexión/habilitación (`enable_device()`) y la desconexión limpia del socket TCP para asegurar que **ningún reloj físico quede bloqueado o deshabilitado**.

### Sintaxis y Argumentos:
```bash
asistpy worker [OPCIONES]
```

| Opción | Variable de Entorno | Por Defecto | Descripción |
| :--- | :--- | :---: | :--- |
| `--interval <segundos>` | `SYNC_INTERVAL_SECONDS` | `300` | Segundos de espera entre cada ciclo de sincronización masiva. |
| `--nightly-time <HH:MM>` | `NIGHTLY_PROCESSING_TIME` | `23:59` | Hora local para la evaluación nocturna de la jornada. |
| `--branch-id <id>` | `SYNC_BRANCH_ID` | `None` | Restringe el worker a los relojes y empleados de una sucursal específica. |
| `--stop-on-error` | `SYNC_STOP_ON_ERROR` | `false` | Detiene el worker ante una excepción en vez de registrar el fallo y continuar. |
| `--run-nightly-on-start` | - | `false` | Ejecuta de inmediato el corte nocturno al iniciar el servicio. |
| `--once` | - | `false` | Ejecuta un único ciclo de sincronización y finaliza (útil para pruebas o cron jobs). |

### Ejemplos de Uso:

#### 1. Iniciar worker continuo cada 5 minutos
```bash
asistpy worker
```

#### 2. Sincronización rápida cada 60 segundos y corte a las 22:30 hrs
```bash
asistpy worker --interval 60 --nightly-time 22:30
```

#### 3. Worker dedicado para una sucursal (ej. Sucursal Norte ID: 2)
```bash
asistpy worker --branch-id 2 --interval 120
```

#### 4. Ejecución en Android (Termux)
```bash
# En terminal Termux conectada a la red Wi-Fi de la empresa:
asistpy worker --interval 300
```

**Salida de ejemplo durante la ejecución continua:**
```text
[2026-09-03 23:55:00] [asistpy-worker] === Servicio AsistPy Worker Iniciado ===
[2026-09-03 23:55:00] [asistpy-worker] Configuración: intervalo=300s, hora_cierre=23:59
[2026-09-03 23:55:00] [asistpy-worker] Esperando eventos (Presione Ctrl+C o envíe SIGTERM para detener)...
[2026-09-03 23:55:01] [asistpy-worker] Iniciando ciclo de sincronización masiva...
[2026-09-03 23:55:03] [asistpy-worker]   [✔] Dispositivo 'Reloj Entrada' (ID: 1): 12 nuevas marcaciones.
[2026-09-03 23:55:04] [asistpy-worker]   [✔] Dispositivo 'Reloj Comedor' (ID: 2): 4 nuevas marcaciones.
[2026-09-03 23:55:04] [asistpy-worker] Sincronización completada: 2/2 dispositivos OK, 0 fallidos. Total nuevas marcaciones: 16.
[2026-09-03 23:59:00] [asistpy-worker] Iniciando procesamiento nocturno de jornada diaria para fecha operativa: 2026-09-03...
[2026-09-03 23:59:02] [asistpy-worker] Procesamiento nocturno completado exitosamente: 45 empleados evaluados para 2026-09-03.
```

**Salida de ejemplo ante apagado limpio (SIGINT / SIGTERM / SIGBREAK):**
```text
[2026-09-04 00:15:30] [asistpy-worker] Recibida SIGTERM. Iniciando apagado limpio (graceful shutdown)...
[2026-09-04 00:15:30] [asistpy-worker] Liberando conexión con reloj biométrico y asegurando estado habilitado...
[2026-09-04 00:15:31] [asistpy-worker] === Servicio AsistPy Worker Detenido limpiamente ===
[2026-09-04 00:15:31] [asistpy-worker] Garantía de integridad: Ningún reloj biométrico quedó deshabilitado.
```

---

## 🐳 Despliegue con Docker y Docker Compose

AsistPy incluye un `Dockerfile` multi-stage optimizado para producción y una configuración completa en `docker-compose.yml`.

### Características de la Imagen:
- **Multi-stage build**: Imagen final ligera basada en `python:3.11-slim` sin compiladores ni dependencias de desarrollo.
- **Seguridad**: Ejecuta bajo un usuario sin privilegios `asistpy` (UID 1000).
- **Graceful Shutdown**: Configura `STOPSIGNAL SIGTERM` para que `docker stop` o `docker compose down` permitan al worker liberar los sockets biométricos de forma limpia.
- **Soporte de Bases de Datos**: Incluye controladores para PostgreSQL (`psycopg`), MySQL (`pymysql`) y SQLite.

### Inicio Rápido con Docker Compose:
El archivo `docker-compose.yml` preconfigura el servicio `asistpy-worker` vinculado a PostgreSQL con verificación de estado (`healthcheck`):

```bash
# 1. Iniciar PostgreSQL y el Worker en segundo plano:
docker compose up -d

# 2. Ver registros en tiempo real del worker:
docker compose logs -f asistpy-worker

# 3. Detener de forma limpia los servicios:
docker compose stop
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
