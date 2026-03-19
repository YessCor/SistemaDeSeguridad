# local-system/core/face_recognizer.py
"""
Reconocimiento facial basado en comparación de embeddings.
Compara el embedding capturado contra los registrados en el backend.
"""

import logging
from typing import Optional, Tuple

import face_recognition
import numpy as np

from config.settings import FACE_TOLERANCE
from core.face_detector import Embedding

logger = logging.getLogger(__name__)


class MatchResult:
    """Resultado de una comparación facial."""

    def __init__(self, matched: bool, user_id: Optional[int], score: float) -> None:
        self.matched  = matched
        self.user_id  = user_id
        self.score    = score              # 0.0 = idéntico, 1.0 = muy diferente

    @property
    def confidence(self) -> float:
        """Confianza entre 0 y 1 (inverso de la distancia)."""
        return max(0.0, 1.0 - self.score)

    def __repr__(self) -> str:
        return f"MatchResult(matched={self.matched}, user_id={self.user_id}, score={self.score:.4f})"


class FaceRecognizer:
    """
    Compara el embedding capturado contra una base de conocidos.

    Los embeddings conocidos se cargan desde el backend al iniciar
    o registrar un nuevo usuario, y se almacenan en memoria para
    comparaciones rápidas sin round-trip a la API en cada frame.
    """

    def __init__(self, tolerance: float = FACE_TOLERANCE) -> None:
        self._tolerance = tolerance
        # { user_id: embedding_vector }
        self._known: dict[int, Embedding] = {}

    # ── Gestión de conocidos ──────────────────────────────────

    def load_known(self, known: dict[int, Embedding]) -> None:
        """Carga o reemplaza el conjunto de embeddings conocidos."""
        self._known = known
        logger.info("Cargados %d embedding(s) en memoria", len(known))

    def add_user(self, user_id: int, embedding: Embedding) -> None:
        self._known[user_id] = embedding

    def remove_user(self, user_id: int) -> None:
        self._known.pop(user_id, None)

    # ── Comparación ───────────────────────────────────────────

    def match(self, embedding: Embedding) -> MatchResult:
        """
        Busca el usuario más cercano al embedding dado.

        Returns:
            MatchResult con matched=True si la distancia es ≤ tolerance.
        """
        if not self._known:
            logger.warning("No hay embeddings cargados. Registre usuarios primero.")
            return MatchResult(matched=False, user_id=None, score=1.0)

        query = np.array(embedding)
        best_id, best_dist = self._find_best(query)

        matched = best_dist <= self._tolerance
        logger.debug("Mejor match → user_id=%s dist=%.4f (tolerance=%.2f)", best_id, best_dist, self._tolerance)
        return MatchResult(matched=matched, user_id=best_id if matched else None, score=float(best_dist))

    # ── Privado ───────────────────────────────────────────────

    def _find_best(self, query: np.ndarray) -> Tuple[int, float]:
        best_id   = -1
        best_dist = float("inf")

        for uid, known_emb in self._known.items():
            dist = face_recognition.face_distance([np.array(known_emb)], query)[0]
            if dist < best_dist:
                best_dist = dist
                best_id   = uid

        return best_id, best_dist
