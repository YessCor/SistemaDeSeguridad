# local-system/config/settings.py
"""
Configuración centralizada del sistema local.
Todas las credenciales se leen desde variables de entorno.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── API Backend ───────────────────────────────────────────────
BACKEND_URL: str  = os.getenv("BACKEND_URL", "http://localhost:3000")
API_KEY: str      = os.getenv("API_KEY", "")           # Nunca hardcodear

# ── Reconocimiento facial ─────────────────────────────────────
FACE_TOLERANCE: float = float(os.getenv("FACE_TOLERANCE", "0.50"))   # 0.0 = exacto, 1.0 = muy permisivo
FACE_MODEL: str        = os.getenv("FACE_MODEL", "large")             # 'small' (rápido) | 'large' (preciso)

# ── Liveness detection ────────────────────────────────────────
BLINK_THRESHOLD: float   = float(os.getenv("BLINK_THRESHOLD", "0.25"))  # EAR ratio
BLINKS_REQUIRED: int     = int(os.getenv("BLINKS_REQUIRED", "2"))
HEAD_ANGLE_THRESHOLD: float = float(os.getenv("HEAD_ANGLE_THRESHOLD", "15.0"))  # grados

# ── Seguridad ────────────────────────────────────────────────
MAX_FAILED_ATTEMPTS: int = int(os.getenv("MAX_FAILED_ATTEMPTS", "3"))
LOCKOUT_MINUTES: int     = int(os.getenv("LOCKOUT_MINUTES", "5"))

# ── Cámara ────────────────────────────────────────────────────
CAMERA_INDEX: int    = int(os.getenv("CAMERA_INDEX", "0"))
FRAME_WIDTH: int     = int(os.getenv("FRAME_WIDTH", "640"))
FRAME_HEIGHT: int    = int(os.getenv("FRAME_HEIGHT", "480"))
TARGET_FPS: int      = int(os.getenv("TARGET_FPS", "30"))

# ── Logging ───────────────────────────────────────────────────
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE: str  = os.getenv("LOG_FILE", "logs/system.log")
