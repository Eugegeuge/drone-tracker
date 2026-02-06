import cv2
from ultralytics import YOLO
import time
import numpy as np

# --- Configuration ---
USE_MOCK = True  # Set to False to use real Tello

if USE_MOCK:
    class MockDrone:
        def __init__(self):
            print("[MockDrone] Initialized")
            self.is_flying = False
            self.battery = 100

        def connect(self):
            print("[MockDrone] Connected")

        def takeoff(self):
            print("[MockDrone] Takeoff!")
            self.is_flying = True

        def land(self):
            print("[MockDrone] Landing!")
            self.is_flying = False

        def send_rc_control(self, lr, fb, ud, yv):
            # Log command if it's non-zero
            if lr != 0 or fb != 0 or ud != 0 or yv != 0:
                print(f"[CMD] LR: {lr}, FB: {fb}, UD: {ud}, YAW: {yv}")

        def get_battery(self):
            return self.battery
            
        def streamon(self):
             pass
        def streamoff(self):
             pass

    Tello = MockDrone
else:
    from djitellopy import Tello

class DroneController:
    def __init__(self):
        # 1. Initialize YOLO
        print("Loading YOLO model...")
        self.model = YOLO('yolov8n.pt')
        print("Model loaded.")

        # 2. Initialize Drone interface
        self.drone = Tello()
        
        # COMANDO: connect()
        # Envía el comando "command" al dron.
        # Es NECESARIO para que el dron entre en modo SDK y acepte instrucciones.
        # También verifica que haya conexión WiFi con el dron.
        self.drone.connect()
        
        # 3. Initialize Webcam
        # We ALWAYS use webcam for this version as requested
        print("Opening Webcam...")
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("Error: Could not open webcam.")
            return

        # Control Parameters
        self.center_threshold = 50  # Pixels from center to trigger movement
        self.area_min = 30000       # Target Area (Distance)
        self.area_max = 60000
        self.max_speed = 50
        
        # PID Gains (Simple P)
        self.kp_yaw = 0.3
        self.kp_ud = 0.4
        self.kp_fb = 0.4

        self.is_flying = False # We will simulate this locally for logic

    def clamp(self, value, min_val, max_val):
        return max(min(value, max_val), min_val)

    def process_frame(self, frame):
        results = self.model(frame, verbose=False)
        
        height, width, _ = frame.shape
        center_x, center_y = width // 2, height // 2
        
        # Draw Center Crosshair
        cv2.line(frame, (center_x - 10, center_y), (center_x + 10, center_y), (255, 255, 0), 1)
        cv2.line(frame, (center_x, center_y - 10), (center_x, center_y + 10), (255, 255, 0), 1)

        best_person = None
        max_area = 0

        # Find largest person
        for result in results:
            for box in result.boxes:
                cls = int(box.cls[0])
                if self.model.names[cls] == 'person':
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    area = (x2 - x1) * (y2 - y1)
                    if area > max_area:
                        max_area = area
                        best_person = (x1, y1, x2, y2)

        # Control Logic
        lr, fb, ud, yv = 0, 0, 0, 0
        status_text = "SEARCHING"

        if best_person:
            status_text = "TRACKING"
            x1, y1, x2, y2 = best_person
            px, py = (x1 + x2) // 2, (y1 + y2) // 2
            
            # Draw Face Box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.circle(frame, (px, py), 5, (0, 255, 0), -1)
            
            # Calculate Errors
            error_x = px - center_x
            error_y = py - center_y
            
            # 1. Yaw (Rotate to center X)
            if abs(error_x) > self.center_threshold:
                yv = int(error_x * self.kp_yaw)
                
            # 2. Up/Down (Center Y)
            # Image Y is positive DOWN. Tello Up is positive.
            # If person is below center (+error_y), we go DOWN (-speed)
            if abs(error_y) > self.center_threshold:
                ud = int(-error_y * self.kp_ud)

            # 3. Forward/Back (Distance/Area)
            if max_area < self.area_min:
                fb = 20 # Move Forward
            elif max_area > self.area_max:
                fb = -20 # Move Backward
                
            # Clamp Speeds
            lr = self.clamp(lr, -self.max_speed, self.max_speed)
            fb = self.clamp(fb, -self.max_speed, self.max_speed)
            ud = self.clamp(ud, -self.max_speed, self.max_speed)
            yv = self.clamp(yv, -self.max_speed, self.max_speed) 

            # Display Stats
            stats = f"ErrX:{error_x} ErrY:{error_y} Area:{max_area}"
            cv2.putText(frame, stats, (10, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # Send Commands
        # We always send if flying OR if mocked (to see output)
        if self.is_flying or USE_MOCK:
            # COMANDO: send_rc_control(left_right, forward_backward, up_down, yaw)
            # Envía velocidades en los 4 ejes al dron.
            # Valores: -100 a 100.
            # lr: Izquierda (-)/Derecha (+)
            # fb: Atrás (-)/Adelante (+)
            # ud: Abajo (-)/Arriba (+)
            # yv: Girar Izq (-)/Girar Der (+)
            self.drone.send_rc_control(lr, fb, ud, yv)
            
        # Draw HUD
        cv2.putText(frame, f"MODE: {'FLYING' if self.is_flying else 'LANDED'}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.putText(frame, f"STATUS: {status_text}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        return frame

    def run(self):
        print("Controls: 't' Takeoff, 'l' Land, 'q' Quit")
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("Failed to grab frame")
                break
                
            processed_frame = self.process_frame(frame)
            cv2.imshow("Webcam Tracker", processed_frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('t'):
                # COMANDO: takeoff()
                # Envía orden de despegue automático.
                # El dron sube a 1.2 metros y se mantiene en "hover".
                self.drone.takeoff()
                self.is_flying = True
            elif key == ord('l'):
                # COMANDO: land()
                # Envía orden de aterrizaje automático.
                # El dron desciende lentamente hasta tocar el suelo y apaga motores.
                self.drone.land()
                self.is_flying = False
                
        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    controller = DroneController()
    controller.run()
