"""
Controlador de Webots para seguimiento de personas con YOLO.
Diseñado para el modelo DJI Mavic 2 Pro de Webots.
"""

import os
import sys
import platform

# --- AUTO CONFIGURACION DE WEBOTS PARA WINDOWS ---
if 'WEBOTS_HOME' not in os.environ:
    # Ruta por defecto de Webots en Windows
    os.environ['WEBOTS_HOME'] = "C:\\Program Files\\Webots"

webots_home = os.environ['WEBOTS_HOME']
python_path = os.path.join(webots_home, 'lib', 'controller', 'python')

if python_path not in sys.path:
    sys.path.append(python_path)

if platform.system() == 'Windows':
    # Añadir rutas de DLLs requeridas por la API de C de Webots
    dll_dir = os.path.join(webots_home, 'msys64', 'mingw64', 'bin')
    cpp_dir = os.path.join(webots_home, 'msys64', 'mingw64', 'bin', 'cpp')
    
    os.environ['PATH'] = f"{dll_dir};{cpp_dir};" + os.environ.get('PATH', '')
    if hasattr(os, 'add_dll_directory'):
        try:
            os.add_dll_directory(dll_dir)
            os.add_dll_directory(cpp_dir)
        except OSError:
            pass # Falla silenciosa si las carpetas no existen o Webots no está ahí

try:
    from controller import Robot, Keyboard
except ImportError:
    print("\n[!] ERROR CRITICO: No se ha podido cargar la librería de Webots.")
    print(f"Me he asegurado de buscar en: {webots_home}")
    print("Verifica que Webots esté instalado correctamente en 'C:\\Program Files\\Webots'.\n")
    sys.exit(1)

import cv2
import numpy as np
import time
import numpy as np
import time
try:
    from ultralytics import YOLO
except ImportError:
    print("Error: ultralytics no está instalado. Ejecuta: pip install ultralytics")
    exit(1)

# --- CONFIGURACION PID ESTABILIZACION (Drone de Webots) ---
# Constantes básicas extraidas de la simulación del Mavic de Webots
K_VERTICAL_THRUST = 68.5
K_VERTICAL_OFFSET = 0.6
K_VERTICAL_P = 3.0
K_ROLL_P = 50.0
K_PITCH_P = 30.0

