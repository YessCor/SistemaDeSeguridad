# Arquitectura del Sistema de Seguridad Inteligente

## Visión General

El sistema está diseñado con una arquitectura de **tres capas** que separa las responsabilidades de manera clara:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ARQUITECTURA DEL SISTEMA                       │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────┐          ┌─────────────────┐          ┌─────────────┐
    │   SISTEMA      │          │    BACKEND      │          │    BASE     │
    │   LOCAL        │          │    (Vercel)     │          │    DE       │
    │   (Python)     │─────────▶│    (Node.js)    │─────────▶│    DATOS    │
    │                │   REST   │                 │   PG     │   (Neon)    │
    └─────────────────┘          └─────────────────┘          └─────────────┘

    ┌─────────────────┐          ┌─────────────────┐
    │ • Captura video │          │ • API REST      │
    │ • Detección     │          │ • Auth          │
    │ • Reconocimiento│          │ • Logs          │
    │ • Liveness      │          │ • Alertas       │
    └─────────────────┘          └─────────────────┘
```

---

## 1. Sistema Local (Python)

### 1.1 Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SISTEMA LOCAL (PYTHON)                             │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌───────────────────────┐
                              │      main.py          │
                              │   (Punto de entrada)  │
                              └───────────┬───────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CORE (Módulos principales)                        │
└─────────────────────────────────────────────────────────────────────────────┘

     ┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
     │   Camera    │────▶│FaceDetector  │────▶│FaceRecognizer   │
     │  (Webcam)  │     │ (dlib)       │     │ (Embeddings)    │
     └─────────────┘     └──────────────┘     └────────┬────────┘
           │                                               │
           │                                               ▼
           │                                    ┌─────────────────────┐
           │                                    │  LivenessDetector   │
           │                                    │  (EAR + Pose)       │
           │                                    └──────────┬──────────┘
           │                                               │
           └───────────────────────────────────────────────┘
                              │
                              ▼
                  ┌───────────────────────┐
                  │  AuthController       │
                  │  (Orquestador)        │
                  └───────────┬───────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           UTILS                                             │
└─────────────────────────────────────────────────────────────────────────────┘

                  ┌───────────────────────┐
                  │    ApiClient          │
                  │  (HTTP requests)      │
                  └───────────┬───────────┘
                              │
                              ▼  HTTPS
                  ┌───────────────────────┐
                  │    BACKEND (Vercel)   │
                  └───────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           CONFIG                                            │
└─────────────────────────────────────────────────────────────────────────────┘

                  ┌───────────────────────┐
                  │    Settings           │
                  │  (Environment vars)   │
                  └───────────────────────┘
```

### 1.2 Clases Principales

#### Camera (`core/camera.py`)
- **Responsabilidad**: Abstraer la captura de video de OpenCV
- **API**:
  - `__init__(index=0)`: Inicializa la cámara especificada
  - `stream()`: Generador que Yield frames BGR continuamente
  - `__enter__/__exit__`**: Context manager para limpieza automática

#### FaceDetector (`core/face_detector.py`)
- **Responsabilidad**: Detectar rostros y extraer embeddings faciales
- **API**:
  - `detect(frame_bgr) -> List[DetectedFace]`: Detecta todos los rostros
  - `detect_primary(frame_bgr) -> Optional[DetectedFace]`: Retorna el rostro más grande
- **Dependencias**: `face_recognition` (wrapper de dlib)

#### FaceRecognizer (`core/face_recognizer.py`)
- **Responsabilidad**: Comparar embeddings faciales
- **API**:
  - `load_known(known_embeddings)`: Cargar usuarios conocidos en memoria
  - `match(embedding) -> MatchResult`: Comparar embedding con la base

#### LivenessDetector (`core/liveness_detector.py`)
- **Responsabilidad**: Validar que el sujeto está vivo
- **Técnicas**:
  - **EAR (Eye Aspect Ratio)**: Detecta parpadeo midiendo la relación de aspecto del ojo
  - **Estimación de pose**: Detecta movimiento de cabeza (yaw)
