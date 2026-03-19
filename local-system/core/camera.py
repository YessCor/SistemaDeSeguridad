# local-system/core/camera.py
"""
Captura de video desde webcam.
Gestiona el ciclo de vida del dispositivo de cámara.
"""

import cv2
import logging
from typing import Optional, Generator
from config.settings import CAMERA_INDEX, FRAME_WIDTH, FRAME_HEIGHT, TARGET_FPS

logger = logging.getLogger(__name__)


class Camera:
    """
    Abstracción sobre OpenCV VideoCapture.
    Uso como context manager garantiza liberación de recursos.
    
    Ejemplo:
        with Camera() as cam:
            for frame in cam.stream():
                process(frame)
    """

    def __init__(self, index: int = CAMERA_INDEX) -> None:
        self._index = index
        self._cap: Optional[cv2.VideoCapture] = None

    # ── Ciclo de vida ─────────────────────────────────────────

    def open(self) -> None:
        self._cap = cv2.VideoCapture(self._index)
        if not self._cap.isOpened():
            raise RuntimeError(f"No se pudo abrir la cámara con índice {self._index}")

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_WIDTH)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        self._cap.set(cv2.CAP_PROP_FPS,          TARGET_FPS)
        logger.info("Cámara inicializada: %dx%d @ %d fps", FRAME_WIDTH, FRAME_HEIGHT, TARGET_FPS)

    def release(self) -> None:
        if self._cap and self._cap.isOpened():
            self._cap.release()
            logger.info("Cámara liberada")

    def __enter__(self) -> "Camera":
        self.open()
        return self

    def __exit__(self, *_) -> None:
        self.release()

    # ── Lectura de frames ─────────────────────────────────────

    def read_frame(self) -> Optional[cv2.typing.MatLike]:
        """Lee un frame BGR. Retorna None si la captura falla."""
        if not self._cap:
            return None
        ok, frame = self._cap.read()
        return frame if ok else None

    def stream(self) -> Generator[cv2.typing.MatLike, None, None]:
        """Generador infinito de frames. Detener con KeyboardInterrupt."""
        while True:
            frame = self.read_frame()
            if frame is None:
                logger.warning("Frame no disponible, reintentando...")
                continue
            yield frame
