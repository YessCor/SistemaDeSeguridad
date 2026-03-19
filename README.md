# Sistema de Seguridad Inteligente para Monitoreo y Control de Accesos

Sistema de software capaz de monitorear, detectar y prevenir accesos no autorizados mediante reconocimiento facial, validación de vida (liveness detection) y control de accesos, garantizando la seguridad de los usuarios y la información, con registro de eventos y alertas en tiempo real.

---

## 🚀 Características Principales

- **Reconocimiento Facial**: Extrae embeddings de 128 dimensiones usando dlib/face_recognition
- **Detección de Vida (Liveness)**: Valida parpadeo y movimiento de cabeza para prevenir suplantación con fotos
- **API REST Serverless**: Backend en Vercel con PostgreSQL serverless (Neon)
- **Logs de Acceso**: Registro completo de todos los intentos de acceso
- **Alertas Automáticas**: Notificaciones ante múltiples intentos fallidos
- **Seguridad**: API Key con comparación en tiempo constante, variables de entorno, SSL

---

## 📁 Estructura del Proyecto

```
SistemaDeSeguridad/
│
├── local-system/                    # Sistema local (Python)
│   ├── core/                        # Módulos principales
│   │   ├── camera.py               # Captura de video desde webcam
│   │   ├── face_detector.py        # Detección de rostros con dlib
│   │   ├── face_recognizer.py      # Comparación de embeddings faciales
│   │   ├── liveness_detector.py    # Detección de vida (EAR + pose)
│   │   └── auth_controller.py      # Orquestador del flujo de autenticación
│   │
│   ├── models/                     # Modelos de datos
│   │   └── user.py
│   │
│   ├── utils/                      # Utilidades
│   │   ├── api_client.py           # Cliente HTTP hacia backend
│   │   └── logger.py              # Logging estructurado
│   │
│   ├── config/                     # Configuración
│   │   └── settings.py             # Variables de entorno
│   │
│   ├── tests/                      # Tests unitarios
│   │   ├── test_face_detector.py
│   │   └── test_liveness.py
│   │
│   ├── main.py                     # Punto de entrada CLI
│   ├── requirements.txt            # Dependencias Python
│   └── .env.example               # Ejemplo de configuración
│
├── backend/                        # API en Vercel (Node.js)
│   ├── api/                        # Endpoints
│   │   ├── register.js            # POST /api/register
│   │   ├── login.js               # POST /api/login
│   │   ├── logs.js                # GET/POST /api/logs
│   │   ├── alertas.js             # GET/POST/PATCH/DELETE /api/alertas
│   │   ├── usuarios.js           # GET /api/usuarios
│   │   └── usuarios-delete.js     # DELETE /api/usuarios/:id
│   │
│   ├── lib/                        # Utilidades del backend
│   │   └── db.js                  # Conexión a PostgreSQL (Neon)
│   │
│   ├── middleware/                 # Middleware
│   │   └── validateApiKey.js      # Validación de API Key
│   │
│   ├── vercel.json                # Configuración de Vercel
│   ├── package.json               # Dependencias Node.js
│   └── .env.example              # Ejemplo de configuración
│
└── docs/                           # Documentación
    ├── schema.sql                 # Esquema de base de datos
    ├── api-reference.md           # Referencia de API
    ├── security-and-roadmap.md    # Seguridad y mejoras
    └── setup-guide.md             # Guía de instalación
```

---

## 🔄 Flujo del Sistema

