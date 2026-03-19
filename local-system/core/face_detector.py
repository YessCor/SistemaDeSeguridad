# local-system/core/face_detector.py
"""
Detección y codificación de rostros usando face_recognition (dlib).
Extrae embeddings de 128 dimensiones por cada rostro detectado.
"""

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import face_recognition
import numpy as np

from config.settings import FACE_MODEL

logger = logging.getLogger(__name__)

# Tipo alias para claridad
Embedding = List[float]                   # Vector de 128 floats
BoundingBox = Tuple[int, int, int, int]   # (top, right, bottom, left)


@dataclass
class DetectedFace:
    """Rostro detectado con su bounding box y embedding."""
    bounding_box: BoundingBox
    embedding: Embedding
    confidence: float = 1.0


class FaceDetector:
    """
    Encapsula la detección y codificación facial.
    
    Convierte frames BGR (OpenCV) a RGB antes de procesarlos
    porque face_recognition trabaja en espacio RGB.
    """

    def __init__(self, model: str = FACE_MODEL) -> None:
        self._model = model
        logger.info("FaceDetector inicializado (modelo: %s)", model)

    # ── API pública ───────────────────────────────────────────

    def detect(self, frame_bgr: np.ndarray) -> List[DetectedFace]:
        """
        Detecta todos los rostros en el frame.

        Args:
            frame_bgr: Frame en formato BGR (salida de OpenCV).

        Returns:
            Lista de DetectedFace (puede estar vacía).
        """
        rgb = self._to_rgb(frame_bgr)
        locations = face_recognition.face_locations(rgb, model="hog")

        if not locations:
            return []

        encodings = face_recognition.face_encodings(rgb, locations, model=self._model)

        faces = [
            DetectedFace(bounding_box=loc, embedding=list(enc))
            for loc, enc in zip(locations, encodings)
        ]
        logger.debug("%d rostro(s) detectado(s)", len(faces))
        return faces

    def detect_primary(self, frame_bgr: np.ndarray) -> Optional[DetectedFace]:
        """Retorna el rostro más grande (principal) o None."""
        faces = self.detect(frame_bgr)
        if not faces:
            return None
        return max(faces, key=lambda f: self._area(f.bounding_box))

    # ── Utilidades ────────────────────────────────────────────

    @staticmethod
    def _to_rgb(frame_bgr: np.ndarray) -> np.ndarray:
        return cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

    @staticmethod
    def _area(box: BoundingBox) -> int:
        top, right, bottom, left = box
        return (bottom - top) * (right - left)