- **API**:
  - `update(frame_bgr, session) -> LivenessSession`: Procesa un frame
  - Requiere `dlib.shape_predictor` (modelo de 68 landmarks)

#### AuthController (`core/auth_controller.py`)
- **Responsabilidad**: Orquestar todo el flujo de autenticación
- **Flujo**:
  1. Capturar frame de cámara
  2. Detectar rostro
  3. Actualizar sesión de liveness
  4. Si está vivo → comparar embedding
  5. Registrar log en backend
  6. Si hay muchos fallos → generar alerta
- **API**:
  - `load_users()`: Cargar usuarios del backend
  - `authenticate(frame_bgr) -> AuthStatus`: Procesar un frame

#### ApiClient (`utils/api_client.py`)
- **Responsabilidad**: Comunicarse con el backend REST
- **Características**:
  - Reintentos automáticos en errores de red
  - Timeout configurable
  - Headers de autenticación

---

## 2. Backend (Node.js/Vercel)

### 2.1 Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BACKEND (VERCEL)                                    │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────────────────────────────────────────────────────┐
    │                        HANDLER (API Routes)                          │
    │                                                                      │
    │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
    │  │ register.js │ │ login.js    │ │ logs.js     │ │ alertas.js  │   │
    │  │             │ │             │ │             │ │             │   │
    │  │ POST        │ │ POST        │ │ GET/POST    │ │ GET/POST    │   │
    │  │ /register   │ │ /login      │ │ /logs       │ │ /alertas    │   │
    │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘   │
    │                                                                      │
    │  ┌─────────────┐ ┌─────────────────────┐                            │
    │  │ usuarios.js │ │ usuarios-delete.js  │                            │
    │  │             │ │                     │                            │
    │  │ GET         │ │ DELETE              │                            │
    │  │ /usuarios   │ │ /usuarios/:id       │                            │
    │  └─────────────┘ └─────────────────────┘                            │
    └──────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
    ┌──────────────────────────────────────────────────────────────────────┐
    │                        MIDDLEWARE                                    │
    │                                                                      │
    │  ┌─────────────────────────────────────────────────────────────┐    │
    │  │                  validateApiKey.js                          │    │
    │  │  - Valida header X-API-Key                                  │    │
    │  │  - Comparación en tiempo constante                          │    │
    │  └─────────────────────────────────────────────────────────────┘    │
    └──────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
    ┌──────────────────────────────────────────────────────────────────────┐
    │                           LIB                                         │
    │                                                                      │
    │  ┌─────────────────────────────────────────────────────────────┐    │
    │  │                      db.js                                  │    │
    │  │  - Pool de conexiones PostgreSQL                            │    │
    │  │  - Queries parametrizadas                                  │    │
    │  │  - SSL habilitado                                          │    │
    └─────────────────────────────────────────────────────────────┘    │
    └──────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
    ┌──────────────────────────────────────────────────────────────────────┐
    │                      BASE DE DATOS (Neon)                            │
    │                                                                      │
    │   ┌─────────┐  ┌──────────┐  ┌──────┐  ┌─────────────┐  ┌────────┐  │
    │   │usuarios │  │biometria │  │logs  │  │intentos_    │  │alertas │  │
    │   │         │  │          │  │      │  │fallidos     │  │        │  │
    │   └─────────┘  └──────────┘  └──────┘  └─────────────┘  └────────┘  │
    └──────────────────────────────────────────────────────────────────────┘
```

### 2.2 Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/register` | POST | Registrar usuario con embedding facial |
| `/api/login` | POST | Registrar intento de acceso |
| `/api/logs` | GET | Consultar logs (paginado, filtrable) |
| `/api/logs` | POST | Crear nuevo log |
| `/api/usuarios` | GET | Listar usuarios con embeddings |
| `/api/usuarios/:id` | DELETE | Eliminar usuario y sus datos (GDPR) |
| `/api/alertas` | GET | Listar alertas |
| `/api/alertas` | POST | Crear alerta |
| `/api/alertas/:id` | PATCH | Actualizar alerta |
| `/api/alertas/:id` | DELETE | Eliminar alerta |

