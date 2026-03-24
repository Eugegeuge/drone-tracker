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
# Constantes OFICIALES de Webots para el Mavic 2 Pro
K_VERTICAL_THRUST = 68.5   # Con este valor el dron flota
K_VERTICAL_OFFSET = 0.6
K_VERTICAL_P = 3.0
K_ROLL_P = 50.0
K_PITCH_P = 30.0

class WebotsYOLOTracker(Robot):
    def __init__(self):
        super().__init__()
        self.time_step = int(self.getBasicTimeStep())
        
        # 1. Cargar YOLO (Puedes probar 'yolov8s.pt' si el 'n' es poco preciso)
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
        
        # Gimbal de la cámara (Asegurar que mire al frente)
        self.camera_pitch_motor = self.getDevice("camera pitch")
        if self.camera_pitch_motor:
            self.camera_pitch_motor.setPosition(0.7) # Inclinación ligera hacia abajo
        
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
        self.target_altitude = 1.0 # Altitud por defecto (como en el C)
        self.target_yaw = 0.0      
        self.target_pitch = 0.0    
        self.target_roll = 0.0     
        self.is_flying = False
        self.auto_mode = False     
        
        # Parámetros Tracking PID de Visión
        self.center_threshold = 30
        self.area_target = 25000
        
    def process_camera(self):
        # Leer imagen de Webots
        img_array = np.frombuffer(self.camera.getImage(), np.uint8)
        # Webots suele ser BGRA en Windows. Si ves los colores mal (ej. rojos en azul),
        # cambia la siguiente línea por: frame = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2RGB)
        img = img_array.reshape((self.camera.getHeight(), self.camera.getWidth(), 4))
        frame = img[:, :, :3].copy()
        
        # Debug visual: si no ves nada, mira si estos valores son 0
        if self.getTime() % 2.0 < 0.05:
            mean_val = np.mean(frame)
            print(f"[DEBUG VISION] Frame: {frame.shape} | Brillo medio: {mean_val:.1f}")
        
        height, width, _ = frame.shape
        center_x, center_y = width // 2, height // 2
        
        results = self.yolo_model(frame, verbose=False)
        
        best_person = None
        max_area = 0
        
        # Verbose: Ver qué está viendo YOLO realmente
        detected_names = [result.names[int(box.cls[0])] for result in results for box in result.boxes]
        if detected_names:
            print(f"YOLO ve: {detected_names}")

        for result in results:
            for box in result.boxes:
                if int(box.cls[0]) == 0: # 0 = person en COCO
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    area = (x2-x1) * (y2-y1)
                    if area > max_area:
                        max_area = area
                        best_person = (x1, y1, x2, y2)
                        
        self.auto_yaw_disturbance = 0.0
        self.auto_pitch_disturbance = 0.0
        self.auto_roll_disturbance = 0.0
        
        if best_person and self.is_flying:
            x1, y1, x2, y2 = best_person
            px, py = (x1 + x2) // 2, (y1 + y2) // 2
            
            error_x = px - center_x
            error_y = center_y - py # Positivo si está por encima del centro de la pantalla
            
            # Dibujar siempre si hay detección
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, "PERSONA", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

            if self.auto_mode:
                # Ajuste de Yaw (Hacia el centro en X)
                if abs(error_x) > self.center_threshold:
                    # En el C oficial, yaw_disturbance es aprox +-1.3 para girar rápido
                    self.auto_yaw_disturbance = -1.3 if error_x > 0 else 1.3
                    
                # Ajuste de Altura (Modificamos el target_altitude)
                if error_y > 40:
                    self.target_altitude += 0.05
                elif error_y < -40:
                    self.target_altitude -= 0.05
                    
                # Ajuste de Pitch (Avanzar/Retroceder)
                if max_area < self.area_target - 5000:
                    self.auto_pitch_disturbance = -0.5 # Avanzar (Negative in C is forward)
                elif max_area > self.area_target + 5000:
                    self.auto_pitch_disturbance = 0.5 # Retroceder
                
                info_text = f"AUTO: Pitch {self.auto_pitch_disturbance} | Yaw {self.auto_yaw_disturbance}"
                cv2.putText(frame, info_text, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)
                print(f"> TRACKING AUTO < Área: {max_area}. Pitch Dist: {self.auto_pitch_disturbance}, Yaw Dist: {self.auto_yaw_disturbance}")
            else:
                cv2.putText(frame, "PRESIONA 'M' PARA AUTO-TRACKING", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,0), 1)
            
        # Dibujar HUD
        mode_text = "MODO: AUTO (YOLO)" if self.auto_mode else "MODO: MANUAL (WASD)"
        cv2.putText(frame, mode_text, (10, height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

        cv2.imshow("Webots YOLO Tracker", frame)
        cv2.waitKey(5)
        
    def run(self):
        print("\n--- CONTROLES DEL SIMULADOR ---")
        print("T: Despegar / Toggle AUTO Mode")
        print("L: Aterrizar")
        print("Manual: W/S (Avanzar), A/D (Lados), Q/E (Girar), Flechas Arriba/Abajo (Altura)")
        print("-------------------------------\n")
        
        while self.step(self.time_step) != -1:
            # 1. Leer teclado y definir perturbaciones (como en el C oficial)
            key = self.keyboard.getKey()
            roll_disturbance = 0.0
            pitch_disturbance = 0.0
            yaw_disturbance = 0.0

            if key != -1:
                # Log opcional para debug: print(f"Tecla: {key}")
                pass

            if key == ord('T'): 
                self.is_flying = not self.is_flying
                print(f"ESTADO: {'VUELO' if self.is_flying else 'TIERRA'}")
            elif key == ord('M'): # M para alternar AUTO
                self.auto_mode = not self.auto_mode
                print(f"MODO AUTO: {'ON' if self.auto_mode else 'OFF'}")
            elif key == ord('L'):
                self.is_flying = False
                print("ESTADO: Aterrizaje forzado")

            # Control Manual mapeado a perturbaciones (WASD + Arrows)
            if self.is_flying and not self.auto_mode:
                if key == ord('W') or key == Keyboard.UP:    pitch_disturbance = -2.0
                if key == ord('S') or key == Keyboard.DOWN:  pitch_disturbance = 2.0
                if key == ord('D') or key == Keyboard.RIGHT: yaw_disturbance = -1.3
                if key == ord('A') or key == Keyboard.LEFT:  yaw_disturbance = 1.3
                if key == ord('Q'): roll_disturbance = 1.0  # Bank Left
                if key == ord('E'): roll_disturbance = -1.0 # Bank Right
                # Altura
                if key == ord('U'): self.target_altitude += 0.05
                if key == ord('J'): self.target_altitude -= 0.05

            # 2. Leer Sensores
            roll, pitch, yaw = self.imu.getRollPitchYaw()
            gps_values = self.gps.getValues()
            gps_z = gps_values[2] # Altura en Mavic
            roll_velocity, pitch_velocity, yaw_velocity = self.gyro.getValues()
            
            # 3. Procesar Cámara y YOLO
            self.process_camera()
            
            # Si estamos en AUTO, YOLO sobreescribe las perturbaciones manuales
            if self.auto_mode and self.is_flying:
                roll_disturbance = self.auto_roll_disturbance
                pitch_disturbance = self.auto_pitch_disturbance
                yaw_disturbance = self.auto_yaw_disturbance

            # 4. Estabilizar Dron (PID FÍSICO Oficial)
            clamped_diff = max(-1.0, min(1.0, self.target_altitude - gps_z + K_VERTICAL_OFFSET))
            vertical_input = K_VERTICAL_P * pow(clamped_diff, 3.0)
            
            roll_input = K_ROLL_P * max(-1.0, min(1.0, roll - self.target_roll)) + roll_velocity + roll_disturbance
            pitch_input = K_PITCH_P * max(-1.0, min(1.0, pitch - self.target_pitch)) + pitch_velocity + pitch_disturbance
            yaw_input = yaw_disturbance
            
            # Mezclador (Mavic 2 Pro)
            if not self.is_flying and gps_z < 0.2:
                m1 = m2 = m3 = m4 = 0.0
            else:
                m1 = K_VERTICAL_THRUST + vertical_input - roll_input + pitch_input - yaw_input
                m2 = K_VERTICAL_THRUST + vertical_input + roll_input + pitch_input + yaw_input
                m3 = K_VERTICAL_THRUST + vertical_input - roll_input - pitch_input + yaw_input
                m4 = K_VERTICAL_THRUST + vertical_input + roll_input - pitch_input - yaw_input
            
            # Aplicar potencias (Motores 2 y 3 invertidos)
            self.front_left_motor.setVelocity(self._clamp(m1))
            self.front_right_motor.setVelocity(self._clamp(-m2))
            self.rear_left_motor.setVelocity(self._clamp(-m3))
            self.rear_right_motor.setVelocity(self._clamp(m4))

            # Debug de motores (solo si estamos intentando volar pero no sube)
            if self.is_flying and gps_z < 0.2 and self.getTime() % 2.0 < 0.1:
                print(f"[DEBUG MOTORES] FL={m1:.1f}, FR={m2:.1f}, RL={m3:.1f}, RR={m4:.1f}")

    def _clamp(self, val):
        MAX_SPEED = 600.0 # Volvemos al límite recomendado
        return max(-MAX_SPEED, min(MAX_SPEED, val))

if __name__ == '__main__':
    controller = WebotsYOLOTracker()
    controller.run()
