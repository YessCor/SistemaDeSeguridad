# local-system/core/liveness_detector.py
"""
Detección de vida (liveness detection) para prevenir suplantación con fotos.

Técnicas implementadas:
  1. EAR (Eye Aspect Ratio) — detecta parpadeo real.
  2. Variación del ángulo de cabeza entre frames — detecta movimiento 3D.

Ambas deben superarse para considerar la sesión "viva".
"""

import logging
import math
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, List, Optional

import cv2
import dlib
import numpy as np

from config.settings import (
    BLINK_THRESHOLD,
    BLINKS_REQUIRED,
    HEAD_ANGLE_THRESHOLD,
)

logger = logging.getLogger(__name__)

# Landmarks de ojo izquierdo y derecho (modelo de 68 puntos de dlib)
LEFT_EYE_IDX  = list(range(42, 48))
RIGHT_EYE_IDX = list(range(36, 42))

# Puntos 3D de referencia para estimación de pose
MODEL_POINTS_3D = np.array([
    (0.0,    0.0,    0.0),    # Punta de nariz
    (0.0,   -330.0, -65.0),   # Mentón
    (-225.0, 170.0, -135.0),  # Ojo izquierdo (externo)
    (225.0,  170.0, -135.0),  # Ojo derecho (externo)
    (-150.0,-150.0, -125.0),  # Boca izquierda
    (150.0, -150.0, -125.0),  # Boca derecha
], dtype=np.float64)

LANDMARK_INDICES_FOR_POSE = [30, 8, 36, 45, 48, 54]


@dataclass
class LivenessSession:
    """Estado de una sesión de detección de vida."""
    blinks_detected: int = 0
    head_moved:      bool = False
    is_live:         bool = False
    ear_history:     Deque[float] = field(default_factory=lambda: deque(maxlen=10))
    initial_yaw:     Optional[float] = None

    def reset(self) -> None:
        self.blinks_detected = 0
        self.head_moved      = False
        self.is_live         = False
        self.ear_history.clear()
        self.initial_yaw     = None


class LivenessDetector:
    """
    Evalúa si el sujeto frente a la cámara está vivo.

    Uso:
        detector = LivenessDetector()
        session  = LivenessSession()
        
        for frame in camera.stream():
            liveness = detector.update(frame, session)
            if liveness.is_live:
                break
    """

    def __init__(self) -> None:
        self._predictor = dlib.shape_predictor(
            "models/shape_predictor_68_face_landmarks.dat"
        )
        self._detector = dlib.get_frontal_face_detector()
        logger.info("LivenessDetector inicializado")

    # ── API pública ───────────────────────────────────────────

    def update(self, frame_bgr: np.ndarray, session: LivenessSession) -> LivenessSession:
        """
        Procesa un frame y actualiza el estado de la sesión.

        Args:
            frame_bgr: Frame capturado por OpenCV.
            session:   Sesión mutable que acumula el estado.

        Returns:
            La misma sesión actualizada (mismo objeto).
        """
        gray  = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        faces = self._detector(gray, 0)

        if not faces:
            return session

        shape = self._predictor(gray, faces[0])
        landmarks = self._shape_to_array(shape)

        # ── 1. Detección de parpadeo (EAR) ────────────────────
        ear = self._compute_ear(landmarks)
        session.ear_history.append(ear)

        if self._blink_detected(session.ear_history):
            session.blinks_detected += 1
            logger.debug("Parpadeo detectado (%d/%d)", session.blinks_detected, BLINKS_REQUIRED)

        # ── 2. Detección de movimiento de cabeza (yaw) ────────
        yaw = self._estimate_yaw(landmarks, frame_bgr.shape)
        if yaw is not None:
            if session.initial_yaw is None:
                session.initial_yaw = yaw
            elif abs(yaw - session.initial_yaw) >= HEAD_ANGLE_THRESHOLD:
                session.head_moved = True
                logger.debug("Movimiento de cabeza detectado (Δyaw=%.1f°)", abs(yaw - session.initial_yaw))

        # ── Veredicto final ───────────────────────────────────
        session.is_live = (
            session.blinks_detected >= BLINKS_REQUIRED and
            session.head_moved
        )
        return session

    # ── Cálculo EAR ──────────────────────────────────────────

    @staticmethod
    def _eye_aspect_ratio(eye: np.ndarray) -> float:
        """EAR = (‖p2−p6‖ + ‖p3−p5‖) / (2·‖p1−p4‖)"""
        a = np.linalg.norm(eye[1] - eye[5])
        b = np.linalg.norm(eye[2] - eye[4])
        c = np.linalg.norm(eye[0] - eye[3])
        return (a + b) / (2.0 * c + 1e-6)

    def _compute_ear(self, landmarks: np.ndarray) -> float:
        left  = self._eye_aspect_ratio(landmarks[LEFT_EYE_IDX])
        right = self._eye_aspect_ratio(landmarks[RIGHT_EYE_IDX])
        return (left + right) / 2.0

    @staticmethod
    def _blink_detected(history: Deque[float]) -> bool:
        """Un parpadeo = caída bajo umbral seguida de recuperación."""
        if len(history) < 3:
            return False
        values = list(history)
        below = any(v < BLINK_THRESHOLD for v in values[-3:])
        above = values[-1] >= BLINK_THRESHOLD
        return below and above

    # ── Estimación de pose (yaw) ──────────────────────────────

    def _estimate_yaw(self, landmarks: np.ndarray, shape) -> Optional[float]:
        h, w = shape[:2]
        focal = w
        center = (w / 2, h / 2)
        camera_matrix = np.array([
            [focal, 0,     center[0]],
            [0,     focal, center[1]],
            [0,     0,     1        ],
        ], dtype=np.float64)

        image_points = np.array(
            [landmarks[i] for i in LANDMARK_INDICES_FOR_POSE],
            dtype=np.float64,
        )
        dist_coeffs = np.zeros((4, 1))
        ok, rvec, _ = cv2.solvePnP(
            MODEL_POINTS_3D, image_points,
            camera_matrix, dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )
        if not ok:
            return None

        rmat, _ = cv2.Rodrigues(rvec)
        _, _, _, _, _, _, euler = cv2.decomposeProjectionMatrix(
            np.hstack([rmat, np.zeros((3, 1))])
        )
        yaw = euler[1, 0]
        return float(yaw)

    # ── Utilidades ────────────────────────────────────────────

    @staticmethod
    def _shape_to_array(shape) -> np.ndarray:
        return np.array([[p.x, p.y] for p in shape.parts()])