---

## 3. Base de Datos (PostgreSQL/Neon)

### 3.1 Modelo Entidad-Relación

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MODELO DE DATOS                                      │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌────────────────┐           ┌────────────────┐
    │    usuarios   │           │   biometria    │
    ├────────────────┤           ├────────────────┤
    │ id (PK)       │◀──────────│ usuario_id (FK)│
    │ nombre        │    1:N    │ encoding (JSONB)│
    │ email (UNIQUE)│           │ modelo         │
    │ activo        │           │ creado_en      │
    │ creado_en     │           └────────────────┘
    └────────────────┘                    │
                                           │
    ┌────────────────┐                    │
    │   logs         │                    │
    ├────────────────┤                    │
    │ id (PK)        │                    │
    │ usuario_id (FK)│───────────▶────────┘
    │ estado         │    0:N
    │ metodo         │
    │ detalle        │
    │ confianza      │
    │ fecha          │
    └────────────────┘

    ┌────────────────────┐     ┌────────────────┐
    │  intentos_fallidos │     │    alertas     │
    ├────────────────────┤     ├────────────────┤
    │ id (PK)            │     │ id (PK)        │
    │ usuario_id (FK)    │     │ tipo           │
    │ cantidad           │     │ descripcion   │
    │ ultima_vez         │     │ usuario_id (FK)│
    └────────────────────┘     │ resuelta       │
                               │ creada_en      │
                               └────────────────┘
```

### 3.2 Tablas

#### usuarios
| Columna | Tipo | Descripción |
|---------|------|-------------|
| id | SERIAL | Primary key |
| nombre | VARCHAR(120) | Nombre completo |
| email | VARCHAR(255) | Email único |
| activo | BOOLEAN | Si el usuario está activo |
| creado_en | TIMESTAMPTZ | Fecha de creación |

#### biometria
| Columna | Tipo | Descripción |
|---------|------|-------------|
| id | SERIAL | Primary key |
| usuario_id | INTEGER | FK a usuarios |
| encoding | JSONB | Embedding de 128 floats |
| modelo | VARCHAR(50) | Modelo usado |
| creado_en | TIMESTAMPTZ | Fecha de creación |

#### logs
| Columna | Tipo | Descripción |
|---------|------|-------------|
| id | SERIAL | Primary key |
| usuario_id | INTEGER | FK a usuarios (nullable) |
| estado | VARCHAR(20) | permitido/denegado/error |
| metodo | VARCHAR(30) | Método de autenticación |
| detalle | TEXT | Descripción del evento |
| confianza | NUMERIC(5,4) | Score de similitud |
| ip_origen | VARCHAR(45) | IP del solicitante |
| fecha | TIMESTAMPTZ | Fecha del evento |

#### intentos_fallidos
| Columna | Tipo | Descripción |
|---------|------|-------------|
| id | SERIAL | Primary key |
| usuario_id | INTEGER | FK a usuarios |
| cantidad | INTEGER | Intentos fallidos |
| ultima_vez | TIMESTAMPTZ | Último intento |

#### alertas
| Columna | Tipo | Descripción |
|---------|------|-------------|
| id | SERIAL | Primary key |
| tipo | VARCHAR(50) | Tipo de alerta |
| descripcion | TEXT | Descripción |
| usuario_id | INTEGER | FK a usuarios |
| resuelta | BOOLEAN | Si está resuelta |
| creada_en | TIMESTAMPTZ | Fecha de creación |

---

## 4. Flujo de Datos

### 4.1 Registro de Usuario

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      FLUJO: REGISTRO DE USUARIO                            │
└─────────────────────────────────────────────────────────────────────────────┘

  SISTEMA LOCAL                    BACKEND                         BD (NEON)
       │                             │                                 │
       │  1. Captura video           │                                 │
       │────────────────────────────>│                                 │
       │                             │                                 │
       │  2. Detecta rostro          │                                 │
       │  (face_recognition)         │                                 │
       │                             │                                 │
       │  3. Extrae embedding        │                                 │
       │  (128 floats)              │                                 │
       │                             │                                 │
       │  4. POST /api/register     │                                 │
       │  {nombre, email, encoding} │                                 │
       │────────────────────────────>│                                 │
       │                             │                                 │
       │                             │ 5. Valida API Key              │
       │                             │── ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ >│
       │                             │                                 │
       │                             │ 6. Valida entrada              │
       │                             │ (email, encoding length)       │
       │                             │                                 │
       │                             │ 7. BEGIN TRANSACTION           │
       │                             │─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ >│
       │                             │                                 │
       │                             │ 8. INSERT usuarios             │
       │                             │─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ >│
       │                             │< ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │
       │                             │  (RETURNING id)               │
       │                             │                                 │
       │                             │ 9. INSERT biometria            │
       │                             │─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ >│
       │                             │                                 │
       │                             │ 10. COMMIT                     │
       │                             │─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ >│
       │                             │                                 │
       │  11. {usuario_id, mensaje} │                                 │
       │<────────────────────────────│                                 │
       │                             │                                 │
       ▼                             ▼                                 ▼
```

