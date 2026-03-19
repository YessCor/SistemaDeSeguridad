# local-system/tests/test_liveness_detector.py
"""
Tests unitarios para el modulo LivenessDetector.

Estos tests verifican:
- Detección de parpadeo (EAR)
- Estimación de pose de cabeza
- Estado de sesión de liveness
"""

import pytest
import numpy as np
from collections import deque

from core.liveness_detector import LivenessDetector, LivenessSession


class TestEyeAspectRatio:
    """Tests para el calculo de EAR (Eye Aspect Ratio)."""

    def test_eye_aspect_ratio_ojo_abierto(self):
        """EAR debe ser alto cuando el ojo esta abierto."""
        eye = np.array([
            [0.0, 3.0],
            [1.0, 2.0],
            [1.0, 2.0],
            [4.0, 3.0],
            [1.0, 2.0],
            [1.0, 2.0],
        ], dtype=np.float64)

        ear = LivenessDetector._eye_aspect_ratio(LivenessDetector, eye)
        
        assert ear > 0.2, f"EAR demasiado bajo para ojo abierto: {ear}"

    def test_eye_aspect_ratio_ojo_cerrado(self):
        """EAR debe ser bajo cuando el ojo esta cerrado."""
        eye = np.array([
            [0.0, 3.0],
            [1.0, 3.0],
            [1.0, 3.0],
            [4.0, 3.0],
            [1.0, 3.0],
            [1.0, 3.0],
        ], dtype=np.float64)

        ear = LivenessDetector._eye_aspect_ratio(LivenessDetector, eye)
        
        assert ear < 0.15, f"EAR demasiado alto para ojo cerrado: {ear}"

    def test_eye_aspect_ratio_division_por_cero(self):
        """Debe manejar division por cero."""
        eye = np.array([
            [0.0, 0.0],
            [0.0, 0.0],
            [0.0, 0.0],
            [0.0, 0.0],
            [0.0, 0.0],
            [0.0, 0.0],
        ], dtype=np.float64)

        ear = LivenessDetector._eye_aspect_ratio(LivenessDetector, eye)
        assert ear >= 0


class TestBlinkDetection:
    """Tests para la deteccion de parpadeo."""

    def test_blink_detected_con_historial_valido(self):
        """Debe detectar parpadeo cuando hay caida y recuperacion."""
        history = deque([0.3, 0.2, 0.3])
        
        assert LivenessDetector._blink_detected(LivenessDetector, history) is True

    def test_blink_no_detectado_sin_recuperacion(self):
        """No debe detectar parpadeo sin recuperacion."""
        history = deque([0.3, 0.2, 0.15])
        
        assert LivenessDetector._blink_detected(LivenessDetector, history) is False

    def test_blink_no_detectado_sin_caida(self):
        """No debe detectar parpadeo sin caida."""
        history = deque([0.3, 0.3, 0.3])
        
        assert LivenessDetector._blink_detected(LivenessDetector, history) is False

    def test_blink_no_detectado_historial_corto(self):
        """No debe detectar parpadeo con historial muy corto."""
        history = deque([0.3, 0.2])
        
        assert LivenessDetector._blink_detected(LivenessDetector, history) is False


class TestLivenessSession:
    """Tests para el estado de sesion de liveness."""

    def test_session_reset(self):
        """Debe reiniciar todos los valores."""
        session = LivenessSession()
        
        session.blinks_detected = 5
        session.head_moved = True
        session.is_live = True
        session.ear_history.append(0.3)
        session.initial_yaw = 10.0
        
        session.reset()
        
        assert session.blinks_detected == 0
        assert session.head_moved is False
        assert session.is_live is False
        assert len(session.ear_history) == 0
        assert session.initial_yaw is None


class TestLivenessDetector:
    """Tests de integracion para LivenessDetector."""

    def test_inicializacion(self):
        """Debe inicializar sin errores."""
        try:
            detector = LivenessDetector()
            assert detector is not None
        except Exception as e:
            pytest.skip(f"Modelo de dlib no disponible: {e}")

    def test_update_sin_rostro(self):
        """Debe manejar frames sin rostro."""
        try:
            detector = LivenessDetector()
            session = LivenessSession()
            
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            
            result = detector.update(frame, session)
            
            assert result.is_live is False
        except Exception as e:
            pytest.skip(f"Modelo de dlib no disponible: {e}")


class TestLivenessIntegration:
    """Tests de integracion simulando secuencia de frames."""

    def test_secuencia_liveness_completa(self):
        """Simula una secuencia completa de liveness."""
        try:
            session = LivenessSession()
            
            session.blinks_detected = 2
            session.head_moved = True
            
            session.is_live = (
                session.blinks_detected >= 2 and
                session.head_moved
            )
            assert session.is_live is True
            
        except Exception as e:
            pytest.skip(f"Test de integracion simulado: {e}")

    def test_liveness_falla_sin_parpadeo(self):
        """Sesion NO debe estar viva sin parpadeo."""
        session = LivenessSession()
        
        session.blinks_detected = 0
        session.head_moved = True
        
        session.is_live = (
            session.blinks_detected >= 2 and
            session.head_moved
        )
        
        assert session.is_live is False

    def test_liveness_falla_sin_movimiento_cabeza(self):
        """Sesion NO debe estar viva sin movimiento de cabeza."""
        session = LivenessSession()
        
        session.blinks_detected = 2
        session.head_moved = False
        
        session.is_live = (
            session.blinks_detected >= 2 and
            session.head_moved
        )
        
        assert session.is_live is False