class WebotsYOLOTracker(Robot):
    def __init__(self):
        super().__init__()
        self.time_step = int(self.getBasicTimeStep())
        
        # 1. Cargar YOLO
        print("Cargando modelo YOLOv8n...")
        self.yolo_model = YOLO('yolov8n.pt')
        print("YOLO listo.")

        # 2. Configurar Sensores del Dron
        self.camera = self.getDevice("camera")
        self.camera.enable(self.time_step)
        
        self.imu = self.getDevice("inertial unit")
        self.imu.enable(self.time_step)
        
        self.gps = self.getDevice("gps")
        self.gps.enable(self.time_step)
        
        self.gyro = self.getDevice("gyro")
        self.gyro.enable(self.time_step)
        
        # 3. Configurar Motores
        self.front_left_motor = self.getDevice("front left propeller")
        self.front_right_motor = self.getDevice("front right propeller")
        self.rear_left_motor = self.getDevice("rear left propeller")
        self.rear_right_motor = self.getDevice("rear right propeller")
        
        motors = [self.front_left_motor, self.front_right_motor, self.rear_left_motor, self.rear_right_motor]
        for m in motors:
            m.setPosition(float('inf')) # Velocidad infinita para control por velocidad
            m.setVelocity(1.0) # Empieza despacio
            
        # Teclado para controles manuales
        self.keyboard = Keyboard()
        self.keyboard.enable(self.time_step)

        # 4. Estado del Vuelo y Tracking
        self.target_altitude = 0.0 # Objetivo de altura
        self.target_yaw = 0.0      # Offset de rotación
        self.target_pitch = 0.0    # Adelante/Atrás
        self.is_flying = False
        
        # ParámetrosTracking PID de Visión
        self.center_threshold = 30
        self.area_target = 25000
        
    def process_camera(self):
        # Leer imagen de Webots
        img_array = np.frombuffer(self.camera.getImage(), np.uint8)
        # Convertir bgra a bgr
        img = img_array.reshape((self.camera.getHeight(), self.camera.getWidth(), 4))
        frame = img[:, :, :3]
        
        height, width, _ = frame.shape
        center_x, center_y = width // 2, height // 2
        
        results = self.yolo_model(frame, verbose=False)
        
        best_person = None
        max_area = 0
        
        for result in results:
            for box in result.boxes:
                if int(box.cls[0]) == 0: # 0 = person en COCO
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    area = (x2-x1) * (y2-y1)
                    if area > max_area:
                        max_area = area
                        best_person = (x1, y1, x2, y2)
                        
        self.target_yaw = 0.0
        self.target_pitch = 0.0
        
        if best_person and self.is_flying:
            x1, y1, x2, y2 = best_person
            px, py = (x1 + x2) // 2, (y1 + y2) // 2
            
            error_x = px - center_x
            error_y = center_y - py # Positivo si está por encima del centro de la pantalla
            
            # Ajuste de Yaw (Rotar hacia la persona)
            if abs(error_x) > self.center_threshold:
                # Si error_x > 0 (derecha), queremos girar a la derecha
                self.target_yaw = -2.0 if error_x > 0 else 2.0
                
            # Ajuste de Altura
            if error_y > 30:
                self.target_altitude += 0.05
            elif error_y < -30:
                self.target_altitude -= 0.05
                
            # Ajuste de Pitch (Avanzar/Retroceder)
            if max_area < self.area_target - 5000:
                self.target_pitch = -0.25 # Avanzar
            elif max_area > self.area_target + 5000:
                self.target_pitch = 0.25 # Retroceder
                
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"Area: {max_area} | Pitch: {self.target_pitch} | Yaw: {self.target_yaw}", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)
            print(f"> OBJETIVO DETECTADO < Área: {max_area}. Pitch: {self.target_pitch}, Yaw: {self.target_yaw}")
            
        else:
             # Si no hay nadie, quedarse quieto
             if self.is_flying:
                 cv2.putText(frame, "BUSCANDO PERSONA...", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 1)

        cv2.imshow("Webots YOLO Tracker", frame)
        cv2.waitKey(1)
        
    def run(self):
        print("Iniciando Simulador. Pulsa 't' (en Webots) para despegar, 'l' para aterrizar.")
        
        while self.step(self.time_step) != -1:
            # 1. Leer teclado
            key = self.keyboard.getKey()
            if key == ord('T'): # Despegar
                self.is_flying = True
                self.target_altitude = 1.2
                print("Despegando en Webots...")
            elif key == ord('L'): # Aterrizar
                self.is_flying = False
                self.target_altitude = 0.0
                print("Aterrizando...")
                
            # 2. Leer Sensores de Estabilización
            roll, pitch, yaw = self.imu.getRollPitchYaw()
            altitude = self.gps.getValues()[1] # Asumiendo mundo donde Y o Z es arriba (Webots 2023+ usa Z para arriba, algunos dir usan Y)
            # Para Mavic, Z suele ser altura. Ajustamos si hace falta.
            gps_z = self.gps.getValues()[2] 
            
            # 3. Procesar Cámara y YOLO (cada X ms para no saturar)
            self.process_camera()
            
            # 4. Estabilizar Dron (PID Físico)
            roll_velocity, pitch_velocity, yaw_velocity = self.gyro.getValues()
            
            # Control de Altura (Clamping a tierra si aterrizado)
            if not self.is_flying and gps_z < 0.1:
                motor_base = 0.0
            else:
                altitude_error = self.target_altitude - gps_z
                motor_base = K_VERTICAL_THRUST + K_VERTICAL_P * altitude_error

            # Ajustes PID Estabilización Base vs Targets de Visión
            roll_input = K_ROLL_P * (self.target_roll if hasattr(self, 'target_roll') else 0.0 - roll) + roll_velocity
            pitch_input = K_PITCH_P * (self.target_pitch - pitch) + pitch_velocity
            yaw_input = self.target_yaw
            
            # Mezclador de motores (Quadrotor en X)
            m1 = motor_base - roll_input + pitch_input + yaw_input # Delantero Izq
            m2 = motor_base + roll_input + pitch_input - yaw_input # Delantero Der
            m3 = motor_base - roll_input - pitch_input - yaw_input # Trasero Izq
            m4 = motor_base + roll_input - pitch_input + yaw_input # Trasero Der
            
            # Aplicar potencias
            self.front_left_motor.setVelocity(self._clamp(m1))
            self.front_right_motor.setVelocity(self._clamp(m2))
            self.rear_left_motor.setVelocity(self._clamp(m3))
            self.rear_right_motor.setVelocity(self._clamp(m4))

    def _clamp(self, val):
        MAX_SPEED = 600.0 # Mavic max speed constraint
        return max(-MAX_SPEED, min(MAX_SPEED, val))

if __name__ == '__main__':
    controller = WebotsYOLOTracker()
    controller.run()