### Flujo de Autenticación

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        SISTEMA DE AUTENTICACIÓN                         │
└─────────────────────────────────────────────────────────────────────────┘

  ┌──────────┐    ┌──────────────┐    ┌─────────────┐    ┌────────────┐
  │  CÁMARA  │───▶│ DETECCIÓN DE  │───▶│  EXTRACCIÓN │───▶│ COMPARACIÓN│
  │ (Webcam) │    │    ROSTRO     │    │  EMBEDDING  │    │   FACIAL   │
  └──────────┘    └──────────────┘    └─────────────┘    └────────────┘
                                                                    │
  ┌──────────────────────────────────────────────────────────────────┘
  │
  ▼
  ┌──────────────────┐    ┌────────────────┐    ┌───────────────────┐
  │  ¿Rostro         │    │  ¿Embedding    │    │  REGISTRAR LOG    │
  │  detectado?      │───▶│  coincide?      │───▶│  EN BACKEND       │
  └──────────────────┘    └────────────────┘    └───────────────────┘
        │                         │                        │
       NO                        NO                       ✓
        │                         │                        │
        ▼                         ▼                        ▼
  ┌──────────────┐    ┌────────────────┐    ┌─────────────────────┐
  │ RETORNAR      │    │ RETORNAR        │    │ GENERAR ALERTA SI   │
  │ "SIN ROSTRO" │    │ "DENEGADO"       │    │ INTENTOS FALLIDOS   │
  └──────────────┘    └────────────────┘    └─────────────────────┘

  ┌──────────────────────────────────────────────────────────────────┐
  │                      DETECCIÓN DE VIDA (LIVENESS)                 │
  └──────────────────────────────────────────────────────────────────┘
  │                                                                    │
  ▼                                                                    │
  ┌─────────────────┐    ┌────────────────┐    ┌─────────────────┐   │
  │  Detectar       │    │  ¿Parpadeo      │    │  ¿Movimiento    │   │
  │  landmarks      │───▶│  detectado?     │───▶│  de cabeza?     │   │
  │  (68 puntos)    │    │  (≥2 blinks)    │    │  (yaw ≥15°)     │   │
  └─────────────────┘    └────────────────┘    └─────────────────┘   │
        │                       │                       │               │
       NO                      NO                      NO              │
        │                       │                       │               │
        ▼                       ▼                       ▼               │
  ┌────────────────┐    ┌──────────────┐    ┌────────────────────┐      │
  │ RETORNAR       │    │ REINICIAR    │    │ SESIÓN VIVA =     │      │
  │ "LIVENESS FAIL"│    │ CONTADOR     │    │ VERDADERO ✓       │
  └────────────────┘    └──────────────┘    └────────────────────┘      │
```

### Flujo de Registro de Usuario

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     REGISTRO DE NUEVO USUARIO                          │
└─────────────────────────────────────────────────────────────────────────┘

  ┌────────────┐    ┌─────────────┐    ┌──────────────┐    ┌─────────┐
  │ CAPTURAR   │───▶│ DETECTAR    │───▶│ EXTRAER      │───▶│ ENVIAR  │
  │ VIDEO      │    │ ROSTRO      │    │ EMBEDDING    │    │ A API   │
  └────────────┘    └─────────────┘    └──────────────┘    └─────────┘
                                                                    │
                                                                    ▼
                                                            ┌─────────────┐
                                                            │  BACKEND    │
                                                            │  (Vercel)   │
                                                            └─────────────┘
                                                                    │
  ┌───────────────────────────────────────────────────────────────────┘
  │
  ▼
  ┌──────────────────┐    ┌──────────────────┐    ┌─────────────────┐
  │  INSERTAR en     │    │  INSERTAR en    │    │  RESPONDER      │
  │  tabla USUARIOS  │───▶│  tabla BIOMETRÍA│───▶│  "201 Created"  │
  └──────────────────┘    └──────────────────┘    └─────────────────┘
```

---

## 🏗️ Arquitectura por Módulos

### Sistema Local (Python)

| Módulo | Responsabilidad |
|--------|-----------------|
| [`camera.py`](local-system/core/camera.py) | Abstrae la captura de video de OpenCV |
| [`face_detector.py`](local-system/core/face_detector.py) | Detecta rostros y extrae embeddings |
| [`face_recognizer.py`](local-system/core/face_recognizer.py) | Compara embeddings con la base de usuarios |
| [`liveness_detector.py`](local-system/core/liveness_detector.py) | Valida vida mediante EAR y pose de cabeza |
| [`auth_controller.py`](local-system/core/auth_controller.py) | Orquesta todo el flujo de autenticación |
| [`api_client.py`](local-system/utils/api_client.py) | Cliente HTTP hacia el backend |

### Backend (Node.js/Vercel)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| [`/api/register`](backend/api/register.js) | POST | Registrar usuario con biometría |
| [`/api/login`](backend/api/login.js) | POST | Registrar intento de acceso |
| [`/api/logs`](backend/api/logs.js) | GET/POST | Consultar/crear logs |
| [`/api/usuarios`](backend/api/usuarios.js) | GET | Listar usuarios con embeddings |
| [`/api/alertas`](backend/api/alertas.js) | GET/POST/PATCH/DELETE | Gestionar alertas |
| [`/api/usuarios/:id`](backend/api/usuarios-delete.js) | DELETE | Eliminar usuario (GDPR) |

---

## ⚙️ Requisitos

### Sistema Local (Python)

