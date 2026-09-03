# ==============================================================================
# Dockerfile Multi-stage para Producción - AsistPy
# Proporciona una imagen ligera, segura y optimizada para el demonio/worker 24/7
# ==============================================================================

# ------------------------------------------------------------------------------
# Etapa 1: Builder (Construcción de dependencias y ruedas de Python)
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Instalar dependencias del sistema necesarias para compilar paquetes si aplica
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Crear entorno virtual dedicado en /opt/venv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Actualizar pip y herramientas de empaquetado
RUN pip install --upgrade pip setuptools wheel "poetry-core>=2.0.0,<3.0.0"

# Copiar definiciones del proyecto para pre-instalar dependencias
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Instalar AsistPy con soporte para bases de datos principales (PostgreSQL, MySQL, SQLite)
RUN pip install ".[postgres,mysql,sqlite]"

# ------------------------------------------------------------------------------
# Etapa 2: Runtime (Imagen final de producción sin herramientas de compilación)
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PERSISTENCE_BACKEND=sqlite \
    SYNC_INTERVAL_SECONDS=300 \
    NIGHTLY_PROCESSING_TIME=23:59 \
    ZK_TIMEOUT=60 \
    SYNC_STOP_ON_ERROR=false

# Instalar librerías de tiempo de ejecución mínimas necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario y grupo sin privilegios por seguridad
RUN groupadd -g 1000 asistpy && \
    useradd -u 1000 -g asistpy -m -s /bin/bash asistpy

WORKDIR /app

# Copiar entorno virtual con librerías desde la etapa builder
COPY --from=builder /opt/venv /opt/venv

# Copiar código fuente del proyecto
COPY --chown=asistpy:asistpy pyproject.toml README.md ./
COPY --chown=asistpy:asistpy src/ ./src/

# Instalar el paquete en modo production
RUN pip install --no-deps .

# Crear directorio para base de datos SQLite / almacenamiento local de datos
RUN mkdir -p /app/data && chown -R asistpy:asistpy /app/data

# Cambiar al usuario no privilegiado
USER asistpy

# Manejo de señales: SIGTERM permite al worker realizar graceful shutdown y desconectar los relojes
STOPSIGNAL SIGTERM

# Punto de entrada predeterminado
ENTRYPOINT ["asistpy"]

# Comando por defecto: ejecutar el demonio de asistencia
CMD ["worker"]
