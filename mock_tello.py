import time
import cv2
import threading
import numpy as np
import math

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
        
        # Velocities
        self.vx = 0.0
        self.vy = 0.0
        self.vz = 0.0
        self.vyaw = 0.0
        
        # Simulation thread
        self.sim_running = True
        self.last_time = time.time()
        self.lock = threading.Lock()
        
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
            self.vx = left_right_velocity * 2.0 
            self.vy = forward_backward_velocity * 2.0
            self.vz = up_down_velocity * 1.0
            self.vyaw = yaw_velocity * 1.0 
        
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
                    self.yaw += self.vyaw * dt
                    self.yaw %= 360
                    
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
                    
            time.sleep(0.02) 

class MockFrameReader:
    def __init__(self, drone):
        self.drone = drone
        self.frame = None
        self.stopped = False
        self.lock = threading.Lock()
        
        # Load Assets
        self.background = cv2.imread('assets/background.png')
        self.person = cv2.imread('assets/person.png')
        
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
                # 1. Generate Ground View (Rotated Map)
                view_width = 640
                view_height = 480
                scale = 1.0
                
                cx, cy = int(self.drone.x), int(self.drone.y)
                
                # Rotate background map around drone
                # Note: If drone yaws right (positive), the world rotates left (negative) relative to camera
                M = cv2.getRotationMatrix2D((cx, cy), self.drone.yaw, scale)
                
                # Warp the background only (no person yet)
                rotated_map = cv2.warpAffine(self.background, M, (self.background.shape[1], self.background.shape[0]))
                
                x1 = cx - view_width // 2
                y1 = cy - view_height // 2
                x2 = x1 + view_width
                y2 = y1 + view_height
                
                # Crop camera view
                try:
                    if x1 < 0 or y1 < 0 or x2 > rotated_map.shape[1] or y2 > rotated_map.shape[0]:
                         self.frame = np.zeros((view_height, view_width, 3), dtype=np.uint8)
                    else:
                        self.frame = rotated_map[y1:y2, x1:x2]
                except:
                    self.frame = np.zeros((view_height, view_width, 3), dtype=np.uint8)

                # 2. Render Person (Billboard Style - Always Upright)
                # Calculate person position relative to drone
                px, py = self.person_pos
                dx, dy = self.drone.x, self.drone.y
                
                # Vector from drone to person
                vx = px - dx
                vy = py - dy
                
                # Rotate vector by -yaw to get local camera coordinates
                # Global: +x Right, +y Down
                # Camera: +x Right, +y Down (but Forward is Up in map? No, Forward is -y in map)
                # Let's stick to map coords:
                # Drone Heading is `yaw`. 0 is North (-y).
                # We want to project (vx, vy) onto the Drone's Right/Forward axes.
                
                rad_yaw = math.radians(self.drone.yaw)
                c = math.cos(rad_yaw)
                s = math.sin(rad_yaw)
                
                # Local X (Right):  vx * cos(yaw) + vy * sin(yaw)
                # Local Y (Forward): -vx * sin(yaw) + vy * cos(yaw)  <-- Wait, let's verify
                # If yaw=0 (North): Right=(1,0), Forward=(0,-1).
                # local_x = vx*1 + vy*0 = vx. Correct.
                # local_y = -vx*0 + vy*1 = vy. (So +y is Down/Back). 
                # Camera view: Top of screen is Forward. Bottom is Back.
                # So screen_y should be related to -local_y.
                
                local_x = (vx * c) + (vy * s)
                local_y = (-vx * s) + (vy * c) # This is "Map Y" relative to drone. + is Down/Back. - is Up/Forward.
                
                # Convert to Screen Coordinates
                # Center of screen is (view_width/2, view_height/2) which corresponds to (0,0) local
                screen_cx = view_width // 2
                screen_cy = view_height // 2
                
                dest_x = int(screen_cx + local_x)
                dest_y = int(screen_cy + local_y)
                
                # Check if person is roughly in front/visible
                # local_y is "Map Y". Forward is negative.
                # So if local_y is negative, person is in front.
                # if local_y is positive, person is behind.
                
                # Calculate distance for perspective scaling
                # local_y is "Map Y" relative to drone. + is Down/Back. - is Up/Forward.
                # Distance is roughly abs(local_y) if centered, or sqrt(local_x^2 + local_y^2)
                dist = math.sqrt(local_x**2 + local_y**2)
                
                # Avoid division by zero
                if dist < 10: dist = 10
                
                # Perspective projection: size = base_size * (focal_length / distance)
                focal_length = 400.0 # Adjust for FOV
                scale_factor = focal_length / dist
                
                # Base size of person in world units (pixels in map)
                # Let's say person is 100 units tall in map
                base_h = 100
                
                # Calculate dimensions preserving aspect ratio
                ph, pw, _ = self.person.shape
                aspect_ratio = pw / ph
                
                draw_h = int(base_h * scale_factor)
                draw_w = int(draw_h * aspect_ratio)
                
                # Render person sprite centered at dest_x, dest_y
                if self.person is not None and draw_w > 0 and draw_h > 0:
                    # Resize sprite to calculated perspective size
                    person_resized = cv2.resize(self.person, (draw_w, draw_h))
                    
                    ph, pw, _ = person_resized.shape
                    # Top-left of sprite
                    sx = dest_x - pw // 2
                    sy = dest_y - ph // 2
                    
                    # Clip and Paste
                    y1, y2 = max(0, sy), min(view_height, sy+ph)
                    x1, x2 = max(0, sx), min(view_width, sx+pw)
                    
                    if y2 > y1 and x2 > x1:
                        src_y1 = y1 - sy
                        src_y2 = src_y1 + (y2 - y1)
                        src_x1 = x1 - sx
                        src_x2 = src_x1 + (x2 - x1)
                        
                        self.frame[y1:y2, x1:x2] = person_resized[src_y1:src_y2, src_x1:src_x2]

                if self.frame is not None:
                     cv2.putText(self.frame, f"Sim: x={int(self.drone.x)} y={int(self.drone.y)} yaw={int(self.drone.yaw)}", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 1)

            time.sleep(0.03)
                
    def get_frame(self):
        with self.lock:
            return self.frame
            
    def stop(self):
        self.stopped = True
