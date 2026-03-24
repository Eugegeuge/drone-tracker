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

# Importar el controlador matemático centralizado
try:
    from pid_controller import PIDController
except ImportError:
    print("WARNING: pid_controller.py no encontrado. Asegúrate de ejecutar desde la raíz del repo.")
    import sys; sys.exit(1)

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
        
        # 1. Cargar YOLO (Modelo de Pose para detectar el torso y esqueleto humano)
        print("Cargando modelo YOLOv8n-Pose...")
        self.yolo_model = YOLO('yolov8n-pose.pt') 
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
        
        # Gimbal de la cámara
        self.camera_pitch_motor = self.getDevice("camera pitch")
        self.camera_roll_motor = self.getDevice("camera roll")
        
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
        
        # Contadores para optimizar
        self.step_counter = 0
        self.yolo_freq = 5 # Solo ejecutar YOLO cada 5 steps para evitar lag
        self.last_key = -1 # Para evitar spam de botones
        
        # Parámetros Tracking PID de Visión
        self.center_threshold = 30
        self.area_target = 25000
        
        # Instanciar Controladores Matemáticos Independientes (P, I, D)
        # Separa la lógica matemática de la simulación.
        self.yaw_pid = PIDController(kp=0.005, kd=0.002)
        self.pitch_pid = PIDController(kp=0.00003, kd=0.00002)
        self.alt_pid = PIDController(kp=0.0005, kd=0.001)
        
    def process_camera(self, roll_velocity=0.0, pitch_velocity=0.0):
        # Solo procesar imagen y YOLO cada N steps para evitar lag en el control físico
        if self.step_counter % self.yolo_freq != 0:
            return

        # Leer imagen de Webots
        img_raw = self.camera.getImage()
        if not img_raw:
            return

        img_array = np.frombuffer(img_raw, np.uint8)
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
        best_keypoints = None
        max_area = 0

        for result in results:
            if not result.boxes or not hasattr(result, 'keypoints') or result.keypoints is None:
                continue
                
            for box, kpts in zip(result.boxes, result.keypoints.data):
                # Filtro Estricto: Persona y Confianza > 70%
                if int(box.cls[0]) == 0 and float(box.conf[0]) > 0.70:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    area = (x2-x1) * (y2-y1)
                    if area > max_area:
                        max_area = area
                        best_person = (x1, y1, x2, y2)
                        best_keypoints = kpts
                        
        self.auto_yaw_disturbance = 0.0
        self.auto_pitch_disturbance = 0.0
        self.auto_roll_disturbance = 0.0
        
        if best_person and best_keypoints is not None:
            x1, y1, x2, y2 = best_person
            
            # Intentar usar el punto medio de los hombros (Torso superior) para estabilidad
            px, py = (x1 + x2) // 2, (y1 + y2) // 2
            try:
                # Keypoints YOLOv8 Pose: 5=Left Shoulder, 6=Right Shoulder
                ls = best_keypoints[5]
                rs = best_keypoints[6]
                if ls[2] > 0.4 and rs[2] > 0.4:
                    px = int((ls[0] + rs[0]) / 2.0)
                    py = int((ls[1] + rs[1]) / 2.0)
                    cv2.circle(frame, (px, py), 6, (0, 0, 255), -1)
            except Exception:
                pass # Si el tensor no tiene la forma esperada, caemos en el centro de la BB
            
            error_x = px - center_x
            error_y = center_y - py # Positivo si persona está por encima del centro
            error_area = self.area_target - max_area # Positivo: muy lejos. Negativo: muy cerca.
            
            # Dibujar siempre si hay detección sólida
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, "PERSONA ESTABLE", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            if self.auto_mode:
                # ----------------
                # 1. PID de Yaw (Giro para centrar X)
                # ----------------
                self.auto_yaw_disturbance = -self.yaw_pid.compute(error_x) # Invertido según ejes simulador
                
                if abs(error_x) < self.center_threshold:
                    self.auto_yaw_disturbance = 0.0
                else:
                    self.auto_yaw_disturbance = max(-1.3, min(1.3, self.auto_yaw_disturbance))
                    
                # ----------------
                # 2. PID de Altura (Modificar Target Altitude)
                # ----------------
                alt_correction = self.alt_pid.compute(error_y)
                if abs(error_y) > 40: # Zona muerta vertical
                    self.target_altitude += max(-0.05, min(0.05, alt_correction))
                    
                # ----------------
                # 3. PID de Pitch (Avanzar/Retroceder según área)
                # ----------------
                self.auto_pitch_disturbance = -self.pitch_pid.compute(error_area) # Pitch neg = Avance
                
                if abs(error_area) < 5000: # Tolerancia de tamaño
                    self.auto_pitch_disturbance = 0.0
                else:
                    self.auto_pitch_disturbance = max(-1.0, min(1.0, self.auto_pitch_disturbance))
                
                info_text = f"AUTO: P {self.auto_pitch_disturbance:.2f} | Y {self.auto_yaw_disturbance:.2f}"
                cv2.putText(frame, info_text, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)
            else:
                cv2.putText(frame, "PRESIONA 'M' PARA AUTO-TRACKING", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,0), 1)
            
        # Dibujar HUD
        mode_text = "MODO: AUTO (YOLO)" if self.auto_mode else "MODO: MANUAL (WASD)"
        cv2.putText(frame, mode_text, (10, height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

        cv2.imshow("Webots YOLO Tracker", frame)
        cv2.waitKey(1) # Volvemos a 1ms porque solo entra aquí cada 5 steps
        
    def run(self):
        # Display the welcome message.
        print("Start the drone...")

        # Wait one second.
        while self.step(self.time_step) != -1:
            if self.getTime() > 1.0:
                break

        # Display manual control message.
        print("You can control the drone with your computer keyboard:")
        print("- 'up': move forward.")
        print("- 'down': move backward.")
        print("- 'right': turn right.")
        print("- 'left': turn left.")
        print("- 'shift + up': increase the target altitude.")
        print("- 'shift + down': decrease the target altitude.")
        print("- 'shift + right': strafe right.")
        print("- 'shift + left': strafe left.")
        print("- 'M': Toggle AUTO Mode (YOLO).")

        # Variables.
        self.target_altitude = 1.0  # The target altitude. Can be changed by the user.

        # Main loop
        while self.step(self.time_step) != -1:
            time_val = self.getTime()

            # Retrieve robot position using the sensors.
            roll, pitch, _ = self.imu.getRollPitchYaw()
            gps_values = self.gps.getValues()
            altitude = gps_values[2]
            roll_velocity, pitch_velocity, _ = self.gyro.getValues()

            # Blink the front LEDs alternatively with a 1 second rate.
            led_state = int(time_val) % 2
            if hasattr(self, 'front_left_led') and self.front_left_led:
                self.front_left_led.set(led_state)
            if hasattr(self, 'front_right_led') and self.front_right_led:
                self.front_right_led.set(not led_state)

            # Stabilize the Camera by actuating the camera motors according to the gyro feedback.
            if self.camera_roll_motor:
                self.camera_roll_motor.setPosition(-0.115 * roll_velocity)
            if self.camera_pitch_motor:
                self.camera_pitch_motor.setPosition(-0.1 * pitch_velocity)

            # 4. Transform the keyboard input to disturbances on the stabilization algorithm.
            PITCH_TRIM = 0.03 # Ajuste fino para contrarrestar la tendencia a avanzar
            roll_disturbance = 0.0
            pitch_disturbance = PITCH_TRIM
            yaw_disturbance = 0.0
            
            key = self.keyboard.getKey()
            while key > 0:
                if key == Keyboard.UP:
                    pitch_disturbance = -2.0
                elif key == Keyboard.DOWN:
                    pitch_disturbance = 2.0
                elif key == Keyboard.RIGHT:
                    yaw_disturbance = -1.3
                elif key == Keyboard.LEFT:
                    yaw_disturbance = 1.3
                elif key == (Keyboard.SHIFT + Keyboard.RIGHT):
                    roll_disturbance = -1.0
                elif key == (Keyboard.SHIFT + Keyboard.LEFT):
                    roll_disturbance = 1.0
                elif key == (Keyboard.SHIFT + Keyboard.UP):
                    self.target_altitude += 0.05
                    print(f"target altitude: {self.target_altitude:.2f} [m]")
                elif key == (Keyboard.SHIFT + Keyboard.DOWN):
                    self.target_altitude -= 0.05
                    print(f"target altitude: {self.target_altitude:.2f} [m]")
                elif key == ord('M'):
                    if key != self.last_key:
                        self.auto_mode = not self.auto_mode
                        print(f"AUTO MODE: {'ON' if self.auto_mode else 'OFF'}")
                
                self.last_key = key
                key = self.keyboard.getKey()

            # Procesar YOLO y cámara
            self.process_camera(roll_velocity=roll_velocity, pitch_velocity=pitch_velocity)
            self.step_counter += 1
            
            # Si estamos en AUTO, YOLO sobreescribe las perturbaciones
            if self.auto_mode:
                roll_disturbance = self.auto_roll_disturbance
                pitch_disturbance = self.auto_pitch_disturbance
                yaw_disturbance = self.auto_yaw_disturbance

            # Compute the roll, pitch, yaw and vertical inputs.
            roll_input = K_ROLL_P * max(-1.0, min(1.0, roll)) + roll_velocity + roll_disturbance
            pitch_input = K_PITCH_P * max(-1.0, min(1.0, pitch)) + pitch_velocity + pitch_disturbance
            yaw_input = yaw_disturbance
            clamped_difference_altitude = max(-1.0, min(1.0, self.target_altitude - altitude + K_VERTICAL_OFFSET))
            vertical_input = K_VERTICAL_P * pow(clamped_difference_altitude, 3.0)

            # Actuate the motors taking into consideration all the computed inputs.
            front_left_motor_input = K_VERTICAL_THRUST + vertical_input - roll_input + pitch_input - yaw_input
            front_right_motor_input = K_VERTICAL_THRUST + vertical_input + roll_input + pitch_input + yaw_input
            rear_left_motor_input = K_VERTICAL_THRUST + vertical_input - roll_input - pitch_input + yaw_input
            rear_right_motor_input = K_VERTICAL_THRUST + vertical_input + roll_input - pitch_input - yaw_input

            self.front_left_motor.setVelocity(front_left_motor_input)
            self.front_right_motor.setVelocity(-front_right_motor_input)
            self.rear_left_motor.setVelocity(-rear_left_motor_input)
            self.rear_right_motor.setVelocity(rear_right_motor_input)

if __name__ == '__main__':
    controller = WebotsYOLOTracker()
    controller.run()