### 4.2 Autenticación

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      FLUJO: AUTENTICACIÓN                                   │
└─────────────────────────────────────────────────────────────────────────────┘

  SISTEMA LOCAL                    BACKEND                         BD (NEON)
       │                             │                                 │
       │  1. GET /api/usuarios      │                                 │
       │  (carga embeddings)        │                                 │
       │────────────────────────────>│                                 │
       │                             │                                 │
       │  2. [usuarios con encoding]│                                 │
       │<────────────────────────────│                                 │
       │                             │                                 │
       │  3. Loop de autenticación   │                                 │
       │  (por cada frame)          │                                 │
       │                             │                                 │
       │  4. Detectar rostro         │                                 │
       │                             │                                 │
       │  5. Verificar liveness     │                                 │
       │  (parpadeo + cabeza)       │                                 │
       │                             │                                 │
       │  6. Si vivo:               │                                 │
       │     Comparar embedding     │                                 │
       │                             │                                 │
       │  7. POST /api/login        │                                 │
       │  {usuario_id, estado,      │                                 │
       │   confianza, metodo}       │                                 │
       │────────────────────────────>│                                 │
       │                             │                                 │
       │                             │ 8. Verificar bloqueo           │
       │                             │─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ >│
       │                             │                                 │
       │                             │ 9. INSERT logs                 │
       │                             │─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ >│
       │                             │                                 │
       │  10. {acceso, mensaje,     │                                 │
       │       intentos_fallidos}   │                                 │
       │<────────────────────────────│                                 │
       │                             │                                 │
       │  11. Si denegado + límite:  │                                 │
       │     POST /api/alertas      │                                 │
       │────────────────────────────>│                                 │
       │                             │                                 │
       │                             │ 12. INSERT alertas             │
       │                             │─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ >│
       │                             │                                 │
       ▼                             ▼                                 ▼
