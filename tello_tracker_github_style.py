import sys
print("\n--- INICIANDO SCRIPT DE TRACKING ---", flush=True)
print("> Cargando librerías (OpenCV, PyTorch/YOLO... esto puede tardar unos segundos)...", flush=True)

import cv2
from ultralytics import YOLO
import time
print("> Librerías cargadas con éxito.", flush=True)

from pid_controller import PIDController

# --- Configuration ---
USE_MOCK = False  # Cambia a False para usar el dron real Tello

if USE_MOCK:
    from mock_tello import MockTello
    Tello = MockTello
else:
    from djitellopy import Tello

class Tracker24M:
    def __init__(self):
        print("Cargando modelo YOLO (Pose) para detectar nariz y tracking...")
        # Usamos el modelo de pose para tener los keypoints (0 = nariz)
        self.model = YOLO('yolov8n-pose.pt')
        
        self.drone = Tello()
        self.drone.connect()
        
        print("Iniciando video...")
        self.drone.streamon()
        if USE_MOCK:
            self.frame_reader = self.drone.get_frame_read()
        else:
            self.frame_reader = self.drone.get_frame_read()

        # ==========================================
        # --- Configuration ---
        self.VISION_ONLY_MODE = False
        self.DRY_RUN_AUTOPILOT = False  # <--- VUELO AUTONÓMICO REAL ACTIVADO
        # ==========================================

        # --- Variables de Tracker ---
        self.override_cc = 0
        self.override_ud = 0
        self.override_fb = 0
        self.override_lr = 0
        
        self.tracking_enabled = False
        self.is_flying = False

        self.pid_yaw = PIDController(0.15, 0.1, 0.1)  # Giro muy suave
        self.pid_ud = PIDController(0.2, 0.05, 0.1)   # Ajuste Vertical muy lento y estable
        self.pid_fb = PIDController(0.3, 0.05, 0.1)   # Avance/Retroceso más amortiguado
        
        self.center_threshold = 20
        # --- NUEVOS PARÁMETROS DE DISTANCIA REAL ---
        self.KNOWN_HEAD_TO_SHOULDER_CM = 18.0  # Media nariz a línea de hombros (cm)
        self.FOCAL_LENGTH_PX = 950.0           # Focal estimada del Tello a 720p
        self.target_dist_m = 1.1               # Distancia deseada en metros (Subido para evitar perder FOV)
        
        # Píxeles objetivo basados en la distancia real en metros
        self.target_dist_px = (self.FOCAL_LENGTH_PX * self.KNOWN_HEAD_TO_SHOULDER_CM) / (self.target_dist_m * 100)
        self.dist_margin = 15
        self.max_height_cm = 230
        
        # ID de Tracking
        self.target_id = None

    def clamp(self, value, limit):
        return max(min(int(value), limit), -limit)

    def run(self):
        print("\nControles:")
        if self.VISION_ONLY_MODE:
            print(" ---- MODO SÓLO VISIÓN ACTIVADO ----")
            print(" ESC     : Salir\n")
        else:
            print(" ESPACIO : Despegar")
            print(" L       : Aterrizar")
            print(" T       : Activar/Desactivar Tracker Automático")
            print(" W/S/A/D : Adelante/Atras/Izquierda/Derecha")
            print(" Q/E     : Rotar Izquierda/Derecha")
            print(" R       : Volver a Hover manual")
            print(" ESC     : Salir\n")
        
        last_time = time.time()
        first_frame_ack = False
        print("\nEsperando flujo de video del Tello...", flush=True)
        
        while True:
            # Obtener frame
            if USE_MOCK:
                frame = self.frame_reader.get_frame()
                if frame is None:
                    time.sleep(0.01)
                    continue
            else:
                frame = self.frame_reader.frame
                if frame is None:
                    time.sleep(0.01)
                    continue
                # ARREGLO DE COLORES: Tello devuelve RGB, OpenCV usa BGR.
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            if not first_frame_ack:
                print("¡VIDEO RECIBIDO! Abriendo ventana de tracking...", flush=True)
                first_frame_ack = True

            height, width, _ = frame.shape
            center_x, center_y = width // 2, height // 2
            target_y = int(height * 0.35) # Punto objetivo más arriba (35% desde arriba, aprox 2/3 hacia arriba)

            # Dibujamos una pequeña cruceta roja indicando el PUNTO OBJETIVO
            cv2.line(frame, (center_x - 10, target_y), (center_x + 10, target_y), (0, 0, 255), 2)
            cv2.line(frame, (center_x, target_y - 10), (center_x, target_y + 10), (0, 0, 255), 2)

            # Deteccion con persistencia usando track() y filtrando por persona (clase 0)
            # YOLOv8-pose detectará a la persona e intentará mantener un ID
            results = self.model.track(frame, persist=True, verbose=False, classes=[0])
            
            best_person_box = None
            best_person_nose = None
            best_person_dist = 0
            max_area = 0

            # Analizar resultados
            for result in results:
                # Si no detectó personas ignoramos
                if result.boxes is None or result.boxes.id is None:
                    continue
                
                boxes = result.boxes.xyxy.cpu().numpy()
                track_ids = result.boxes.id.cpu().numpy()
                
                # Para obtener keypoints si existen
                if result.keypoints is not None:
                    keypoints = result.keypoints.xy.cpu().numpy()
                else:
                    keypoints = [None] * len(boxes)

                # Busca si nuestro target_id aún está en escena
                target_found_this_frame = False
                
                # Si no teníamos target, o lo hemos perdido temporalmente, escogemos la caja más grande
                if self.target_id not in track_ids:
                    # Encontrar el area máxima para asignar nuevo ID
                    for box, track_id, kp in zip(boxes, track_ids, keypoints):
                        x1, y1, x2, y2 = map(int, box)
                        area = (x2 - x1) * (y2 - y1)
                        if area > max_area and kp is not None:
                            max_area = area
                            self.target_id = track_id
                
                # Una vez conocemos nuestro target_id (antiguo o nuevo), sacamos sus datos
                for box, track_id, kp in zip(boxes, track_ids, keypoints):
                    if track_id == self.target_id and kp is not None:
                        x1, y1, x2, y2 = map(int, box)
                        area = (x2 - x1) * (y2 - y1)
                        max_area = area
                        
                        # Extraer Nariz (Keypoint 0 es nariz en mmpose/COCO)
                        nose_x, nose_y = kp[0]
                        
                        # Extraer Nariz (Keypoint 0)
                        nose_x, nose_y = kp[0]
                        
                        # CALCULO DE DISTANCIA (Depth) -> Nariz a Hombros (como en Github)
                        dist_px = 0
                        if len(kp) >= 7:
                            ls_y = kp[5][1] # Left Shoulder Y
                            rs_y = kp[6][1] # Right Shoulder Y
                            if ls_y > 0 and rs_y > 0:
                                mean_shoulder_y = (ls_y + rs_y) / 2.0
                                dist_px = mean_shoulder_y - nose_y
                        
                        if nose_x > 0 and nose_y > 0:
                            best_person_box = (x1, y1, x2, y2)
                            best_person_nose = (int(nose_x), int(nose_y))
                            best_person_dist = dist_px
                            
                            # CÁLCULO DE DISTANCIA REAL (cm -> m)
                            if dist_px > 0:
                                self.last_dist_m = (self.FOCAL_LENGTH_PX * self.KNOWN_HEAD_TO_SHOULDER_CM) / (dist_px * 100.0)
                            else:
                                self.last_dist_m = 0
                            
                            target_found_this_frame = True
                        break
            
            # Dibujamos en pantalla al target
            if best_person_box and best_person_nose:
                x1, y1, x2, y2 = best_person_box
                nx, ny = best_person_nose
                
                # Rectángulo principal de color llamativo (Azul/Cian)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 0), 2)
                # Punto amarillo en la nariz
                cv2.circle(frame, (nx, ny), 6, (0, 215, 255), -1)
                
                # Mostrar ID y Distancia Real (Metros) ---
                label_id = f"PERSONA ID: {int(self.target_id)}"
                label_dist = f"DISTANCIA ESTIMADA: {self.last_dist_m:.2f} m"
                
                # Fondo para legibilidad
                cv2.rectangle(frame, (x1, y1 - 45), (x1 + 320, y1), (255, 255, 0), -1)
                cv2.putText(frame, label_id, (x1 + 5, y1 - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
                cv2.putText(frame, label_dist, (x1 + 5, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

            curr_time = time.time()
            dt = curr_time - last_time
            if dt <= 0: dt = 0.01
            last_time = curr_time

            # --- CÁLCULO DE TRACKING Y PID (Siempre se ejecuta para saber qué haría) ---
            auto_yv, auto_ud, auto_fb = 0, 0, 0

            if self.tracking_enabled and best_person_box and best_person_nose:
                # Usamos la NARIZ para X, Y y compensación
                nx, ny = best_person_nose

                error_x = nx - center_x
                error_y = ny - target_y 

                # 1) YAW (Girar basado en X de la nariz)
                if abs(error_x) > self.center_threshold:
                    auto_yv = self.clamp(self.pid_yaw.compute(error_x, dt), 40) # Límite max a 40 para giros suaves
                else:
                    self.pid_yaw.reset_integral()

                # 2) UP/DOWN (Subir/Bajar basado en Y de la nariz)
                if abs(error_y) > 20: # Margen amplio para evitar que una respiración haga moverse al dron
                    auto_ud = self.clamp(self.pid_ud.compute(-error_y, dt), 25) # Maximo de 25 para evitar escaladas bruscas
                else:
                    self.pid_ud.reset_integral()

                # 3) FORWARD/BACKWARD (Acercar/Alejar basado en la distancia NARIZ-HOMBROS)
                if best_person_dist > 0:
                    if self.smoothed_dist_px == 0.0:
                        self.smoothed_dist_px = best_person_dist
                    else:
                        self.smoothed_dist_px = (0.2 * best_person_dist) + (0.8 * self.smoothed_dist_px)

                    error_fb = self.target_dist_px - self.smoothed_dist_px
                    if abs(error_fb) > self.dist_margin:
                        auto_fb = self.clamp(self.pid_fb.compute(error_fb, dt), 30) # Límite max a 30 para acercarse/alejarse suavemente
                    else:
                        self.pid_fb.reset_integral()
                else:
                    self.smoothed_dist_px = 0.0
                    self.pid_fb.reset_integral()
            else:
                self.smoothed_dist_px = 0.0
                self.pid_yaw.reset_integral()
                self.pid_ud.reset_integral()
                self.pid_fb.reset_integral()

            if self.DRY_RUN_AUTOPILOT and self.tracking_enabled:
                # Mostrar intenciones de vuelo en pantalla
                y_intent = "CENTRO"
                if auto_yv > 0: y_intent = "GIRAR DERECHA   -->"
                elif auto_yv < 0: y_intent = "<--   GIRAR IZQUIERDA"

                fb_intent = "MANTENIENDO DISTANCIA"
                if auto_fb > 0: fb_intent = ">>> AVANZAR >>>"
                elif auto_fb < 0: fb_intent = "<<< RETROCEDER <<<"

                cv2.rectangle(frame, (10, 85), (400, 140), (0, 0, 0), -1)
                cv2.putText(frame, f"INTENCION YAW: {y_intent} (vel: {auto_yv})", (10, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
                cv2.putText(frame, f"INTENCION DISTANCIA: {fb_intent} (vel: {auto_fb})", (10, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
                
                # Si estamos en modo Dry Run, NO aplicamos la velocidad automática, permitimos manual
                final_yv = self.override_cc
                final_ud = self.override_ud
                final_fb = self.override_fb
                final_lr = self.override_lr
            else:
                final_yv = auto_yv if self.tracking_enabled else self.override_cc
                final_ud = auto_ud if self.tracking_enabled else self.override_ud
                final_fb = auto_fb if self.tracking_enabled else self.override_fb
                final_lr = 0       if self.tracking_enabled else self.override_lr
                
                # Renderizar indicación de Hover cuando perdemos al target real
                if self.tracking_enabled and not best_person_box:
                    cv2.putText(frame, "TARGET PERDIDO -> HOVERING", (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 3)

            if USE_MOCK:
                current_z = getattr(self.drone, 'z', 0)
                battery = getattr(self.drone, 'battery', 100)
            else:
                try:
                    # El barómetro (get_height) falla mucho en interiores y da medidas erróneas.
                    # El sensor infrarrojo inferior (TOF) es muy preciso hasta los 3 metros.
                    current_z = self.drone.get_distance_tof()
                    battery = self.drone.get_battery()
                except:
                    current_z = 0
                    battery = 0

            limiter_active = False
            if current_z >= self.max_height_cm:
                if final_ud > 0:
                    final_ud = 0
                    limiter_active = True

            if self.is_flying or USE_MOCK:
                self.drone.send_rc_control(
                    int(final_lr), int(final_fb), int(final_ud), int(final_yv)
                )

            # --- DIBUJOS COMUNES AL HUD ---
            mode_desc = "AUTO TRACKING (DRY RUN)" if (self.tracking_enabled and self.DRY_RUN_AUTOPILOT) else ("AUTO TRACKING (REAL)" if self.tracking_enabled else "MODO MANUAL")
            cv2.putText(frame, mode_desc, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0) if not self.DRY_RUN_AUTOPILOT else (0,255,0), 2)
            cv2.putText(frame, f"Alt: {current_z:.1f} cm | Bat: {battery}%", (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            
            if limiter_active:
                cv2.putText(frame, "LIMITE ALTURA ALCANZADO (2.4m)", (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # HUD Prominente para la altura actual
            cv2.rectangle(frame, (10, height - 50), (320, height - 10), (0, 0, 255), -1)
            cv2.putText(frame, f"ALTURA DEL DRONE: {current_z:.1f} cm", (20, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # --- Tareas Comunes ---
            cv2.imshow("Github Style Tracker", frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == 27: # ESC
                print("Exiting...")
                break
            elif key == ord('k'):
                # Resetear el ID forzosamente en caso de bloquearse con la persona equivocada (bonus)
                self.target_id = None
            
            if not self.VISION_ONLY_MODE:
                if key == ord(' '):
                    try:
                        print(f"Intentando despegar...")
                        self.drone.takeoff()
                        self.is_flying = True
                    except Exception as e:
                        print(f"\n[ERROR DE DESPEGUE] {e}\n")
                elif key == ord('l'): 
                    self.drone.land()
                    self.tracking_enabled = False
                    self.is_flying = False
                elif key == ord('t'):
                    self.tracking_enabled = not self.tracking_enabled
                    self.override_cc = self.override_ud = self.override_fb = self.override_lr = 0
                elif key == ord('w'): self.override_fb = 40
                elif key == ord('s'): self.override_fb = -40
                elif key == ord('a'): self.override_lr = -40
                elif key == ord('d'): self.override_lr = 40
                elif key == ord('q'): self.override_cc = -40
                elif key == ord('e'): self.override_cc = 40
                elif key == ord('8'): self.override_ud = 40
                elif key == ord('2'): self.override_ud = -40
                elif key == ord('r'):
                    self.override_cc = self.override_ud = self.override_fb = self.override_lr = 0

        self.drone.streamoff()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    t = Tracker24M()
    t.run()
