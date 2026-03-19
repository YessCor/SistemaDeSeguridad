# Sistema de Seguridad Inteligente - Dockerfile
# Imagen para ejecutar el sistema local en un contenedor Docker

# ============================================================
# IMAGEN BASE
# ============================================================
FROM python:3.10-slim

# ============================================================
# METADATA
# ============================================================
LABEL maintainer="Sistema de Seguridad"
LABEL description="Sistema de reconocimiento facial con liveness detection"

# ============================================================
# VARIABLES DE ENTORNO
# ============================================================
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# ============================================================
# INSTALACIÓN DE DEPENDENCIAS DEL SISTEMA
# ============================================================
# Actualizar paquetes e instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Compiladores y herramientas de construcción
    build-essential \
    cmake \
    wget \
    # Bibliotecas de OpenCV
    libgl1-mesa-glx \
    libglib2.0-0 \
    # Bibliotecas de audio (opcional)
    libsndfile1 \
    # Git para clonar repositorios
    git \
    # Utilidades
    curl \
    vim \
    # Fuentes para OpenCV
    libfontconfig1 \
    libfreetype6 \
    && rm -rf /var/lib/apt/lists/*

# ============================================================
# DIRECTORIO DE TRABAJO
# ============================================================
WORKDIR /app

# ============================================================
# COPIAR ARCHIVOS DE REQUISITOS
# ============================================================
COPY requirements.txt .

# ============================================================
# INSTALAR DEPENDENCIAS DE PYTHON
# ============================================================
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ============================================================
# DESCARGA DE MODELOS DE DLIB
# ============================================================
# Los modelos de dlib se descargan automaticamente con face_recognition
# Pero podemos pre-descargarlos para uso offline
RUN mkdir -p /app/models && \
    wget -q -O /app/models/shape_predictor_68_face_landmarks.dat.bz2 \
    http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2 && \
    bzip2 -d /app/models/shape_predictor_68_face_landmarks.dat.bz2

# ============================================================
# COPIAR CÓDIGO DE LA APLICACIÓN
# ============================================================
COPY . .

# ============================================================
# CREAR DIRECTORIO DE LOGS
# ============================================================
RUN mkdir -p /app/logs

# ============================================================
# CONFIGURAR VARIABLES DE ENTORNO DESDE ARGUMENTOS
# ============================================================
ARG BACKEND_URL=http://localhost:3000
ARG API_KEY=dummy_api_key
ARG FACE_TOLERANCE=0.50
ARG CAMERA_INDEX=0

ENV BACKEND_URL=$BACKEND_URL
ENV API_KEY=$API_KEY
ENV FACE_TOLERANCE=$FACE_TOLERANCE
ENV CAMERA_INDEX=$CAMERA_INDEX
ENV LOG_LEVEL=INFO

# ============================================================
# EXPONER PUERTOS
# ============================================================
# No hay puertos expuestos ya que es una aplicacion de consola
# Pero se puede exponer para debugging
EXPOSE 8080

# ============================================================
# VOLUMENES
# ============================================================
# Directorio de logs persistente
VOLUME ["/app/logs"]

# ============================================================
# CONFIGURACIÓN DE USUARIO NO-ROOT
# ============================================================
# Crear usuario no-root para seguridad
RUN useradd -m -s /bin/bash appuser && \
    chown -R appuser:appuser /app

USER appuser

# ============================================================
# PUNTO DE ENTRADA
# ============================================================
# Por defecto ejecuta el modo de autenticación
ENTRYPOINT ["python", "main.py"]

# Argumentos por defecto
CMD ["--mode", "auth"]
