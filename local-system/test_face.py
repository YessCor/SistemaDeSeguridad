#!/usr/bin/env python3
"""
Script de prueba para el sistema de reconocimiento facial.
Este script prueba las funciones principales sin necesidad de camara real.
"""

import sys
import numpy as np

print("=" * 60)
print("PRUEBA DEL SISTEMA DE RECONOCIMIENTO FACIAL")
print("=" * 60)

# Test 1: Verificar OpenCV
print("\n[1] Verificando OpenCV...")
try:
    import cv2
    print("    [OK] OpenCV version: {}".format(cv2.__version__))
except ImportError as e:
    print("    [ERROR] Error: {}".format(e))
    sys.exit(1)

# Test 2: Verificar MediaPipe
print("\n[2] Verificando MediaPipe...")
try:
    import mediapipe as mp
    print("    [OK] MediaPipe instalado")
except ImportError as e:
    print("    [ERROR] Error: {}".format(e))
    sys.exit(1)

# Test 3: Verificar face_recognition
print("\n[3] Verificando face_recognition...")
try:
    import face_recognition
    print("    [OK] face_recognition instalado")
except ImportError as e:
    print("    [WARN] Advertencia: {}".format(e))
    print("    (El sistema usara MediaPipe para deteccion facial)")

# Test 4: Probar FaceAuthSystem
print("\n[4] Probando FaceAuthSystem...")
try:
    from core.face_auth_system import FaceAuthSystem, AuthState
    
    # Crear instancia
    auth_system = FaceAuthSystem(camera_index=0, show_video=False)
    print("    [OK] FaceAuthSystem creado")
    print("    [OK] Camara index: {}".format(auth_system.camera_index))
    print("    [OK] Tolerancia facial: {}".format(auth_system.FACE_TOLERANCE))
    print("    [OK] Parpadeos requeridos: {}".format(auth_system.BLINKS_REQUIRED))
    print("    [OK] Umbral blink: {}".format(auth_system.BLINK_THRESHOLD))
except Exception as e:
    print("    [ERROR] Error: {}".format(e))

# Test 5: Probar calculos de EAR
print("\n[5] Probando calculo de EAR (Eye Aspect Ratio)...")
try:
    from core.face_auth_system import FaceAuthSystem
    
    auth_system = FaceAuthSystem(show_video=False)
    
    # Crear landmarks simulados de ojo abierto
    open_eye = np.array([
        [0.0, 3.0],
        [1.0, 2.0],
        [1.0, 2.0],
        [4.0, 3.0],
        [1.0, 2.0],
        [1.0, 2.0],
    ], dtype=np.float64)
    
    # Crear landmarks simulados de ojo cerrado
    closed_eye = np.array([
        [0.0, 3.0],
        [1.0, 3.0],
        [1.0, 3.0],
        [4.0, 3.0],
        [1.0, 3.0],
        [1.0, 3.0],
    ], dtype=np.float64)
    
    # Crear array de landmarks vacio
    landmarks = np.zeros((468, 3), dtype=np.float64)
    
    # Indices de ojos de MediaPipe
    LEFT_EYE = [33, 133, 160, 158, 153, 144]
    RIGHT_EYE = [362, 263, 387, 385, 380, 373]
    
    # Asignar puntos de ojo izquierdo (abierto)
    for i, idx in enumerate(LEFT_EYE):
        landmarks[idx] = open_eye[i]
    
    # Asignar puntos de ojo derecho (abierto)
    for i, idx in enumerate(RIGHT_EYE):
        landmarks[idx] = open_eye[i]
    
    ear = auth_system.calculate_ear(landmarks)
    print("    [OK] Ojo abierto - EAR: {:.3f}".format(ear))
    
    # Cerrar ojos
    for i, idx in enumerate(LEFT_EYE):
        landmarks[idx] = closed_eye[i]
    for i, idx in enumerate(RIGHT_EYE):
        landmarks[idx] = closed_eye[i]
    
    ear_closed = auth_system.calculate_ear(landmarks)
    print("    [OK] Ojo cerrado - EAR: {:.3f}".format(ear_closed))
    
    if ear > ear_closed:
        print("    [OK] El sistema detecta correctamente ojos abiertos vs cerrados")
    
except Exception as e:
    print("    [ERROR] Error: {}".format(e))
    import traceback
    traceback.print_exc()

# Test 6: Probar detector de rostros (con mocks)
print("\n[6] Probando deteccion de rostros (simulada)...")
try:
    # Crear frame de prueba
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    print("    [OK] Frame de prueba creado: {}".format(frame.shape))
    
    # Intentar detectar rostros
    from core.face_auth_system import FaceAuthSystem
    auth_system = FaceAuthSystem(show_video=False)
    
    # Esto intentara usar la camara, lo cual puede fallar
    if auth_system.open_camera():
        print("    [OK] Camara abierta")
        frame = auth_system.capture_frame()
        if frame is not None:
            result = auth_system.detect_face(frame)
            if result:
                print("    [OK] Rostro detectado")
            else:
                print("    [INFO] No se detecto rostro (esperado sin cara en frame vacio)")
        else:
            print("    [INFO] No se pudo capturar frame")
        auth_system.close_camera()
    else:
        print("    [INFO] No se puede abrir camara (no hay camara o esta en uso)")
        
except Exception as e:
    print("    [INFO] Error al probar camara: {}".format(e))

# Test 7: Cargar usuarios de ejemplo
print("\n[7] Probando carga de usuarios...")
try:
    from core.face_auth_system import FaceAuthSystem
    
    auth_system = FaceAuthSystem(show_video=False)
    
    # Crear usuario de ejemplo
    test_users = [
        {"id": 1, "nombre": "Usuario Prueba", "encoding": np.random.rand(128).tolist()}
    ]
    
    count = auth_system.load_users(test_users)
    print("    [OK] Usuarios cargados: {}".format(count))
    
    # Verificar reconocimiento
    test_encoding = np.random.rand(128)
    nombre, confianza = auth_system.recognize_face_with_name(test_encoding)
    print("    [OK] Reconocimiento simulado: {} (confianza: {:.2f})".format(nombre, confianza))
    
except Exception as e:
    print("    [ERROR] Error: {}".format(e))

print("\n" + "=" * 60)
print("RESUMEN DE PRUEBAS")
print("=" * 60)
print("""
Para probar el sistema completo con camara:

1. Ejecutar modo autenticacion:
   cd local-system
   python main.py

2. Ejecutar modo registro:
   python main.py --mode register --nombre "TuNombre" --email "tu@email.com"

3. Panel de pruebas web (requiere backend):
   - Inicia el backend con la URL del archivo .env
   - Abre: http://localhost:3000/api/test-panel.html

4. Tests unitarios (requiere instalar dlib):
   pip install cmake
   pip install dlib face-recognition
   pytest tests/ -v
""")
