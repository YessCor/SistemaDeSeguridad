# local-system/core/auth_controller.py
"""
Orquestador del flujo de autenticación completo.

Secuencia:
  1. Capturar frame
  2. Detectar rostro
  3. Validar liveness (parpadeo + cabeza)
  4. Extraer embedding
  5. Comparar con knowns (cargados desde backend)
  6. Registrar log en backend
  7. Disparar alerta si hay intentos fallidos excesivos
"""

import logging
from enum import Enum, auto

import cv2

from config.settings import MAX_FAILED_ATTEMPTS
from core.camera import Camera
from core.face_detector import FaceDetector
from core.face_recognizer import FaceRecognizer, MatchResult
from core.liveness_detector import LivenessDetector, LivenessSession
from utils.api_client import ApiClient

logger = logging.getLogger(__name__)


class AuthStatus(Enum):
    NO_FACE       = auto()   # No se detectó rostro
    LIVENESS_FAIL = auto()   # No pasó detección de vida
    NO_MATCH      = auto()   # No coincide con ningún usuario
    GRANTED       = auto()   # Acceso concedido


class AuthController:
    """
    Coordina todos los módulos para ejecutar el flujo de autenticación.
    
    Ejemplo:
        controller = AuthController()
        controller.load_users()   # Carga encodings desde backend
        
        with Camera() as cam:
            for frame in cam.stream():
                result = controller.authenticate(frame)
                if result == AuthStatus.GRANTED:
                    print("Bienvenido")
                    break
    """

    def __init__(self) -> None:
        self._face_detector   = FaceDetector()
        self._recognizer      = FaceRecognizer()
        self._liveness        = LivenessDetector()
        self._api             = ApiClient()
        self._liveness_session = LivenessSession()
        self._failed_counts: dict[int, int] = {}

    # ── Inicialización ────────────────────────────────────────

    def load_users(self) -> None:
        """Descarga embeddings del backend y los carga en memoria."""
        users = self._api.get_usuarios()
        known = {}
        for u in users:
            if u.get("encoding"):
                known[u["id"]] = u["encoding"]
        self._recognizer.load_known(known)
        logger.info("Usuarios cargados: %d", len(known))

    def reset_liveness(self) -> None:
        """Reinicia sesión de liveness para un nuevo intento."""
        self._liveness_session.reset()

    # ── Autenticación ─────────────────────────────────────────

    def authenticate(self, frame_bgr) -> AuthStatus:
        """
        Procesa un frame y devuelve el estado de autenticación.
        
        Este método se llama frame a frame; el estado de liveness
        se acumula entre llamadas hasta completar los requisitos.
        """
        # ── Paso 1: detectar rostro ───────────────────────────
        face = self._face_detector.detect_primary(frame_bgr)
        if face is None:
            return AuthStatus.NO_FACE

        # ── Paso 2: actualizar sesión de liveness ─────────────
        self._liveness.update(frame_bgr, self._liveness_session)
        if not self._liveness_session.is_live:
            return AuthStatus.LIVENESS_FAIL

        # ── Paso 3: reconocimiento facial ─────────────────────
        result: MatchResult = self._recognizer.match(face.embedding)

        if result.matched:
            self._on_success(result)
            return AuthStatus.GRANTED
        else:
            self._on_failure(result)
            return AuthStatus.NO_MATCH

    # ── Registro ──────────────────────────────────────────────

    def _on_success(self, result: MatchResult) -> None:
        logger.info("Acceso CONCEDIDO → user_id=%s (confianza=%.2f%%)", result.user_id, result.confidence * 100)
        self._failed_counts.pop(result.user_id, None)
        self._api.post_log(
            usuario_id=result.user_id,
            estado="permitido",
            metodo="facial",
            detalle="Reconocimiento facial exitoso con liveness detection",
            confianza=result.confidence,
        )

    def _on_failure(self, result: MatchResult) -> None:
        logger.warning("Acceso DENEGADO → distancia=%.4f", result.score)

        uid = result.user_id or 0
        self._failed_counts[uid] = self._failed_counts.get(uid, 0) + 1

        self._api.post_log(
            usuario_id=result.user_id,
            estado="denegado",
            metodo="facial",
            detalle="Rostro no reconocido",
            confianza=result.confidence,
        )

        if self._failed_counts[uid] >= MAX_FAILED_ATTEMPTS:
            logger.error("Umbral de intentos fallidos excedido para user_id=%s", uid)
            self._api.post_alerta(
                tipo="intentos_excedidos",
                descripcion=f"Se superaron {MAX_FAILED_ATTEMPTS} intentos fallidos",
                usuario_id=result.user_id,
            )
