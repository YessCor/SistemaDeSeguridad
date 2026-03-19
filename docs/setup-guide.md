# Guía de Instalación y Configuración

## Requisitos previos

- Python 3.10+ con pip
- Node.js 18+ con npm
- Cuenta en [Neon](https://neon.tech) (gratuita)
- Cuenta en [Vercel](https://vercel.com) (gratuita)
- Webcam conectada al equipo local
- CMake instalado (requerido por dlib)

---

## Paso 1 — Base de datos (Neon)

1. Crear proyecto en https://console.neon.tech
2. Copiar la `Connection string` (formato: `postgresql://...`)
3. Abrir el SQL Editor de Neon y ejecutar el contenido de `docs/schema.sql`
4. Verificar que las 5 tablas existen en la pestaña Tables

---

## Paso 2 — Backend (Vercel)

```bash
cd backend
npm install
cp .env.example .env
# Editar .env con tu DATABASE_URL y API_KEY generada
```

Generar API Key segura:
```bash
openssl rand -hex 32
```

Desplegar en Vercel:
```bash
npx vercel login
npx vercel deploy --prod
```

Configurar variables en el Dashboard de Vercel:
- `DATABASE_URL` → tu connection string de Neon
- `API_KEY` → la clave generada con openssl
- `MAX_FAILED_ATTEMPTS` → 3
- `LOCKOUT_MINUTES` → 5

Probar que el backend responde:
```bash
curl -H "X-API-Key: TU_API_KEY" https://tu-proyecto.vercel.app/api/usuarios
```

---

## Paso 3 — Sistema local (Python)

### Instalación de dependencias del sistema (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install -y cmake build-essential libopenblas-dev liblapack-dev
```

### Instalación de dependencias del sistema (macOS)
```bash
brew install cmake
```

### Descarga del modelo de landmarks de dlib
```bash
cd local-system
mkdir -p models
wget http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2
bzip2 -d shape_predictor_68_face_landmarks.dat.bz2
mv shape_predictor_68_face_landmarks.dat models/
```

### Entorno virtual y dependencias Python
```bash
cd local-system
python -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

### Configuración
```bash
cp .env.example .env
# Editar .env:
#   BACKEND_URL=https://tu-proyecto.vercel.app
#   API_KEY=la_misma_clave_del_backend
mkdir -p logs
```

---

## Paso 4 — Registrar primer usuario

```bash
cd local-system
source venv/bin/activate
python main.py --mode register --nombre "Ana García" --email "ana@empresa.com"
```

Cuando la ventana de cámara abra: mira directamente y presiona **ESPACIO**.

---

## Paso 5 — Iniciar autenticación

```bash
python main.py --mode auth
```

El sistema pedirá:
1. Que parpadees 2 veces
2. Que muevas la cabeza lateralmente 15°

Si ambas condiciones se cumplen y el rostro coincide, el acceso será concedido.

Presiona **Q** para salir.

---

## Variables de entorno — referencia completa

| Variable | Descripción | Default |
|----------|-------------|---------|
| `BACKEND_URL` | URL del backend Vercel | — |
| `API_KEY` | Clave de autenticación | — |
| `FACE_TOLERANCE` | Distancia máxima para match | `0.50` |
| `FACE_MODEL` | `small` (rápido) o `large` (preciso) | `large` |
| `BLINK_THRESHOLD` | EAR ratio para detectar parpadeo | `0.25` |
| `BLINKS_REQUIRED` | Parpadeos requeridos | `2` |
| `HEAD_ANGLE_THRESHOLD` | Grados de rotación requeridos | `15.0` |
| `MAX_FAILED_ATTEMPTS` | Intentos antes de bloqueo | `3` |
| `LOCKOUT_MINUTES` | Minutos de bloqueo | `5` |
| `CAMERA_INDEX` | Índice de cámara OpenCV | `0` |

---

## Solución de problemas frecuentes

**dlib no instala en Windows:**
Usar el wheel precompilado: `pip install dlib-bin`

**No detecta rostro:**
Asegúrate de tener buena iluminación frontal y el rostro centrado.
Prueba reducir `FACE_TOLERANCE` a `0.60` para mayor permisividad.

**Error de conexión al backend:**
Verifica que `BACKEND_URL` no tenga barra final y que la `API_KEY` coincida exactamente en ambos lados.

**Pool de conexiones agotado en Neon:**
El plan gratuito de Neon permite 100 conexiones. El backend usa máximo 5 por instancia serverless.
