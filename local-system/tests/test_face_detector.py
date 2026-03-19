# local-system/tests/test_face_detector.py
"""
Tests unitarios para FaceDetector.
Usa mocks para evitar dependencia de cámara real y modelos pesados.
"""

import numpy as np
import pytest
from unittest.mock import MagicMock, patch


# ── Fixtures ──────────────────────────────────────────────────

@pytest.fixture
def blank_frame():
    """Frame negro 480x640 en formato BGR."""
    return np.zeros((480, 640, 3), dtype=np.uint8)


@pytest.fixture
def fake_embedding():
    """Embedding aleatorio de 128 dimensiones."""
    rng = np.random.default_rng(42)
    return list(rng.random(128))


# ── Tests FaceDetector ────────────────────────────────────────

class TestFaceDetector:

    @patch("core.face_detector.face_recognition.face_locations")
    @patch("core.face_detector.face_recognition.face_encodings")
    def test_detect_returns_empty_when_no_face(self, mock_enc, mock_loc, blank_frame):
        mock_loc.return_value = []
        mock_enc.return_value = []

        from core.face_detector import FaceDetector
        detector = FaceDetector()
        result = detector.detect(blank_frame)

        assert result == []
        mock_enc.assert_not_called()

    @patch("core.face_detector.face_recognition.face_locations")
    @patch("core.face_detector.face_recognition.face_encodings")
    def test_detect_returns_detected_face(self, mock_enc, mock_loc, blank_frame, fake_embedding):
        mock_loc.return_value = [(50, 200, 150, 100)]  # (top, right, bottom, left)
        mock_enc.return_value = [np.array(fake_embedding)]

        from core.face_detector import FaceDetector
        detector = FaceDetector()
        result = detector.detect(blank_frame)

        assert len(result) == 1
        assert result[0].bounding_box == (50, 200, 150, 100)
        assert len(result[0].embedding) == 128

    @patch("core.face_detector.face_recognition.face_locations")
    @patch("core.face_detector.face_recognition.face_encodings")
    def test_detect_primary_returns_largest_face(self, mock_enc, mock_loc, blank_frame, fake_embedding):
        # Dos rostros detectados: uno pequeño y uno grande
        mock_loc.return_value = [
            (10, 60, 60, 10),    # pequeño: 50x50 = 2500 px²
            (10, 210, 160, 10),  # grande:  150x200 = 30000 px²
        ]
        mock_enc.return_value = [
            np.array(fake_embedding),
            np.array(fake_embedding),
        ]

        from core.face_detector import FaceDetector
        detector = FaceDetector()
        primary = detector.detect_primary(blank_frame)

        assert primary is not None
        assert primary.bounding_box == (10, 210, 160, 10)

    def test_detect_primary_returns_none_when_no_face(self, blank_frame):
        with patch("core.face_detector.face_recognition.face_locations", return_value=[]):
            from core.face_detector import FaceDetector
            detector = FaceDetector()
            assert detector.detect_primary(blank_frame) is None


# ── Tests FaceRecognizer ──────────────────────────────────────

class TestFaceRecognizer:

    def test_match_returns_no_match_when_empty(self, fake_embedding):
        from core.face_recognizer import FaceRecognizer
        recognizer = FaceRecognizer()
        result = recognizer.match(fake_embedding)

        assert result.matched is False
        assert result.user_id is None

    @patch("core.face_recognizer.face_recognition.face_distance")
    def test_match_returns_match_within_tolerance(self, mock_dist, fake_embedding):
        mock_dist.return_value = np.array([0.35])  # debajo del tolerance default 0.50

        from core.face_recognizer import FaceRecognizer
        recognizer = FaceRecognizer(tolerance=0.50)
        recognizer.add_user(user_id=1, embedding=fake_embedding)

        result = recognizer.match(fake_embedding)

        assert result.matched is True
        assert result.user_id == 1
        assert result.confidence > 0.5

    @patch("core.face_recognizer.face_recognition.face_distance")
    def test_match_returns_no_match_beyond_tolerance(self, mock_dist, fake_embedding):
        mock_dist.return_value = np.array([0.72])  # más allá de 0.50

        from core.face_recognizer import FaceRecognizer
        recognizer = FaceRecognizer(tolerance=0.50)
        recognizer.add_user(user_id=1, embedding=fake_embedding)

        result = recognizer.match(fake_embedding)

        assert result.matched is False
