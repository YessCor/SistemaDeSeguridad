# local-system/core/face_auth_system.py
"""
Sistema de autenticación facial en tiempo real.

Este módulo proporciona una clase principal FaceAuthSystem que integra:
- Captura de video desde webcam
- Detección de rostros
- Reconocimiento facial usando embeddings
- Liveness detection (parpadeo + movimiento de cabeza)
- Visualización en tiempo real con OpenCV

Uso:
    auth_system = FaceAuthSystem()
    auth_system.load_users_from_api("http://localhost:3000")
    resultado = auth_system.run_authentication()
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Dict, List, Tuple
from collections import deque

import cv2
import face_recognition
import mediapipe as mp
import numpy as np

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AuthState(Enum):
    """Estados del proceso de autenticación."""
    NO_FACE = auto()
    SEARCHING = auto()          # Buscando rostro
    BLINK_REQUIRED = auto()     # Esperando parpadeo
    HEAD_MOVE_REQUIRED = auto() # Esperando movimiento de cabeza
    AUTHENTICATING = auto()     # Autenticando
    GRANTED = auto()             # Acceso concedido
    DENIED = auto()              # Acceso denegado
    ERROR = auto()               # Error


class AuthResult:
    """Resultado de la autenticación."""
    def __init__(self, usuario: str, estado: str, liveness: bool, 
                 confianza: float = 0.0, mensaje: str = ""):
        self.usuario = usuario
        self.estado = estado          # "permitido" o "denegado"
        self.liveness = liveness
        self.confianza = confianza
        self.mensaje = mensaje
    
    def to_dict(self) -> dict:
        """Convierte el resultado a diccionario para API REST."""
        return {
            "usuario": self.usuario,
            "estado": self.estado,
            "liveness": self.liveness,
            "confianza": self.confianza,
            "mensaje": self.mensaje
        }
    
    def __repr__(self) -> str:
        return (f"AuthResult(usuario={self.usuario}, estado={self.estado}, "
                f"liveness={self.liveness}, confianza={self.confianza:.2f})")


@dataclass
class LivenessState:
    """Estado de la detección de vida (liveness)."""
    blinks_detected: int = 0
    head_moved_left: bool = False
    head_moved_right: bool = False
    initial_yaw: Optional[float] = None
    is_live: bool = False
    ear_history: deque = field(default_factory=lambda: deque(maxlen=10))
    yaw_history: deque = field(default_factory=lambda: deque(maxlen=10))
    
    def reset(self) -> None:
        """Reinicia el estado de liveness."""
        self.blinks_detected = 0
        self.head_moved_left = False
        self.head_moved_right = False
        self.initial_yaw = None
        self.is_live = False
        self.ear_history.clear()
        self.yaw_history.clear()


class FaceAuthSystem:
    """
    Sistema principal de autenticación facial.
    
    Proporciona métodos para:
    - Capturar frames de la webcam
    - Detectar rostros
    - Reconocer rostros usando embeddings
    - Verificar liveness (parpadeo + movimiento de cabeza)
    - Ejecutar autenticación completa en tiempo real
    
    Ejemplo de uso:
        auth_system = FaceAuthSystem()
        auth_system.load_users([{"id": 1, "nombre": "Juan", "encoding": [...]}])
        resultado = auth_system.run_authentication()
    """
    
    # Constantes de configuración
    BLINK_THRESHOLD = 0.25        # EAR mínimo para considerar ojo cerrado
    BLINKS_REQUIRED = 1            # Parpadeos mínimos requeridos
    HEAD_ANGLE_THRESHOLD = 15      # Grados mínimos de movimiento de cabeza
    FACE_TOLERANCE = 0.6           # Tolerancia para reconocimiento facial
    MIN_FACE_SIZE = 80             # Tamaño mínimo del rostro en pixels
    
    def __init__(self, camera_index: int = 0, show_video: bool = True):
        """
        Inicializa el sistema de autenticación facial.
        
        Args:
            camera_index: Índice de la cámara a usar (default: 0)
            show_video: Si True, muestra la ventana con el video
        """
        self.camera_index = camera_index
        self.show_video = show_video
        
        # Inicializar componentes
        self._cap: Optional[cv2.VideoCapture] = None
        self._known_users: Dict[int, Dict] = {}  # {user_id: {nombre, encoding}}
        
        # Inicializar MediaPipe para detección de facial landmarks
        self._mp_face_mesh = mp.solutions.face_mesh
        self._face_mesh = self._mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Estado de liveness
        self._liveness_state = LivenessState()
        
        # Estado de autenticación
        self._auth_state = AuthState.SEARCHING
        
        # Variables para visualización
        self._current_message = ""
        self._face_bbox: Optional[Tuple[int, int, int, int]] = None
        
        logger.info("FaceAuthSystem inicializado")
    
    # =========================================================================
    # Métodos de gestión de usuarios
    # =========================================================================
    
    def load_users(self, users: List[Dict]) -> int:
        """
        Carga usuarios conocidos para reconocimiento facial.
        
        Args:
            users: Lista de diccionarios con formato:
                   [{"id": 1, "nombre": "Juan", "encoding": [...]}]
        
        Returns:
            Número de usuarios cargados
        """
        self._known_users.clear()
        
        for user in users:
            user_id = user.get("id")
            encoding = user.get("encoding")
            
            if user_id and encoding:
                self._known_users[user_id] = {
                    "nombre": user.get("nombre", "Desconocido"),
                    "encoding": np.array(encoding)
                }
        
        logger.info(f"Cargados {len(self._known_users)} usuarios para reconocimiento")
        return len(self._known_users)
    
    def load_users_from_api(self, api_url: str, api_key: str = "") -> int:
        """
        Carga usuarios desde la API REST del backend.
        
        Args:
            api_url: URL base de la API
            api_key: Clave API (opcional)
        
        Returns:
            Número de usuarios cargados
        """
        try:
            import requests
            headers = {"X-API-Key": api_key} if api_key else {}
            response = requests.get(f"{api_url}/api/usuarios", headers=headers, timeout=5)
            
            if response.status_code == 200:
                users = response.json()
                return self.load_users(users)
            else:
                logger.error(f"Error de API: {response.status_code}")
                return 0
        except ImportError:
            logger.error("Requests no está instalado")
            return 0
        except Exception as e:
            logger.error(f"Error al cargar usuarios: {e}")
            return 0
    
    def add_user(self, user_id: int, nombre: str, encoding: List[float]) -> None:
        """Agrega un usuario al sistema."""
        self._known_users[user_id] = {
            "nombre": nombre,
            "encoding": np.array(encoding)
        }
    
    def remove_user(self, user_id: int) -> bool:
        """Elimina un usuario del sistema."""
        return self._known_users.pop(user_id, None) is not None
    
    # =========================================================================
    # Métodos de captura de video
    # =========================================================================
    
    def open_camera(self) -> bool:
        """
        Abre la conexión con la cámara.
        
        Returns:
            True si la cámara se abrió correctamente
        """
        self._cap = cv2.VideoCapture(self.camera_index)
        
        if not self._cap.isOpened():
            logger.error(f"No se pudo abrir la cámara {self.camera_index}")
            return False
        
        # Configurar resolución
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        logger.info(f"Cámara {self.camera_index} abierta correctamente")
        return True
    
    def close_camera(self) -> None:
        """Cierra la conexión con la cámara."""
        if self._cap and self._cap.isOpened():
            self._cap.release()
            logger.info("Cámara cerrada")
    
    def capture_frame(self) -> Optional[np.ndarray]:
        """
        Captura un frame de la cámara.
        
        Returns:
            Frame en formato BGR (numpy array) o None si falla
        """
        if not self._cap or not self._cap.isOpened():
            return None
        
        ret, frame = self._cap.read()
        return frame if ret else None
    
    # =========================================================================
    # Métodos de detección de rostros
    # =========================================================================
    
    def detect_face(self, frame: np.ndarray) -> Optional[Tuple[np.ndarray, Tuple[int, int, int, int]]]:
        """
        Detecta el rostro más grande en el frame.
        
        Args:
            frame: Frame en formato BGR
        
        Returns:
            Tupla (encoding, bounding_box) o None si no hay rostro
        """
        # Convertir a RGB para face_recognition
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detectar ubicaciones de rostros
        face_locations = face_recognition.face_locations(rgb_frame, model="hog")
        
        if not face_locations:
            return None
        
        # Obtener el rostro más grande
        face_bbox = max(face_locations, key=lambda b: (b[2]-b[0])*(b[1]-b[3]))
        
        # Verificar tamaño mínimo
        top, right, bottom, left = face_bbox
        face_width = right - left
        face_height = bottom - top
        
        if face_width < self.MIN_FACE_SIZE or face_height < self.MIN_FACE_SIZE:
            return None
        
        # Obtener encoding del rostro
        face_encodings = face_recognition.face_encodings(rgb_frame, [face_bbox])
        
        if not face_encodings:
            return None
        
        self._face_bbox = face_bbox
        return face_encodings[0], face_bbox
    
    def get_face_landmarks(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        Obtiene los landmarks faciales usando MediaPipe.
        
        Args:
            frame: Frame en formato BGR
        
        Returns:
            Array de landmarks o None
        """
        # Convertir a RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb_frame.flags.writeable = False
        
        # Detectar landmarks
        results = self._face_mesh.process(rgb_frame)
        
        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0]
            return np.array([(lm.x, lm.y, lm.z) for lm in landmarks.landmark])
        
        return None
    
    # =========================================================================
    # Métodos de reconocimiento facial
    # =========================================================================
    
    def recognize_face(self, encoding: np.ndarray) -> Tuple[Optional[int], float]:
        """
        Reconoce el rostro comparando con usuarios conocidos.
        
        Args:
            encoding: Embedding del rostro a reconocer
        
        Returns:
            Tupla (user_id, distancia)
        """
        if not self._known_users:
            logger.warning("No hay usuarios cargados")
            return None, 1.0
        
        best_match = None
        best_distance = float("inf")
        
        for user_id, user_data in self._known_users.items():
            known_encoding = user_data["encoding"]
            
            # Calcular distancia
            distances = face_recognition.face_distance([known_encoding], encoding)
            distance = distances[0]
            
            if distance < best_distance:
                best_distance = distance
                best_match = user_id
        
        # Verificar si está dentro de la tolerancia
        if best_distance <= self.FACE_TOLERANCE:
            return best_match, best_distance
        
        return None, best_distance
    
    def recognize_face_with_name(self, encoding: np.ndarray) -> Tuple[str, float]:
        """
        Reconoce el rostro y retorna el nombre.
        
        Args:
            encoding: Embedding del rostro
        
        Returns:
            Tupla (nombre_usuario, confianza)
        """
        user_id, distance = self.recognize_face(encoding)
        
        if user_id is not None:
            nombre = self._known_users[user_id].get("nombre", "Desconocido")
            confianza = max(0.0, 1.0 - distance)
            return nombre, confianza
        
        return "desconocido", 0.0
    
    # =========================================================================
    # Métodos de detección de parpadeo (Eye Aspect Ratio)
    # =========================================================================
    
    def calculate_ear(self, landmarks: np.ndarray) -> float:
        """
        Calcula el Eye Aspect Ratio (EAR) para ambos ojos.
        
        Args:
            landmarks: Array de landmarks faciales
        
        Returns:
            EAR promedio de ambos ojos
        """
        # Índices de landmarks de ojos (MediaPipe)
        # Ojo izquierdo: 33, 133, 160, 158, 153, 144
        # Ojo derecho: 362, 263, 387, 385, 380, 373
        
        LEFT_EYE = [33, 133, 160, 158, 153, 144]
        RIGHT_EYE = [362, 263, 387, 385, 380, 373]
        
        def eye_aspect_ratio(eye_indices):
            # Puntos del ojo
            p1 = landmarks[eye_indices[0]][:2]  # Esquina exterior
            p2 = landmarks[eye_indices[1]][:2]    # Arriba
            p3 = landmarks[eye_indices[2]][:2]    # Corner interno arriba
            p4 = landmarks[eye_indices[3]][:2]    # Corner interno abajo
            p5 = landmarks[eye_indices[4]][:2]    # Abajo
            p6 = landmarks[eye_indices[5]][:2]    # Esquina exterior
            
            # Calcular distancias verticales
            vertical_1 = np.linalg.norm(p2 - p5)
            vertical_2 = np.linalg.norm(p3 - p4)
            
            # Distancia horizontal
            horizontal = np.linalg.norm(p1 - p6)
            
            # EAR
            ear = (vertical_1 + vertical_2) / (2.0 * horizontal + 1e-6)
            return ear
        
        left_ear = eye_aspect_ratio(LEFT_EYE)
        right_ear = eye_aspect_ratio(RIGHT_EYE)
        
        return (left_ear + right_ear) / 2.0
    
    def detect_blink(self, ear: float) -> bool:
        """
        Detecta si ocurre un parpadeo.
        
        Args:
            ear: Valor actual del EAR
        
        Returns:
            True si se detecta un parpadeo
        """
        self._liveness_state.ear_history.append(ear)
        
        # Necesitamos al menos 3 valores para detectar parpadeo
        if len(self._liveness_state.ear_history) < 3:
            return False
        
        history = list(self._liveness_state.ear_history)
        
        # Parpadeo: ojo pasa de abierto a cerrado y vuelve a abrir
        # Buscar: valor bajo en medio de valores altos
        for i in range(1, len(history) - 1):
            if (history[i] < self.BLINK_THRESHOLD and 
                history[i-1] >= self.BLINK_THRESHOLD and 
                history[i+1] >= self.BLINK_THRESHOLD):
                return True
        
        return False
    
    # =========================================================================
    # Métodos de detección de movimiento de cabeza
    # =========================================================================
    
    def calculate_yaw(self, landmarks: np.ndarray, frame_width: int) -> float:
        """
        Calcula el ángulo de guiño (yaw) de la cabeza.
        
        Args:
            landmarks: Array de landmarks faciales
            frame_width: Ancho del frame
        
        Returns:
            Ángulo de yaw en grados
        """
        # Usar puntos de referencia de la nariz y ojos
        # Punto central de la nariz
        nose_tip = landmarks[1][:2]
        
        # Ojo izquierdo e derecho
        left_eye = landmarks[33][:2]
        right_eye = landmarks[263][:2]
        
        # Centro de los ojos
        eye_center = (left_eye + right_eye) / 2
        
        # Distancia entre ojos (ancho de referencia)
        eye_distance = np.linalg.norm(right_eye - left_eye)
        
        if eye_distance < 1e-6:
            return 0.0
        
        # Desplazamiento horizontal de la nariz respecto al centro de los ojos
        nose_offset = (nose_tip[0] - eye_center[0]) / eye_distance
        
        # Convertir a grados (aproximación)
        yaw = np.degrees(np.arcsin(np.clip(nose_offset, -1, 1)))
        
        return yaw
    
    def detect_head_movement(self, yaw: float) -> bool:
        """
        Detecta movimiento de cabeza izquierda/derecha.
        
        Args:
            yaw: Ángulo actual de yaw
        
        Returns:
            True si se detectó movimiento suficiente
        """
        # Guardar yaw inicial
        if self._liveness_state.initial_yaw is None:
            self._liveness_state.initial_yaw = yaw
            return False
        
        self._liveness_state.yaw_history.append(yaw)
        
        # Calcular diferencia con el yaw inicial
        delta_yaw = abs(yaw - self._liveness_state.initial_yaw)
        
        # Verificar movimiento a izquierda o derecha
        if delta_yaw >= self.HEAD_ANGLE_THRESHOLD:
            if yaw < self._liveness_state.initial_yaw:
                self._liveness_state.head_moved_left = True
            else:
                self._liveness_state.head_moved_right = True
            return True
        
        return False
    
    # =========================================================================
    # Métodos de validación de liveness
    # =========================================================================
    
    def check_liveness(self, frame: np.ndarray) -> bool:
        """
        Verifica si el sujeto está vivo (parpadeo + movimiento de cabeza).
        
        Args:
            frame: Frame actual
        
        Returns:
            True si se pasó la verificación de liveness
        """
        # Obtener landmarks
        landmarks = self.get_face_landmarks(frame)
        
        if landmarks is None:
            self._current_message = "No se detectó rostro"
            return False
        
        # Detectar parpadeo
        ear = self.calculate_ear(landmarks)
        if self.detect_blink(ear):
            self._liveness_state.blinks_detected += 1
            logger.debug(f"Parpadeo detectado: {self._liveness_state.blinks_detected}/{self.BLINKS_REQUIRED}")
        
        # Detectar movimiento de cabeza
        frame_height, frame_width = frame.shape[:2]
        yaw = self.calculate_yaw(landmarks, frame_width)
        self.detect_head_movement(yaw)
        
        # Actualizar mensaje según estado
        if self._liveness_state.blinks_detected < self.BLINKS_REQUIRED:
            self._current_message = f"Parpadea ({self._liveness_state.blinks_detected}/{self.BLINKS_REQUIRED})"
            self._auth_state = AuthState.BLINK_REQUIRED
        elif not (self._liveness_state.head_moved_left or self._liveness_state.head_moved_right):
            self._current_message = "Mueve la cabeza a izquierda/derecha"
            self._auth_state = AuthState.HEAD_MOVE_REQUIRED
        else:
            self._current_message = "Liveness verificado"
            self._liveness_state.is_live = True
            return True
        
        return False
    
    def reset_liveness(self) -> None:
        """Reinicia el estado de liveness para un nuevo intento."""
        self._liveness_state.reset()
        self._current_message = "Buscando rostro..."
        self._auth_state = AuthState.SEARCHING
    
    # =========================================================================
    # Métodos de autenticación completa
    # =========================================================================
    
    def authenticate_frame(self, frame: np.ndarray) -> AuthResult:
        """
        Procesa un frame y retorna resultado de autenticación.
        
        Args:
            frame: Frame a procesar
        
        Returns:
            AuthResult con el estado de autenticación
        """
        # Detectar rostro
        face_data = self.detect_face(frame)
        
        if face_data is None:
            self._current_message = "Buscando rostro..."
            self._auth_state = AuthState.NO_FACE
            return AuthResult("desconocido", "denegado", False, 0.0, "No se detectó rostro")
        
        encoding, bbox = face_data
        
        # Verificar liveness
        if not self._liveness_state.is_live:
            self.check_liveness(frame)
            return AuthResult("desconocido", "denegado", False, 0.0, self._current_message)
        
        # Reconocer rostro
        self._auth_state = AuthState.AUTHENTICATING
        nombre, confianza = self.recognize_face_with_name(encoding)
        
        if nombre != "desconocido":
            self._auth_state = AuthState.GRANTED
            self._current_message = f"Bienvenido, {nombre}"
            return AuthResult(nombre, "permitido", True, confianza, f"Acceso concedido ({confianza*100:.1f}%)")
        else:
            self._auth_state = AuthState.DENIED
            self._current_message = "Usuario no reconocido"
            return AuthResult("desconocido", "denegado", True, confianza, "Rostro no registrado")
    
    def run_authentication(self, max_time: float = 30.0) -> AuthResult:
        """
        Ejecuta el proceso completo de autenticación.
        
        Args:
            max_time: Tiempo máximo de espera en segundos
        
        Returns:
            AuthResult final de la autenticación
        """
        # Abrir cámara
        if not self.open_camera():
            return AuthResult("error", "denegado", False, 0.0, "Error al abrir cámara")
        
        start_time = time.time()
        result = None
        
        try:
            while True:
                # Verificar tiempo máximo
                if time.time() - start_time > max_time:
                    self._current_message = "Tiempo agotado"
                    result = AuthResult("desconocido", "denegado", False, 0.0, "Tiempo máximo superado")
                    break
                
                # Capturar frame
                frame = self.capture_frame()
                
                if frame is None:
                    continue
                
                # Procesar frame
                result = self.authenticate_frame(frame)
                
                # Dibujar visualización
                if self.show_video:
                    self._draw_status(frame, result)
                    
                    # Mostrar frame
                    cv2.imshow("Sistema de Autenticacion Facial", frame)
                    
                    # Salir con 'q'
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        result = AuthResult("desconocido", "denegado", False, 0.0, "Cancelado por usuario")
                        break
                
                # Si autenticación exitosa o denegada, salir
                if result.estado == "permitido" or (result.estado == "denegado" and result.liveness):
                    break
                
        finally:
            # Limpiar recursos
            self.close_camera()
            if self.show_video:
                cv2.destroyAllWindows()
        
        logger.info(f"Autenticación completada: {result}")
        return result
    
    # =========================================================================
    # Métodos de visualización
    # =========================================================================
    
    def _draw_status(self, frame: np.ndarray, result: AuthResult) -> None:
        """
        Dibuja el estado actual en el frame.
        
        Args:
            frame: Frame a dibujar
            result: Resultado de autenticación
        """
        h, w = frame.shape[:2]
        
        # Color según estado
        if self._auth_state == AuthState.GRANTED:
            color = (0, 255, 0)  # Verde
        elif self._auth_state == AuthState.DENIED:
            color = (0, 0, 255)  # Rojo
        elif self._auth_state in [AuthState.BLINK_REQUIRED, AuthState.HEAD_MOVE_REQUIRED]:
            color = (0, 165, 255)  # Naranja
        else:
            color = (255, 255, 255)  # Blanco
        
        # Dibujar bounding box del rostro
        if self._face_bbox:
            top, right, bottom, left = self._face_bbox
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        
        # Dibujar rectángulo de fondo para texto
        cv2.rectangle(frame, (0, h-60), (w, h), (0, 0, 0), -1)
        
        # Dibujar mensaje
        cv2.putText(frame, self._current_message, (10, h-25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        # Dibujar estado de liveness
        liveness_text = f"Blinks: {self._liveness_state.blinks_detected}/{self.BLINKS_REQUIRED}"
        if self._liveness_state.head_moved_left or self._liveness_state.head_moved_right:
            liveness_text += " | Cabeza: OK"
        else:
            liveness_text += " | Cabeza: -"
        
        cv2.putText(frame, liveness_text, (10, h-45),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        # Dibujar resultado si existe
        if result and result.estado != "denegado":
            result_text = f"Usuario: {result.usuario} | Confianza: {result.confianza*100:.1f}%"
            cv2.putText(frame, result_text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    
    # =========================================================================
    # Método de preparación para API REST
    # =========================================================================
    
    def prepare_for_api(self, result: AuthResult) -> dict:
        """
        Prepara el resultado para envío a API REST.
        
        Args:
            result: Resultado de autenticación
        
        Returns:
            Diccionario listo para JSON
        """
        return result.to_dict()


# =============================================================================
# Ejemplo de uso
# =============================================================================

def main():
    """Ejemplo de uso del sistema de autenticación facial."""
    print("=" * 50)
    print("Sistema de Autenticación Facial")
    print("=" * 50)
    
    # Crear instancia del sistema
    auth_system = FaceAuthSystem(camera_index=0, show_video=True)
    
    # Cargar usuarios de ejemplo (en producción, cargar desde API)
    usuarios_ejemplo = [
        {
            "id": 1,
            "nombre": "Usuario de Prueba",
            # Embedding de ejemplo (128 valores aleatorios)
            "encoding": np.random.rand(128).tolist()
        }
    ]
    
    auth_system.load_users(usuarios_ejemplo)
    print(f"Usuarios cargados: {len(usuarios_ejemplo)}")
    
    # También puedes cargar desde API:
    # auth_system.load_users_from_api("http://localhost:3000", "tu-api-key")
    
    # Ejecutar autenticación
    print("\nIniciando autenticación...")
    print("Presiona 'q' para cancelar\n")
    
    resultado = auth_system.run_authentication(max_time=30.0)
    
    # Mostrar resultado
    print("\n" + "=" * 50)
    print("RESULTADO")
    print("=" * 50)
    print(f"Usuario: {resultado.usuario}")
    print(f"Estado: {resultado.estado}")
    print(f"Liveness: {resultado.liveness}")
    print(f"Confianza: {resultado.confianza*100:.1f}%")
    print(f"Mensaje: {resultado.mensaje}")
    
    # Preparar para API
    api_data = auth_system.prepare_for_api(resultado)
    print(f"\nDatos para API: {api_data}")


if __name__ == "__main__":
    main()