- **Python 3.10+**
- **CMake** (para compilar dlib)
- **Visual Studio Build Tools** (Windows)
- Webcam conectada

### Backend (Node.js)

- **Node.js 18+**
- **npm** o **yarn**
- Cuenta en [Vercel](https://vercel.com)
- Cuenta en [Neon](https://neon.tech) (PostgreSQL serverless)

---

## 🔧 Instalación

### 1. Clonar el repositorio

```bash
git clone <repo-url>
cd SistemaDeSeguridad
```

### 2. Configurar Base de Datos (Neon)

1. Crear cuenta en [neon.tech](https://neon.tech)
2. Crear nuevo proyecto
3. Copiar la URL de conexión (DATABASE_URL)
4. Ejecutar el esquema:

```bash
# Desde la raíz del proyecto
psql <DATABASE_URL> -f docs/schema.sql
```

O desde el dashboard de Neon, ejecutar el contenido de [`docs/schema.sql`](docs/schema.sql).

### 3. Configurar Backend (Vercel)

```bash
# Ir al directorio del backend
cd backend

# Instalar dependencias
npm install

# Iniciar sesión en Vercel (si no está autenticado)
vercel login

# Desplegar (seguir instrucciones)
vercel deploy --prod
```

**Variables de entorno requeridas en Vercel:**

| Variable | Descripción |
|----------|-------------|
| `DATABASE_URL` | URL de conexión de Neon (postgresql://...) |
| `API_KEY` | Clave de API segura (generar con `openssl rand -hex 32`) |
| `MAX_FAILED_ATTEMPTS` | Intentos fallidos antes de bloquear (default: 3) |
| `LOCKOUT_MINUTES` | Minutos de bloqueo (default: 5) |

### 4. Configurar Sistema Local

```bash
# Ir al directorio del sistema local
cd local-system

# Crear entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# O en Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Copiar archivo de ejemplo
cp .env.example .env

# Editar .env con tus configuraciones
```

**Variables de entorno en `.env`:**

```env
# URL del backend desplegado
BACKEND_URL=https://tu-proyecto.vercel.app

# API Key (misma que en el backend)
API_KEY=tu_api_key_aqui

# Configuración de reconocimiento facial
FACE_TOLERANCE=0.50
FACE_MODEL=large

# Configuración de liveness
BLINK_THRESHOLD=0.25
BLINKS_REQUIRED=2
HEAD_ANGLE_THRESHOLD=15.0

# Seguridad
MAX_FAILED_ATTEMPTS=3
LOCKOUT_MINUTES=5

# Cámara
CAMERA_INDEX=0
FRAME_WIDTH=640
FRAME_HEIGHT=480
TARGET_FPS=30

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/system.log
```

---

## ▶️ Uso

### Modo Autenticación (por defecto)

```bash
python main.py
```

Esto iniciarán el loop de autenticación:
- Detecta rostros en tiempo real
- Solicita parpadeo y movimiento de cabeza
- Compara con usuarios registrados
- Muestra resultado en pantalla

**Controles:**
- `ESPACIO`: Capturar (en modo registro)
- `q`: Salir

### Modo Registro de Usuario

```bash
python main.py --mode register --nombre "Juan Pérez" --email "juan@ejemplo.com"
```

El sistema:
- Activará la cámara
- Solicitará mirar directamente y presionar ESPACIO
- Capturará el embedding facial
- Lo enviará al backend para registro

---

## 🧪 Tests

```bash
cd local-system

# Ejecutar todos los tests
pytest tests/ -v

# Ejecutar test específico
pytest tests/test_face_detector.py -v
```

---

## 📚 Documentación Adicional

- [Referencia de API](docs/api-reference.md) - Endpoints detallados
- [Esquema de Base de Datos](docs/schema.sql) - Modelo de datos
- [Seguridad y Mejoras](docs/security-and-roadmap.md) - Buenas prácticas y roadmap
- [Guía de Instalación](docs/setup-guide.md) - Guía detallada

---

## 🔒 Seguridad

- **API Key**: Autenticación mediante header `X-API-Key`
- **Comparación en tiempo constante**: Previene ataques de timing
- **Consultas parametrizadas**: Previene inyección SQL
- **SSL/TLS**: Conexión obligatoria a la base de datos
- **Variables de entorno**: Nunca hardcodear credenciales
- **Liveness detection**: Previene suplantación con fotos/videos

---

## 📋 Licencia

MIT License - Ver archivo LICENSE para más detalles.
