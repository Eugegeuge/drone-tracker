import cv2
import argparse
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
from typing import Tuple, Optional, Any
import os
import time

# Control manual avanzado
from pynput import keyboard

# Importación condicional para no crashear si el usuario de webcam no tiene instalado djitellopy
try:
    from djitellopy import Tello
except ImportError:
    Tello = None


class CameraConfig:
    PROFILES = {
        'webcam': {'focal_length': 600.0},
        'tello':  {'focal_length': 950.0}
    }
    S_REAL = 0.185  # Medida física real de la cara detectada (barbilla-cejas)
    MODEL_PATH = "face_detector.tflite"


# --- CONFIGURACIÓN CONTROL MANUAL (pynput) ---
MANUAL_SPEED = 50
keys_pressed = set()

def on_press(key):
    try:
        if hasattr(key, 'char') and key.char:
            keys_pressed.add(keyboard.KeyCode.from_char(key.char.lower()))
        else:
            keys_pressed.add(key)
    except Exception: pass

def on_release(key):
    try:
        if hasattr(key, 'char') and key.char:
            k = keyboard.KeyCode.from_char(key.char.lower())
            if k in keys_pressed: keys_pressed.remove(k)
        if key in keys_pressed: keys_pressed.remove(key)
    except Exception: pass

listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()

def get_manual_controls():
    lr, fb, ud, yv = 0, 0, 0, 0
    shift = any(k in keys_pressed for k in [keyboard.Key.shift, keyboard.Key.shift_r])
    
    if keyboard.Key.up in keys_pressed:
        if shift: ud = MANUAL_SPEED
        else: fb = MANUAL_SPEED
    if keyboard.Key.down in keys_pressed:
        if shift: ud = -MANUAL_SPEED
        else: fb = -MANUAL_SPEED
    if keyboard.Key.left in keys_pressed:
        if shift: lr = -MANUAL_SPEED
        else: yv = -MANUAL_SPEED
    if keyboard.Key.right in keys_pressed:
        if shift: lr = MANUAL_SPEED
        else: yv = MANUAL_SPEED
        
    return lr, fb, ud, yv


