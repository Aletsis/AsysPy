# AsistPy 🕒

> **Servicio integral de control de asistencia para relojes biométricos, diseñado bajo Arquitectura Hexagonal (Puertos y Adaptadores) y Domain-Driven Design (DDD). Concebido para ejecutarse de forma modular en cualquier entorno (Web/API, CLI, Escritorio y Móvil) permitiendo al usuario instalar únicamente lo necesario.**

[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Architecture: Hexagonal](https://img.shields.io/badge/architecture-Hexagonal%20%2F%20DDD-green.svg)](#arquitectura-del-sistema)
[![Plataformas](https://img.shields.io/badge/plataformas-Web%20%7C%20CLI%20%7C%20Desktop%20%7C%20Mobile-informational.svg)](#-visión-multiplataforma-y-despliegue-modular)
[![Tests](https://img.shields.io/badge/tests-136%20passed-brightgreen.svg)](#-pruebas-y-calidad)
[![Linter](https://img.shields.io/badge/linter-ruff-black.svg)](#-pruebas-y-calidad)
[![Type Checker](https://img.shields.io/badge/type%20checker-mypy-blue.svg)](#-pruebas-y-calidad)

---

## 📋 Tabla de Contenidos

- [Descripción General](#-descripción-general)
- [Visión Multiplataforma y Despliegue Modular](#-visión-multiplataforma-y-despliegue-modular)
- [Arquitectura del Sistema](#-arquitectura-del-sistema)
- [Alcances y Capacidades](#-alcances-y-capacidades)
- [Estado Actual del Proyecto](#-estado-actual-del-proyecto)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Requisitos Previos](#-requisitos-previos)
- [Instalación y Configuración](#-instalación-y-configuración)
- [Instrucciones de Ejecución y Despliegue](#-instrucciones-de-ejecución-y-despliegue)
  - [Herramienta CLI Unificada (`asistpy`)](#3-herramienta-cli-unificada-asistpy)
- [Pruebas y Calidad](#-pruebas-y-calidad)
- [Pendientes y Roadmap](#-pendientes-y-roadmap)
- [Autor y Licencia](#-autor-y-licencia)

---

## 📖 Descripción General

**AsistPy** es una solución robusta, agnóstica y desacoplada para la captura, procesamiento, evaluación y almacenamiento de registros de asistencia provenientes de relojes biométricos (con soporte nativo para dispositivos ZKTeco vía protocolo TCP por puerto 4370 y extensible a otros fabricantes).

El núcleo del sistema resuelve la complejidad integral de los esquemas laborales modernos:
- Turnos fijos, rotativos y jornadas nocturnas (que cruzan la medianoche).
- Ventanas de tolerancia y gracia para entradas y salidas.
- Cálculo riguroso de minutos laborados, retardos, salidas anticipadas y horas extras sujetas a políticas organizacionales.
- Detección y clasificación automática de incidencias (faltas, omisión de entrada/salida).
- Justificaciones administrativas y ajustes manuales respaldados por una bitácora inmutable de auditoría.

---

## 🌐 Visión Multiplataforma y Despliegue Modular

Uno de los pilares de diseño de AsistPy es su **portabilidad extrema y versatilidad de despliegue**. El sistema está proyectado para que el usuario o administrador elija libremente la forma y el entorno en que desea operarlo, instalando **exclusivamente las dependencias necesarias** para ese propósito sin sobrecargar el sistema con librerías innecesarias.

```
                                         ┌───────────────────────────────────┐
                                         │       NÚCLEO COMÚN ASISTPY        │
                                         │   (Dominio + Casos de Uso DDD)    │
                                         └─────────────────┬─────────────────┘
                                                           │
             ┌───────────────────────────────┬─────────────┴───────────────┬───────────────────────────────┐
             │                               │                             │                               │
             ▼                               ▼                             ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────┐   ┌─────────────────────────┐     ┌─────────────────────────┐
│     SERVICIO WEB /      │     │      HERRAMIENTA        │   │      APLICACIÓN DE      │     │       APLICACIÓN        │
│       API SERVER        │     │        CLI              │   │        ESCRITORIO       │     │         MÓVIL           │
├─────────────────────────┤     ├─────────────────────────┤   ├─────────────────────────┤     ├─────────────────────────┤
│ • Linux / Win / macOS   │     │ • Terminal / Consola    │   │ • Windows, macOS, Linux │     │ • Android & iOS         │
│ • Docker / Microservicio│     │ • DevOps / Scripts cron │   │ • Terminal / Caseta RRHH│     │ • Supervisores en campo │
│ • FastAPI / Uvicorn     │     │ • Typer / Click / Arg   │   │ • PySide6 / Flet / GUI  │     │ • Modo Quiosco Tablet   │
│ • BD Central (Postgres) │     │ • Sync / Report / Init  │   │ • SQLite embebida       │     │ • SQLite / Sync Remoto  │
└─────────────────────────┘     └─────────────────────────┘   └─────────────────────────┘     └─────────────────────────┘
```

### 1. Modalidades de Despliegue Planificadas

1. 🌐 **Servicio Web / API Backend (Linux, Windows Server, macOS, Docker)**:
   - Para despliegue centralizado en servidores corporativos, nubes privadas o contenedores Docker.
   - Provee una API REST (FastAPI) para comunicar con sistemas de nómina (ERP/HRIS) y recolectar datos de múltiples sucursales.
   - Ideal con motores relacionales como PostgreSQL, MySQL o SQL Server.

2. 💻 **Herramienta de Línea de Comandos (CLI)**:
   - Para administradores de sistemas, servidores headless, tareas programadas en crontab, scripts bash/PowerShell y usuarios de consola.
   - Permite operar el sistema sin levantar servidores pesados ni interfaces gráficas:
     - `asistpy device probe / sync`: Sondeo y sincronización manual directa de relojes.
     - `asistpy attendance evaluate`: Evaluación y cierre de asistencias por fecha o empleado.
     - `asistpy report`: Generación rápida de reportes tabulares en pantalla o exportación a CSV/JSON.
     - `asistpy db init / migrate`: Inicialización o mantenimiento de la base de datos.

3. 🖥️ **Aplicación de Escritorio Nativa (Windows, macOS, Linux)**:
   - Para uso en estaciones de trabajo individuales, computadoras de recursos humanos o casetas de vigilancia en fábricas/oficinas que gestionan relojes locales.
   - Empaquetada como ejecutable autocontenido (.exe, .dmg, AppImage).
   - Puede operar con base de datos local SQLite (cero configuración externa) o conectarse a una base de datos centralizada.

4. 📱 **Aplicación Móvil (Android, iOS)**:
   - Para supervisores y jefes de cuadrilla en faenas mineras, construcción o trabajo de campo donde se requiere verificar asistencias in situ o usar una tablet en modo quiosco.
   - Uso de SQLite local con sincronización bajo demanda hacia el servidor central.

5. 📦 **Librería / Módulo Embebido**:
   - Puede importarse directamente dentro de otros sistemas o scripts en Python existentes como paquete de dominio puro.

### 2. Filosofía de Instalación: "Instala solo lo que necesitas"

De la misma manera en que la capa de base de datos permite instalar únicamente el driver necesario (`asistpy[sqlite]`, `asistpy[postgres]`, `asistpy[mysql]`, etc.), los runtimes y entornos de interfaz seguirán este mismo esquema de dependencias modulares opcionales (`extras`):

| Caso de Uso / Despliegue | Dependencias Necesarias | Comando de Instalación (Ejemplo) |
| :--- | :--- | :--- |
| **Servicio Backend + PostgreSQL** | Core + SQLAlchemy + Driver Postgres + API Web | `pip install "asistpy[postgres,web]"` |
| **Herramienta de Consola (CLI)** | Core + SQLite + Soporte CLI | `pip install "asistpy[cli]"` |
| **Puesto de Control Local (Escritorio)** | Core + SQLite + GUI Framework | `pip install "asistpy[sqlite,desktop]"` |
| **Dispositivo Móvil / Quiosco** | Core + SQLite + Mobile Runtime | Empaquetado optimizado para Android/iOS |
| **Pruebas / Desarrollo Ligero** | Core + Adaptadores en Memoria | `pip install "asistpy"` (sin drivers extras) |

> [!NOTE]
> La arquitectura interna ya está totalmente desacoplada para permitir este modelo. Las capas de presentación e interfaz (Web API, CLI, Desktop GUI y empaquetado Móvil) se irán liberando progresivamente como módulos independientes según el roadmap del proyecto.

---

## 🏛 Arquitectura del Sistema

El proyecto está diseñado bajo los principios de **Clean Architecture**, **Hexagonal Architecture (Puertos y Adaptadores)** y **Domain-Driven Design (DDD)**:

```
                  ┌──────────────────────────────────────────────┐
                  │                 ADAPTADORES                  │
                  │   (zk_tcp, sql, mongo, memory, cli/api/gui)  │
                  │  ┌────────────────────────────────────────┐  │
                  │  │          CASOS DE USO                  │  │
                  │  │   (application: sync, pair, evaluate)  │  │
                  │  │  ┌──────────────────────────────────┐  │  │
                  │  │  │       PUERTOS (Interfaces)       │  │  │
                  │  │  │  ┌────────────────────────────┐  │  │  │
                  │  │  │  │     DOMINIO PURO           │  │  │  │
                  │  │  │  │  (Entities, VOs, Policies) │  │  │  │
                  │  │  │  └────────────────────────────┘  │  │  │
                  │  │  └──────────────────────────────────┘  │  │
                  │  └────────────────────────────────────────┘  │
                  └──────────────────────────────────────────────┘
```

1. **Dominio Puro (`src/attendance/domain`)**:
   - Totalmente independiente de bases de datos, frameworks gráficos, librerías web o protocolos de hardware.
   - Contiene la esencia de las reglas de negocio: `Device`, `DeviceCapabilities`, `DailyAttendance`, `AttendancePairer`, `AttendanceEvaluator`, `Shift`, `Rotation`, `Incidence`, `AuditLog`.
2. **Puertos (`src/attendance/ports`)**:
   - Interfaces abstractas (Protocolos) que definen contratos para persistencia (`DeviceRepository`, `DeviceRegistry`, `AttendanceRepository`, `DailyAttendanceRepository`, `EmployeeRepository`, `SyncStateRepository`, etc.) y lectores de hardware (`DeviceReader`).
3. **Casos de Uso (`src/attendance/application`)**:
   - Orquesta la lógica del negocio: sincronización incremental de marcaciones (`sync_device_logs`), orquestación de sincronización masiva de relojes activos (`SyncAllActiveDevices`), emparejamiento entrada/salida, evaluación de jornada diaria, ajuste manual con auditoría y justificación de incidencias.
4. **Adaptadores (`src/attendance/adapters`)**:
   - **Hardware**: Adaptador `ZkTcpReader` mediante `pyzk` (TCP 4370) con bloqueo de seguridad del reloj durante la lectura.
   - **Persistencia en Memoria**: Repositorios en memoria (`InMemoryDeviceRepository`, `InMemoryAttendanceRepository`, etc.) para pruebas ultrarrápidas y desarrollo local aislado.
   - **Persistencia Relacional SQL**: Repositorios SQLAlchemy 2.0 (`SqlDeviceRepository`, `SqlAttendanceRepository`, etc.) para SQLite, PostgreSQL, MySQL y SQL Server.
   - **Persistencia NoSQL**: Cliente base para MongoDB.
   - **Fábrica Políglota (`PersistenceFactory`)**: Instanciación dinámica del conjunto de repositorios y catálogo (`PersistenceBundle.device_repo`) según configuración (`DATABASE_URL` o `PERSISTENCE_BACKEND`).

---

## 🚀 Alcances y Capacidades

### 1. Ingesta Segura desde Relojes Biométricos y Catálogo
- **Catálogo Centralizado de Dispositivos**: Administración y persistencia de relojes biométricos (`Device`) con dirección IP, puerto, sucursal, número de serie, metadatos de hardware (`DeviceCapabilities`: firmware, algoritmos, MAC) y control de estado activo/inactivo.
- **Orquestador de Sincronización Masiva (`SyncAllActiveDevices`)**: Sincronización por lote de todos los dispositivos activos del catálogo con soporte para filtrado por sucursal (`branch_id`), inyección configurable de lectores (`reader_factory`), y tolerancia a fallos por dispositivo (`stop_on_error=False`) con métricas agregadas (`SyncAllResult`).
- Lectura segura por red TCP/IP (puerto 4370) con bloqueo temporal (`disable_device`) durante la extracción de datos para evitar registros huérfanos o colisión de lecturas, asegurando su reactivación (`enable_device`) en bloques `finally`.
- Sincronización incremental: seguimiento de `last_record_uid` y `last_sync_time` para evitar duplicidad y procesar solo nuevos eventos.
- Detección de reinicio o vaciado de memoria en el dispositivo para resincronización limpia.


### 2. Motor de Emparejamiento (Punch Pairing)
- Asociación inteligente de marcaciones de entrada (*Check-In*) y salida (*Check-Out*).
- Tolerancia contra dobles marcaciones por error o rebote del sensor en ventanas breves configurables.
- Clasificación y aislamiento de marcaciones huérfanas (falta de salida o entrada no registrada).

### 3. Evaluación Diaria y Horarios Flexibles
- Soporte para **turnos fijos**, **turnos rotativos** y **jornadas que cruzan la medianoche**.
- Ventanas de tolerancia para inicio y fin de jornada (gracia por retardo).
- Cálculo exacto de minutos trabajados, minutos de retardo, salida anticipada y horas extras sujetas a políticas de la empresa.

### 4. Gestión de Incidencias y Justificaciones
- Clasificación automática de incidencias: `LATE_ARRIVAL` (Retardo), `EARLY_DEPARTURE` (Salida anticipada), `ABSENCE` (Falta), `MISSING_CHECKOUT` / `MISSING_CHECKIN`.
- Registro y asociación de justificaciones aprobadas por supervisores o recursos humanos.

### 5. Ajustes Manuales con Auditoría Estricta
- Corrección de marcaciones por parte de administradores o supervisores.
- Registro inmutable en `audit_logs`: usuario responsable, fecha/hora anterior, nueva fecha/hora, motivo y fecha de modificación.

### 6. Persistencia Políglota y Desacoplada
- Selección sin cambios de código entre SQLite, PostgreSQL, MySQL, SQL Server, MongoDB o almacenamiento en memoria a través de la fábrica de repositorios (`PersistenceFactory`).

---

## 📊 Estado Actual del Proyecto

| Componente | Estado | Detalle |
| :--- | :---: | :--- |
| **Dominio & Reglas de Negocio** | ✅ Completo | Modelos de asistencia, turnos, políticas, incidencias y auditoría. |
| **Puertos (Contratos)** | ✅ Completo | Interfaces abstractas para todos los agregados del sistema. |
| **Casos de Uso (Aplicación)** | ✅ Completo | Sincronización, emparejamiento, cálculo diario y ajustes con auditoría. |
| **Adaptador Biométrico (pyzk)** | ✅ Completo | `ZkTcpReader` probado con manejo de timeouts y ciclo de vida de conexión. |
| **Adaptadores In-Memory** | ✅ Completo | Suite completa de repositorios en memoria para pruebas. |
| **Adaptadores SQL (SQLAlchemy)** | ✅ Completo | Modelos, mappers y repositorios relacionales para SQLite, Postgres, MySQL y SQL Server. |
| **Adaptador Base MongoDB** | 🔄 Fase 1 | Cliente de conexión base (`MongoClientWrapper`). Repositorios NoSQL programados. |
| **Pruebas Automatizadas** | ✅ 136/136 | 136 pruebas unitarias e integrales pasando con 100% de éxito. |
| **Análisis Estático y Tipado** | ✅ 0 errores | `ruff` (linter) y `mypy` (type-checker en 148 archivos) limpios. |
| **Herramienta CLI** | ✅ Completo | CLI unificada (`asistpy`) con CRUD completo para branch, department, employee, shift, schedule, device, más attendance, report y db. |
| **Capa Web / API REST** | ⏳ Planificado | En diseño de endpoints bajo FastAPI. |
| **Capa Desktop GUI** | ⏳ Planificado | Planeada con PySide6 / Flet con SQLite local. |
| **Capa Mobile (Android/iOS)** | ⏳ Planificado | Planeada para modo quiosco y supervisores de campo. |

---

## 📂 Estructura del Proyecto

```text
AsistPy/
├── .env.example                     # Plantilla de configuración de variables de entorno
├── .gitattributes                  # Estandarización de saltos de línea (LF) y tipos de archivo
├── .gitignore                      # Reglas de exclusión de Git (venv, cachés, bases de datos)
├── DOCS/                           # Manuales y documentación de usuario
│   └── CLI_MANUAL.md               # Manual completo de la CLI unificada asistpy
├── docker-compose.yml              # Servicios para desarrollo local (Postgres, MySQL, Mongo)
├── LICENSE                         # Licencia de código abierto MIT
├── migrations/                     # Directorio reservado para migraciones con Alembic
│   └── .gitkeep
├── poetry.lock                     # Versiones exactas y reproducibles de dependencias
├── pyproject.toml                  # Configuración de Poetry, dependencias, ruff y mypy
├── README.md                       # Documentación técnica principal del proyecto
├── scripts/
│   └── probe_device.py             # Script de diagnóstico para pruebas directas con el reloj
├── src/
│   └── attendance/
│       ├── adapters/               # Adaptadores externos (Hardware, SQL, Mongo, Memoria, CLI)
│       │   ├── cli/                # Adaptador Driving CLI (asistpy) con subcomandos y tablas
│       │   ├── memory/             # Repositorios en memoria
│       │   ├── persistence/        # Persistencia: factory, SQL (modelos/repos) y MongoDB
│       │   └── zk_tcp/             # Cliente de conexión TCP para relojes ZKTeco
│       ├── application/            # Casos de uso de la aplicación
│       │   ├── adjustment/         # Ajuste manual de marcaciones con auditoría
│       │   ├── attendance/         # Emparejamiento y evaluación diaria
│       │   ├── device/             # Sincronización incremental de registros
│       │   ├── incidence/          # Justificaciones e incidencias
│       │   └── schedule/           # Resolución y asignación de turnos
│       ├── domain/                 # Núcleo del dominio y reglas de negocio puras
│       │   ├── attendance/         # Entidades de asistencia, sesiones, estados
│       │   ├── audit/              # Entidades y registros de auditoría
│       │   ├── common/             # Rangos de tiempo, fechas y excepciones base
│       │   ├── device/             # Entidades de dispositivo biométrico y logs
│       │   ├── incidence/          # Incidencias y justificaciones
│       │   ├── organization/       # Empleados, sucursales, departamentos
│       │   ├── policy/             # Políticas de tolerancia y horas extras
│       │   └── schedule/           # Turnos, asignaciones, rotaciones y excepciones
│       ├── ports/                  # Puertos abstractos (interfaces)
│       └── cli.py                  # Atajo directo para python -m attendance.cli
└── tests/
    ├── integration/                # Pruebas de integración con factorías, BD SQL y comandos CLI
    └── unit/                       # Pruebas unitarias de dominio, casos de uso, formatters y parser CLI
```

---

## 🛠 Requisitos Previos

- **Python**: Versión `3.11` o superior (probado hasta Python 3.14).
- **Poetry**: Gestor de empaquetado y dependencias para Python (`>=1.8`).
- **Docker / Docker Compose** *(opcional)*: Para levantar bases de datos de desarrollo (PostgreSQL, MySQL, MongoDB).

---

## 💻 Instalación y Configuración

### 1. Clonar el Repositorio
```bash
git clone <URL_DEL_REPOSITORIO>
cd AsistPy
```

### 2. Configurar el Entorno Virtual e Instalar Dependencias
Instalación base (incluye driver nativo SQLite y adaptadores en memoria):
```bash
poetry install
```

Si requieres soporte para motores de base de datos específicos, instala los extras correspondientes:
```bash
# Para PostgreSQL:
poetry install -E postgres

# Para MySQL / MariaDB:
poetry install -E mysql

# Para Microsoft SQL Server:
poetry install -E sqlserver

# Para MongoDB:
poetry install -E mongo

# O instalar todos los drivers de persistencia simultáneamente:
poetry install -E all
```

*(En futuras fases se habilitarán los extras `poetry install -E web`, `poetry install -E cli` o `poetry install -E desktop` para los entornos respectivos).*

### 3. Configurar Variables de Entorno
Copia el archivo de ejemplo y edita según tu infraestructura:
```bash
cp .env.example .env
```

Parámetros principales en `.env`:
- `PERSISTENCE_BACKEND`: `sqlite` (predeterminado), `postgres`, `mysql`, `sqlserver`, `mongo` o `memory`.
- `DATABASE_URL`: Cadena de conexión a tu base de datos.
- `ZK_DEVICE_IP`, `ZK_DEVICE_PORT`, `ZK_TIMEOUT`: Datos de conexión al reloj biométrico.

---

## 🚀 Instrucciones de Ejecución y Despliegue

### 1. Servicios Auxiliares con Docker Compose
Si deseas probar contra PostgreSQL, MySQL o MongoDB localmente:
```bash
# Iniciar base de datos PostgreSQL
docker compose up -d postgres

# O iniciar todos los motores para pruebas cruzadas
docker compose up -d
```

### 2. Diagnóstico y Sondeo del Reloj Biométrico
Para verificar la conectividad con un reloj ZKTeco en la red:
```bash
poetry run python scripts/probe_device.py
```
> **Nota:** Puedes definir variables antes de ejecutar si difieren de las de `.env`:
> ```bash
> ZK_DEVICE_IP="192.168.1.200" ZK_DEVICE_PORT="4370" poetry run python scripts/probe_device.py
> ```

### 3. Herramienta CLI Unificada (`asistpy`)
AsistPy incluye una consola CLI completa para administrar el sistema, diagnosticar relojes, sincronizar marcaciones y generar reportes sin necesidad de interfaces gráficas ni servidores web:

```bash
# Diagnosticar estado y conectividad de la base de datos
asistpy db status

# Sondear conectividad física con un reloj ZKTeco en red
asistpy device probe --ip 192.168.0.233 --port 4370

# Sincronización incremental de todos los relojes activos del catálogo
asistpy device sync

# Evaluación de jornada de asistencia para todos los empleados activos
asistpy attendance evaluate --date 2026-09-02

# Exportar reporte consolidado de asistencia a formato CSV
asistpy report summary --start-date 2026-09-01 --end-date 2026-09-07 --format csv --output reportes/semana.csv
```

> 📘 Para consultar todos los subcomandos, ejemplos y recetas de automatización con `cron`, revisa el [Manual de la CLI (DOCS/CLI_MANUAL.md)](DOCS/CLI_MANUAL.md).

### 4. Inicialización Programática de Persistencia
Para inicializar el conjunto completo de repositorios desde código Python:
```python
from attendance.adapters.persistence.factory import PersistenceFactory

# Crear bundle según variables de entorno o parámetros explícitos
bundle = PersistenceFactory.create_bundle(
    backend="sqlite",
    connection_string="sqlite:///asistpy.db",
    init_tables=True,
)

# Acceso inmediato a todos los repositorios:
employee = bundle.employee_repo.get_by_id("emp-001")
print(employee)
```

---

## 🧪 Pruebas y Calidad

El proyecto mantiene un estándar riguroso de calidad de código y cobertura:

### Ejecución de Pruebas Unitarias e Integración
```bash
poetry run pytest -v
```
Resultado esperado: **136 tests pasando**.

### Análisis de Estilo y Linting (Ruff)
```bash
poetry run ruff check .
```

### Análisis Estático de Tipado (Mypy)
```bash
poetry run mypy src tests
```
Resultado esperado: **Success: no issues found in 148 source files**.

---

## 🗺 Pendientes y Roadmap

El núcleo del dominio, los casos de uso, la capa relacional y la CLI unificada están completamente operativos. Las siguientes fases comprenden:

### Fase 1: Capa de Servicio Web & API Centralizada
- [ ] **API REST / FastAPI**: Endpoints para consulta de asistencias, reportes, justificación de incidencias y administración de turnos.
- [ ] **Daemon / Worker de Sincronización en Segundo Plano**: Tarea periódica automatizada (cron/worker) para consultar relojes en segundo plano y registrar logs de forma desatendida.
- [ ] **Dockerización de Producción**: Imagen Docker ligera y configuración para orquestación en la nube.

### Fase 2: Herramienta de Línea de Comandos (CLI)
- [x] **CLI Unificada (`asistpy`) con CRUD Completo**:
  - `asistpy branch [add | show | list | edit | delete]`: Catálogo de sucursales con persistencia en BD.
  - `asistpy department [add | show | list | edit | delete]`: Catálogo de departamentos y áreas funcionales.
  - `asistpy employee [add | show | list | edit | delete]`: Catálogo de empleados y colaboradores.
  - `asistpy shift [add | show | list | edit | delete]`: Catálogo de turnos, tolerancias y jornadas nocturnas.
  - `asistpy schedule [assign | show | list | edit | close | delete]`: Asignaciones de horarios.
  - `asistpy device [add | show | list | edit | delete | probe | sync]`: Catálogo y sincronización de relojes biométricos.
  - `asistpy attendance [evaluate | list | adjust]`: Evaluación diaria y ajustes manuales con auditoría.
  - `asistpy report summary`: Generación y exportación de reportes a consola, CSV o JSON.
  - `asistpy db [init | status]`: Inicialización, creación de esquema y diagnóstico de bases de datos.
- [x] **Extra de Dependencias `[cli]`**: Empaquetado ligero para terminal y manual de uso exhaustivo en `DOCS/CLI_MANUAL.md`.

### Fase 3: Aplicación de Escritorio Multiplataforma (Windows, macOS, Linux)
- [ ] **Interfaz Gráfica de Escritorio**: Implementación de interfaz ligera (PySide6 / Flet) para casetas de control, estaciones de RRHH locales y administradores de sucursal.
- [ ] **Empaquetado Autocontenido**: Distribución en ejecutables independientes (.exe para Windows, .dmg para macOS, AppImage/deb para Linux) con soporte para base de datos SQLite integrada.

### Fase 4: Aplicación Móvil (Android & iOS)
- [ ] **Cliente Móvil para Supervisores**: Aplicación táctil optimizada para teléfonos y tablets Android / iOS.
- [ ] **Modo Quiosco Tablet**: Posibilidad de utilizar tablets como punto de asistencia alternativo o de consulta de saldo de horas y turnos para empleados.
- [ ] **Sincronización Local/Remota (Offline-First)**: Almacenamiento en SQLite local del dispositivo móvil con sincronización hacia el backend cuando haya conectividad disponible.

### Fase 5: Persistencia Avanzada y Mantenimiento
- [ ] **Suite Completa NoSQL para MongoDB**: Repositorios de asistencia y auditoría implementados para colecciones de Mongo.
- [ ] **Control de Migraciones con Alembic**: Scripts de versionado automático de esquemas de base de datos en `migrations/`.

---

## 👤 Autor y Licencia

- **Autor:** Alexis Barron (<alexis.barron.luna@gmail.com>)
- **Licencia:** Este proyecto se distribuye bajo los términos de la [Licencia MIT](LICENSE).
