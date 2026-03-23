import time
import cv2
import threading
import numpy as np
import math
import os

# Get the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')

class MockTello:
    def __init__(self):
        self.is_flying = False
        self.battery = 100
        self.frame_read = None
        
        # Physics State
        self.x = 1000.0 # Start in middle of map
        self.y = 1000.0
        self.z = 100.0  # Height
        self.yaw = 0.0  # Degrees
        
        # Physics Constants
        self.drag = 0.1  # Drag coefficient (0-1)
        self.accel_factor = 30.0 # Force applied by RC commands
        self.max_physics_speed = 150.0

        # Simulation thread
        self.sim_running = True
        self.last_time = time.time()
        self.lock = threading.Lock()
        
        # New: Target movement params
        self.auto_person_move = True
        self.person_theta = 0.0 # For circular movement
        
        self.sim_thread = threading.Thread(target=self.update_physics)
        self.sim_thread.daemon = True
        self.sim_thread.start()

    def connect(self):
        print("[MockTello] Connecting to drone...")
        time.sleep(1)
        print("[MockTello] Connected! Battery: {}%".format(self.battery))
        return True
        
    def takeoff(self):
        print("[MockTello] Taking off...")
        time.sleep(2)
        self.is_flying = True
        self.z = 100.0
        print("[MockTello] Takeoff complete.")
        
    def land(self):
        print("[MockTello] Landing...")
        time.sleep(2)
        self.is_flying = False
        self.z = 0.0
        print("[MockTello] Landed.")
        
    def streamon(self):
        print("[MockTello] Video stream started.")
        self.frame_read = MockFrameReader(self)
        
    def streamoff(self):
        print("[MockTello] Video stream stopped.")
        if self.frame_read:
            self.frame_read.stop()
            
    def get_frame_read(self):
        return self.frame_read
        
    def send_rc_control(self, left_right_velocity, forward_backward_velocity, up_down_velocity, yaw_velocity):
        with self.lock:
            # We treat these as "Target Forces" or "Thrust"
            self.target_vx = left_right_velocity * self.accel_factor
            self.target_vy = forward_backward_velocity * self.accel_factor
            self.target_vz = up_down_velocity * 0.5
            self.vyaw = yaw_velocity * 2.0 
        
    def get_battery(self):
        return self.battery
        
    def set_person_pos(self, x, y):
        if self.frame_read:
            self.frame_read.set_person_pos(x, y)

    def get_map_draw(self):
        if self.frame_read:
            return self.frame_read.get_map_draw()
        return None

    def update_physics(self):
        while self.sim_running:
            current_time = time.time()
            dt = current_time - self.last_time
            self.last_time = current_time
            
            if self.is_flying:
                with self.lock:
                    # 1. Update Rotation
                    self.yaw += self.vyaw * dt
                    self.yaw %= 360
                    
                    # 2. Apply Acceleration & Drag (Simple Euler)
                    # accel = (Thrust - Drag * velocity)
                    self.vx += (self.target_vx - self.vx * self.drag) * dt
                    self.vy += (self.target_vy - self.vy * self.drag) * dt
                    self.vz += (self.target_vz - self.vz * self.drag) * dt
                    
                    # Clamp max speed
                    self.vx = max(-self.max_physics_speed, min(self.max_physics_speed, self.vx))
                    self.vy = max(-self.max_physics_speed, min(self.max_physics_speed, self.vy))
                    
                    # 3. Translate Position
                    rad_yaw = math.radians(self.yaw)
                    c = math.cos(rad_yaw)
                    s = math.sin(rad_yaw)
                    
                    global_vx = (self.vx * c) + (self.vy * s)
                    global_vy = (self.vx * s) - (self.vy * c)
                    
                    self.x += global_vx * dt
                    self.y += global_vy * dt
                    self.z += self.vz * dt
                    
                    self.x = max(0, min(2000, self.x))
                    self.y = max(0, min(2000, self.y))

                    # 4. Update Autonomous Person Movement
                    if self.auto_person_move:
                        self.person_theta += 0.5 * dt # Speed of circle
                        radius = 400
                        px = 1000 + radius * math.cos(self.person_theta)
                        py = 1000 + radius * math.sin(self.person_theta * 0.7) # Figure 8 ish
                        self.set_person_pos(px, py)
                    
            time.sleep(0.01) # Higher frequency for physics

from collections import deque