```

---

## 5. Seguridad

### 5.1 Capas de Seguridad

| Capa | Mecanismo | Descripción |
|------|-----------|-------------|
| **Transporte** | SSL/TLS | Conexión obligatoria a BD |
| **Autenticación** | API Key | Header `X-API-Key` |
| **Anti-Timing** | `timingSafeEqual` | Comparación en tiempo constante |
| **Anti-Spoofing** | Liveness Detection | EAR + Pose de cabeza |
| **Rate Limiting** | Intentos fallidos | Bloqueo temporal después de 3 fallos |
| **SQL** | Consultas parametrizadas | Sin inyección SQL |
| **Datos** | Variables de entorno | Sin credenciales hardcodeadas |

### 5.2 Variables de Entorno

**Backend (.env):**
- `DATABASE_URL`: URL de Neon
- `API_KEY`: Clave de API
- `MAX_FAILED_ATTEMPTS`: Intentos antes de bloquear
- `LOCKOUT_MINUTES`: Minutos de bloqueo

**Local (.env):**
- `BACKEND_URL`: URL del backend
- `API_KEY`: Clave de API
- `FACE_TOLERANCE`: Tolerancia de matching (0.0-1.0)
- `BLINK_THRESHOLD`: Ratio EAR para parpadeo
- `HEAD_ANGLE_THRESHOLD`: Grados de movimiento de cabeza

---

## 6. Despliegue

### 6.1 Infraestructura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         INFRAESTRUCTURA DE DESPLIEGUE                       │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────────────────────────────────────────────────────┐
    │                          INTERNET                                     │
    └──────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
    ┌──────────────────────────────────────────────────────────────────────┐
    │                    CLOUDFLARE (CDN + WAF)                           │
    │                 (Opcional: DDoS protection)                          │
    └──────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
    ┌──────────────────────────────────────────────────────────────────────┐
    │                           VERCEL                                    │
    │                                                                      │
    │  ┌────────────────────────────────────────────────────────────────┐ │
    │  │                    SERVERLESS FUNCTIONS                        │ │
    │  │                                                                 │ │
    │  │   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐              │ │
    │  │   │register │ │ login   │ │  logs   │ │ alertas │  ...         │ │
    │  │   └─────────┘ └─────────┘ └─────────┘ └─────────┘              │ │
    │  │                                                                 │ │
    │  │   ┌─────────────────────────────────────────────────────────┐ │ │
    │  │   │            MIDDLEWARE (API Key)                         │ │ │
    │  │   └─────────────────────────────────────────────────────────┘ │ │
    │  │                                                                 │ │
    │  └────────────────────────────────────────────────────────────────┘ │
    │                              │                                        │
    └──────────────────────────────┼────────────────────────────────────────┘
                                   │
                                   ▼
    ┌──────────────────────────────────────────────────────────────────────┐
    │                         NEON (PostgreSQL)                            │
    │                                                                      │
    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                   │
    │  │   Storage  │  │   Compute   │  │   Branching │                   │
    │  │  ( SSD )   │  │  ( Serverless)│  │  ( Dev/Prod)│                   │
    │  └─────────────┘  └─────────────┘  └─────────────┘                   │
    │                                                                      │
    └──────────────────────────────────────────────────────────────────────┘


    ┌──────────────────────────────────────────────────────────────────────┐
    │                    SISTEMA LOCAL (on-premise)                        │
    │                                                                      │
    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                   │
    │  │   Laptop/PC │  │   Webcam   │  │   Python    │                   │
    │  │  (usuario)  │  │  (USB)     │  │  (proceso)  │                   │
    │  └─────────────┘  └─────────────┘  └─────────────┘                   │
    └──────────────────────────────────────────────────────────────────────┘
```

### 6.2 Escalabilidad

| Componente | Estrategia |
|------------|------------|
| **Backend** | Serverless en Vercel → auto-escalamiento |
| **BD** | Neon serverless → escala automática |
| **Sistema local** | Una instancia por punto de acceso |
| **API** | Cache con Redis (futuro) |

---

## 7. Mejoras Futuras

- Dashboard web (Next.js/React)
- Notificaciones en tiempo real (WebSockets)
- Reconocimiento con InsightFace (ArcFace)
- Anti-spoofing con profundidad (cámaras IR)
- Rate limiting por IP
- Cifrado de embeddings (pgcrypto)
- Autenticación de admins (Auth0/Keycloak)
- Contenedores Docker
