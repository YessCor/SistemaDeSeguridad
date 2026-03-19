# local-system/main.py
"""
Punto de entrada del Sistema de Seguridad Inteligente.

Modos:
  --mode auth      (por defecto) Loop de autenticación continua
  --mode register  Registrar un nuevo usuario
"""

import argparse
import logging
import sys

import cv2

from config.settings import LOG_LEVEL, LOG_FILE
from core.auth_controller import AuthController, AuthStatus
from core.camera import Camera

# ── Logging ───────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE),
    ],
)
logger = logging.getLogger("main")


# ── Modos ─────────────────────────────────────────────────────

def run_auth_loop() -> None:
    """Loop principal de autenticación en tiempo real."""
    controller = AuthController()
    controller.load_users()

    logger.info("Sistema de autenticación iniciado. Presiona 'q' para salir.")

    with Camera() as cam:
        controller.reset_liveness()

        for frame in cam.stream():
            status = controller.authenticate(frame)

            # Overlay visual de estado
            color, label = _status_overlay(status)
            cv2.putText(frame, label, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
            cv2.imshow("Smart Security System", frame)

            if status == AuthStatus.GRANTED:
                logger.info("Acceso concedido. Reiniciando sesión en 3 segundos...")
                cv2.waitKey(3000)
                controller.reset_liveness()

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cv2.destroyAllWindows()
    logger.info("Sistema detenido")


def run_register(nombre: str, email: str) -> None:
    """Captura embedding de un nuevo usuario y lo registra en el backend."""
    from core.face_detector import FaceDetector
    from utils.api_client import ApiClient

    detector = FaceDetector()
    api      = ApiClient()

    logger.info("Iniciando registro de usuario: %s <%s>", nombre, email)
    logger.info("Mira directamente a la cámara y presiona ESPACIO para capturar.")

    with Camera() as cam:
        for frame in cam.stream():
            cv2.imshow("Registro — Presiona ESPACIO para capturar", frame)
            key = cv2.waitKey(1) & 0xFF

            if key == ord(" "):
                face = detector.detect_primary(frame)
                if face:
                    result = api.register_user(nombre, email, face.embedding)
                    if result:
                        logger.info("Usuario registrado: %s", result)
                    else:
                        logger.error("Error al registrar en el backend")
                    break
                else:
                    logger.warning("No se detectó rostro. Inténtalo de nuevo.")

            elif key == ord("q"):
                break

    cv2.destroyAllWindows()


def _status_overlay(status: AuthStatus):
    mapping = {
        AuthStatus.NO_FACE:       ((100, 100, 100), "Sin rostro detectado"),
        AuthStatus.LIVENESS_FAIL: ((0, 165, 255),   "Parpadea y mueve la cabeza"),
        AuthStatus.NO_MATCH:      ((0, 0, 220),     "Acceso denegado"),
        AuthStatus.GRANTED:       ((0, 200, 0),     "ACCESO CONCEDIDO"),
    }
    return mapping.get(status, ((255, 255, 255), str(status)))


# ── CLI ───────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smart Security System")
    parser.add_argument("--mode",   choices=["auth", "register"], default="auth")
    parser.add_argument("--nombre", default="", help="Nombre (modo register)")
    parser.add_argument("--email",  default="", help="Email (modo register)")
    args = parser.parse_args()

    if args.mode == "register":
        if not args.nombre or not args.email:
            parser.error("--nombre y --email son requeridos en modo register")
        run_register(args.nombre, args.email)
    else:
        run_auth_loop()