class MockFrameReader:
    def __init__(self, drone):
        self.drone = drone
        self.latest_frame = None
        self.frame_buffer = deque()
        self.latency_seconds = 0.2 # 200ms default latency (characteristic of Tello WiFi)
        self.stopped = False
        self.lock = threading.Lock()
        
        # Load Assets
        self.background = cv2.imread(os.path.join(ASSETS_DIR, 'background.png'))
        self.person = cv2.imread(os.path.join(ASSETS_DIR, 'person.png'))
        
        if self.person is not None:
            self.person = cv2.resize(self.person, (200, 200)) 
        
        self.person_pos = (1000, 850) 
        
        # Start background thread
        self.t = threading.Thread(target=self.update, args=())
        self.t.daemon = True
        self.t.start()
        
    def set_person_pos(self, x, y):
        with self.lock:
            # Center the person sprite on the click
            ph, pw, _ = self.person.shape
            self.person_pos = (x - pw//2, y - ph//2)

    def get_map_draw(self):
        # Return the map with overlays (Drone + Person) for visualization
        with self.lock:
            display_map = self.background.copy()
            
            # Draw Person
            px, py = self.person_pos
            ph, pw, _ = self.person.shape
            
            # Safe paste
            y1, y2 = max(0, py), min(display_map.shape[0], py+ph)
            x1, x2 = max(0, px), min(display_map.shape[1], px+pw)
            
            # Calculate source offsets if cropped
            sy1 = max(0, -py)
            sy2 = sy1 + (y2 - y1)
            sx1 = max(0, -px)
            sx2 = sx1 + (x2 - x1)
            
            if y2 > y1 and x2 > x1:
                 display_map[y1:y2, x1:x2] = self.person[sy1:sy2, sx1:sx2]
            
            # Draw Drone
            dx, dy = int(self.drone.x), int(self.drone.y)
            cv2.circle(display_map, (dx, dy), 20, (0, 0, 255), -1) # Red dot for drone
            
            # Draw Heading
            rad_yaw = math.radians(self.drone.yaw)
            end_x = int(dx + 50 * math.sin(rad_yaw)) # +x is right, yaw 0 is up? No, yaw 0 is up (North)
            end_y = int(dy - 50 * math.cos(rad_yaw)) # -y is up
            
            # Wait, my physics math:
            # 0 deg (Up): c=1, s=0. global_vy = -vy. Forward moves UP. Correct.
            # So heading line for 0 deg should be UP.
            # sin(0)=0, cos(0)=1. end_x = dx, end_y = dy - 50. Correct.
            
            cv2.arrowedLine(display_map, (dx, dy), (end_x, end_y), (0, 0, 255), 2)
            
            # Draw FOV (approximate)
            # +/- 30 degrees
            fov = 30
            rad_left = math.radians(self.drone.yaw - fov)
            rad_right = math.radians(self.drone.yaw + fov)
            
            lx = int(dx + 100 * math.sin(rad_left))
            ly = int(dy - 100 * math.cos(rad_left))
            rx = int(dx + 100 * math.sin(rad_right))
            ry = int(dy - 100 * math.cos(rad_right))
            
            cv2.line(display_map, (dx, dy), (lx, ly), (0, 255, 255), 1)
            cv2.line(display_map, (dx, dy), (rx, ry), (0, 255, 255), 1)
            
            return display_map

    def update(self):
        while not self.stopped:
            with self.lock:
                # [Same image generation logic as before...]
                # [Skipping repeat to keep chunk small, just updating how we store it]
                new_frame = self.generate_synthetic_frame() 
                
                # Timestamp the frame and add to buffer
                self.frame_buffer.append((time.time(), new_frame))
                
                # Cleanup old frames (keep at least 1)
                now = time.time()
                while len(self.frame_buffer) > 1 and (now - self.frame_buffer[0][0]) > self.latency_seconds:
                    _, self.latest_frame = self.frame_buffer.popleft()

            time.sleep(0.03)

    def generate_synthetic_frame(self):
        # Move the large logic from original update() here
        # (This is a refactor to accommodate the latency buffer)
        view_width = 640
        view_height = 480
        scale = 1.0
        
        cx, cy = int(self.drone.x), int(self.drone.y)
        M = cv2.getRotationMatrix2D((cx, cy), self.drone.yaw, scale)
        rotated_map = cv2.warpAffine(self.background, M, (self.background.shape[1], self.background.shape[0]))
        
        x1 = cx - view_width // 2
        y1 = cy - view_height // 2
        x2 = x1 + view_width
        y2 = y1 + view_height
        
        try:
            if x1 < 0 or y1 < 0 or x2 > rotated_map.shape[1] or y2 > rotated_map.shape[0]:
                 temp_frame = np.zeros((view_height, view_width, 3), dtype=np.uint8)
            else:
                temp_frame = rotated_map[y1:y2, x1:x2].copy()
        except:
            temp_frame = np.zeros((view_height, view_width, 3), dtype=np.uint8)

        # Render Person
        px, py = self.person_pos
        dx, dy = self.drone.x, self.drone.y
        vx, vy = px - dx, py - dy
        rad_yaw = math.radians(self.drone.yaw)
        c, s = math.cos(rad_yaw), math.sin(rad_yaw)
        local_x = (vx * c) + (vy * s)
        local_y = (-vx * s) + (vy * c)
        
        screen_cx, screen_cy = view_width // 2, view_height // 2
        dest_x, dest_y = int(screen_cx + local_x), int(screen_cy + local_y)
        dist = math.sqrt(local_x**2 + local_y**2)
        if dist < 10: dist = 10
        focal_length = 400.0
        scale_factor = focal_length / dist
        base_h = 100
        ph, pw, _ = self.person.shape
        aspect_ratio = pw / ph
        draw_h, draw_w = int(base_h * scale_factor), int(base_h * scale_factor * aspect_ratio)
        
        if self.person is not None and draw_w > 0 and draw_h > 0:
            person_resized = cv2.resize(self.person, (draw_w, draw_h))
            ph, pw, _ = person_resized.shape
            sx, sy = dest_x - pw // 2, dest_y - ph // 2
            y1, y2 = max(0, sy), min(view_height, sy+ph)
            x1, x2 = max(0, sx), min(view_width, sx+pw)
            if y2 > y1 and x2 > x1:
                src_y1, src_x1 = y1 - sy, x1 - sx
                src_y2, src_x2 = src_y1 + (y2 - y1), src_x1 + (x2 - x1)
                temp_frame[y1:y2, x1:x2] = person_resized[src_y1:src_y2, src_x1:src_x2]

        cv2.putText(temp_frame, f"Sim Latency: {int(self.latency_seconds*1000)}ms", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 1)
        return temp_frame
                
    def get_frame(self):
        with self.lock:
            return self.latest_frame
            
    def stop(self):
        self.stopped = True