class DistanceEstimator:
    """
    Estima la distancia y la desviación en X e Y del rostro.
    """
    def __init__(self, alpha: float = 0.2, s_real: float = CameraConfig.S_REAL, model_path: str = CameraConfig.MODEL_PATH):
        self.alpha = alpha
        self.s_real = s_real
        self.ema_pixels: Optional[float] = None
        
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.FaceDetectorOptions(base_options=base_options)
        self.detector = vision.FaceDetector.create_from_options(options)

    def process_frame(self, frame: np.ndarray, focal_length: float) -> Tuple[np.ndarray, Optional[float], float, float]:
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        detection_result = self.detector.detect(mp_image)
        
        h, w, _ = frame.shape
        distance = None
        error_x = 0.0
        error_y = 0.0

        if detection_result.detections:
            detection = detection_result.detections[0]
            bbox = detection.bounding_box
            
            # Filtro EMA (Distancia)
            current_pixels = float(bbox.height)
            if self.ema_pixels is None:
                self.ema_pixels = current_pixels
            else:
                self.ema_pixels = (self.alpha * current_pixels) + ((1.0 - self.alpha) * self.ema_pixels)
                
            distance = (self.s_real * focal_length) / self.ema_pixels
            
            # --- CENTRADO GEOMÉTRICO (Calculo de desviación) ---
            face_cx = bbox.origin_x + bbox.width / 2.0
            face_cy = bbox.origin_y + bbox.height / 2.0
            
            target_cx = w / 2.0
            target_cy = h * 0.4  # Queremos la cabeza en el tercio superior (40% de altura)
            
            # Errores normalizados de -0.5 a +0.5
            error_x = (face_cx - target_cx) / w
            error_y = (face_cy - target_cy) / h
            
            # Pintar GUI
            cv2.rectangle(frame, (bbox.origin_x, bbox.origin_y), (bbox.origin_x + bbox.width, bbox.origin_y + bbox.height), (0, 255, 0), 2)
            cv2.circle(frame, (int(face_cx), int(face_cy)), 5, (0, 0, 255), -1) # Punto rojo en cabeza
            
            cv2.putText(frame, f"Distancia Z: {distance:.2f} m", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            cv2.putText(frame, f"Deriva X, Y: {error_x:.2f}, {error_y:.2f}", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        else:
            self.ema_pixels = None

        return frame, distance, error_x, error_y


def main():
    parser = argparse.ArgumentParser(description="Control HÍBRIDO PID + Teleop")
    parser.add_argument('--mode', type=str, choices=['webcam', 'tello'], default='webcam')
    args = parser.parse_args()

    if not os.path.exists(CameraConfig.MODEL_PATH):
        print(f"[ERROR] No se encontró el modelo {CameraConfig.MODEL_PATH}.")
        return

    focal_length = CameraConfig.PROFILES[args.mode]['focal_length']
    estimator = DistanceEstimator(alpha=0.3, s_real=CameraConfig.S_REAL)

    # ------------------ MODO WEBCAM ------------------
    if args.mode == 'webcam':
        cap = cv2.VideoCapture(0)
        print("[INFO] Modo WEBCAM inicializado. Presiona 'q' para salir.")
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            
            processed_frame, distance, ex, ey = estimator.process_frame(frame, focal_length)
            cv2.imshow("Drone Tracker - Tracker View", processed_frame)
            
            if cv2.waitKey(40) & 0xFF == ord('q'):
                break
        cap.release()
        cv2.destroyAllWindows()

    # ------------------ MODO TELLO ------------------
    elif args.mode == 'tello':
        if Tello is None: return

        tello = Tello()
        try:
            tello.connect()
            print(f"[INFO] Tello conectado con exito. Bateria: {tello.get_battery()}%")
            tello.streamon()
            
            print("=== DJ TELLO - TRACKER HIBRIDO ===")
            print("  't': Despegar")
            print("  'l': Aterrizar")
            print("  'm': Alternar MODO SEGUIMIENTO / MANUAL")
            print("  'Flechitas + Shift': Mover si estas en modo MANUAL")
            print("  'q' o 'ESC': Salida de emergencia y cerrar")
            print("==================================")
            
            frame_reader = tello.get_frame_read()
            
            # Máquina de estados
            is_flying = False
            auto_mode = False
            
            t_key = keyboard.KeyCode.from_char('t')
            l_key = keyboard.KeyCode.from_char('l')
            m_key = keyboard.KeyCode.from_char('m')
            
            # Anti-rebote para la tecla 'm'
            m_was_pressed = False

            while True:
                frame = frame_reader.frame
                if frame is None:
                    time.sleep(0.01)
                    continue
                    
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) 
                processed_frame, distance, ex, ey = estimator.process_frame(frame_bgr, focal_length)
                
                # --- CONTROL KEYBOARD GLOBAL (Pynput) ---
                if keyboard.Key.esc in keys_pressed:
                    break
                    
                if t_key in keys_pressed and not is_flying:
                    print("[INFO] Despegando...")
                    tello.takeoff()
                    is_flying = True
                    keys_pressed.remove(t_key)
                    
                if l_key in keys_pressed and is_flying:
                    print("[INFO] Aterrizando...")
                    # Forzamos parada
                    tello.send_rc_control(0,0,0,0)
                    tello.land()
                    is_flying = False
                    keys_pressed.remove(l_key)
                    
                if m_key in keys_pressed:
                    if not m_was_pressed: # Trigger en flanco de subida
                        auto_mode = not auto_mode
                        m_was_pressed = True
                        print(f"[*] Cambiado a Modo {'AUTO' if auto_mode else 'MANUAL'} !")
                else:
                    m_was_pressed = False

                # --- LÓGICA DE MOVIMIENTO ---
                lr, fb, ud, yv = 0, 0, 0, 0

                if is_flying:
                    if auto_mode:
                        # 1. PITCH (Forward/Back) -> Distancia objetivo 1.5m
                        if distance is not None:
                            error_dist = distance - 1.5
                            if abs(error_dist) > 0.2:
                                fb = max(-35, min(35, int(error_dist * 40)))
                        
                        # 2. YAW (Giro L/R) -> Centrar cara horizontalmente
                        # Si ex > 0, cara a la derecha, debe girar a la derecha (+yv)
                        if abs(ex) > 0.1:
                            yv = max(-45, min(45, int(ex * 80)))
                            
                        # 3. THROTTLE (Up/Down) -> Centrar cara verticalmente
                        # Si ey < 0, cara está en Y bajas (arriba visualmente), dron debe subir (+ud)
                        if abs(ey) > 0.1:
                            ud = max(-35, min(35, int(-ey * 80)))
                            
                        tello.send_rc_control(lr, fb, ud, yv)
                    else:
                        # Control manual teleop Webots
                        lr, fb, ud, yv = get_manual_controls()
                        tello.send_rc_control(lr, fb, ud, yv)
                else:
                    # En tierra (Safety)
                    tello.send_rc_control(0, 0, 0, 0)

                # --- HUD RENDERING ---
                bat_text = f"Bateria: {tello.get_battery()}%"
                cv2.putText(processed_frame, bat_text, (20, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
                
                # Suelo
                try: ground_dist = tello.get_distance_tof()
                except: ground_dist = "N/A"
                cv2.putText(processed_frame, f"Suelo: {ground_dist} cm", (20, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                
                # Modo y comandos
                mode_str = "AUTO" if auto_mode else "MANUAL"
                color = (0, 255, 0) if auto_mode else (0, 0, 255)
                cv2.putText(processed_frame, f"[{mode_str}] Velocidades FB:{fb} LR:{lr} UD:{ud} Y:{yv}", 
                            (20, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

                if auto_mode and distance is None:
                     cv2.putText(processed_frame, "¡BUSCANDO PERSONA - HOVER!", (20, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

                cv2.imshow("Drone Tracker - Tracker View", processed_frame)
                
                key = cv2.waitKey(40) & 0xFF
                if key == ord('q'):
                    print("[INFO] SALIDA DE EMERGENCIA...")
                    break
                    
        except Exception as e:
            print(f"[ERROR MODO TELLO]: {e}")
        finally:
            print("[INFO] Cerrando comunicaciones de Hardware...")
            try:
                tello.send_rc_control(0, 0, 0, 0)
                if is_flying: tello.land()
                tello.streamoff()
            except:
                pass
            cv2.destroyAllWindows()
            listener.stop()

if __name__ == "__main__":
    main()
