import time
import math
import numpy as np
import cv2
import threading
from collections import deque
import sys

from direct.showbase.ShowBase import ShowBase
from panda3d.core import AmbientLight, DirectionalLight
from panda3d.core import Vec3, Vec4, Point3
from panda3d.core import GraphicsOutput

class MockTello3D:
    def __init__(self):
        self.is_flying = False
        self.battery = 100
        self.frame_read = None
        
        # Physics State
        self.x = 0.0
        self.y = -10.0 # Start a bit back
        self.z = 1.2   # 1.2m height
        self.yaw = 0.0 # Degrees
        self.pitch = 0.0
        self.roll = 0.0
        
        # Target Forces (from RC)
        self.target_vx = 0.0
        self.target_vy = 0.0
        self.target_vz = 0.0
        self.target_vyaw = 0.0
        
        # Current Velocities
        self.vx = 0.0
        self.vy = 0.0
        self.vz = 0.0
        self.vyaw = 0.0
        
        # Physics Parameters
        self.drag = 2.0
        self.accel_factor = 0.1 # m/s^2 per RC unit
        self.max_speed = 5.0 # m/s
        
        self.lock = threading.Lock()
        
        # Initialize the 3D Engine in a separate thread
        self.engine_thread = threading.Thread(target=self._start_engine)
        self.engine_thread.daemon = True
        self.engine_thread.start()
        
        # Wait for engine to signal ready
        # In a real robust implementation we'd use Events, using sleep for simplicity
        time.sleep(2) 

    def _start_engine(self):
        from panda3d.core import loadPrcFileData
        # Force offscreen rendering explicitly
        loadPrcFileData("", "window-type offscreen")
        loadPrcFileData("", "win-size 640 480")
        self.app = DroneEngine(self)
        
        # Disable signal handlers that crash in background threads
        import panda3d.core as p3d
        p3d.ConfigVariableBool('abort-on-keyboard-interrupt').setValue(False)
        self.app.taskMgr.setupTaskChain('default', tickClock=True)
        # Hack to prevent step() from calling signal.signal
        class _DummySignal:
            def signal(self, *args, **kwargs): pass
        self.app.taskMgr.signal = _DummySignal()

        self.engine_ready = True
        
        # Custom loop to avoid signal issues in background thread
        try:
             while True:
                 # Panda3D taskMgr tries to import signal if it exists. We override it.
                 import direct.task.Task
                 direct.task.Task.signal = _DummySignal()
                 self.app.taskMgr.step()
                 time.sleep(0.001)
        except Exception as e:
            print("Engine stopped:", e)

    def connect(self):
        print("[MockTello3D] Connecting to 3D Drone...")
        time.sleep(1)
        # Wait until engine finishes loading
        while not hasattr(self, 'engine_ready'):
            time.sleep(0.1)
        print("[MockTello3D] Connected! Battery: {}%".format(self.battery))
        return True
        
    def takeoff(self):
        print("[MockTello3D] Taking off...")
        time.sleep(2)
        self.is_flying = True
        with self.lock:
            self.z = 1.2
        print("[MockTello3D] Takeoff complete.")
        
    def land(self):
        print("[MockTello3D] Landing...")
        time.sleep(2)
        self.is_flying = False
        with self.lock:
            self.z = 0.0
        print("[MockTello3D] Landed.")
        
    def send_rc_control(self, left_right_velocity, forward_backward_velocity, up_down_velocity, yaw_velocity):
        with self.lock:
            # We map RC commands [-100, 100] to target velocities/forces
            # Note Panda3D: Y is forward, X is right, Z is up
            self.target_vx = left_right_velocity * self.accel_factor
            self.target_vy = forward_backward_velocity * self.accel_factor
            self.target_vz = up_down_velocity * (self.accel_factor * 0.5)
            self.target_vyaw = yaw_velocity * -2.0 # Invert yaw to match standard orientation
            
    def streamon(self):
        print("[MockTello3D] Video stream started.")
        self.frame_read = self.app.get_frame_reader()
        
    def streamoff(self):
        print("[MockTello3D] Video stream stopped.")
        pass
            
    def get_frame_read(self):
        return self.frame_read
        
    def get_battery(self):
        return self.battery

    def get_map_draw(self):
        # We don't have a 2D map anymore, returning None disables it in tracker
        return None


class DroneEngine(ShowBase):
    def __init__(self, drone_controller):
        # Override standard output to suppress Panda3D spam if needed
        ShowBase.__init__(self, windowType='offscreen') # Render offscreen!
        self.drone = drone_controller
        
        # Frame capture setup (Offscreen Buffer size is set by PRC)
        # Generate world
        self.build_world()
        
        # Frame reader interface
        self.frame_reader = FrameReader3D()
        
        # Task manager
        self.taskMgr.add(self.update_physics, "update_physics")
        self.taskMgr.add(self.capture_frame, "capture_frame")
        
        # Target movement properties
        self.person_theta = 0.0

    def get_frame_reader(self):
        return self.frame_reader

    def build_world(self):
        # Lights
        alight = AmbientLight('alight')
        alight.setColor(Vec4(0.4, 0.4, 0.4, 1))
        alnp = self.render.attachNewNode(alight)
        self.render.setLight(alnp)

        dlight = DirectionalLight('dlight')
        dlight.setColor(Vec4(0.8, 0.8, 0.8, 1))
        dnp = self.render.attachNewNode(dlight)
        dnp.setHpr(45, -45, 0)
        self.render.setLight(dnp)
        
        # Floor (Chessboard pattern)
        # We use CardMaker directly to avoid missing model errors
        from panda3d.core import CardMaker
        cm = CardMaker('ground')
        cm.setFrame(-50, 50, -50, 50)
        ground = self.render.attachNewNode(cm.generate())
        ground.setHpr(0, -90, 0)
        ground.setColor(0.6, 0.8, 0.6, 1)
        
        # The Target (A simple cylinder to represent a person)
        # We programmatically create a box to avoid missing smiley models
        cm_person = CardMaker('person_face')
        cm_person.setFrame(-0.5, 0.5, -1, 1)
        
        self.person = self.render.attachNewNode("PersonNode")
        
        # Billboard to always face camera
        face = self.person.attachNewNode(cm_person.generate())
        face.setColor(0.8, 0.2, 0.2, 1) # Red person target
        face.setBillboardAxis()
        
        self.person.setZ(1.0)

        # Environment obstacles (just columns)
        cm_col = CardMaker('col')
        cm_col.setFrame(-0.5, 0.5, 0, 4)
        for i in range(5):
             col = self.render.attachNewNode(cm_col.generate())
             col.setPos((i-2)*5, 10, 0)
             col.setColor(0.3, 0.3, 0.3, 1)
             col.setBillboardAxis()

        self.cam.setPos(0, -10, 1.2)
        
    # Removed _create_grid, inline above

    def update_physics(self, task):
        dt = self.taskMgr.globalClock.getDt()
        
        with self.drone.lock:
            # Physical drone limits and drag application
            if self.drone.is_flying:
                # Apply commands as forces
                self.drone.vx += (self.drone.target_vx - self.drone.vx * self.drone.drag) * dt
                self.drone.vy += (self.drone.target_vy - self.drone.vy * self.drone.drag) * dt
                self.drone.vz += (self.drone.target_vz - self.drone.vz * self.drone.drag) * dt
                self.drone.vyaw += (self.drone.target_vyaw - self.drone.vyaw * self.drone.drag) * dt
            else:
                 # Gravity / friction to zero
                 self.drone.vx *= 0.9
                 self.drone.vy *= 0.9
                 self.drone.vyaw *= 0.9

            # Update orientation
            self.drone.yaw += self.drone.vyaw * dt
            
            # Local to Global translation
            # In Panda3D, Y is forward. We rotate around Z axis.
            heading_rad = math.radians(self.drone.yaw)
            c = math.cos(heading_rad)
            s = math.sin(heading_rad)
            
            # drone.vy is commanded forward speed (Y in local)
            # drone.vx is commanded right speed (X in local)
            global_vx = (self.drone.vx * c) + (self.drone.vy * s)
            global_vy = (-self.drone.vx * s) + (self.drone.vy * c)
            
            self.drone.x += global_vx * dt
            self.drone.y += global_vy * dt
            self.drone.z += self.drone.vz * dt
            
            if self.drone.z < 0: self.drone.z = 0
            
            # Sync Camera to Drone
            self.cam.setPos(self.drone.x, self.drone.y, self.drone.z)
            self.cam.setHpr(self.drone.yaw, 0, 0) # HPR = Yaw, Pitch, Roll
            
        # Move target
        if hasattr(self, 'person'):
            self.person_theta += 0.5 * dt
            r = 4.0
            px = r * math.cos(self.person_theta)
            py = r * math.sin(self.person_theta * 0.8)
            self.person.setPos(px, py + 5, 1.0)
            
        return task.cont

    def capture_frame(self, task):
        # High CPU cost: we extract the texture
        tex = self.win.getDisplayRegion(0).getScreenshot()
        if tex:
            data = tex.getRamImageAs("BGR")
            # Convert to numpy array
            image = np.frombuffer(data, np.uint8)
            image.shape = (tex.getYSize(), tex.getXSize(), tex.getNumComponents())
            
            # Flip vertically (Panda3D origin is bottom left)
            image = cv2.flip(image, 0)
            
            self.frame_reader.push_frame(image)
            
        return task.cont


class FrameReader3D:
    def __init__(self):
        self.frame_buffer = deque()
        self.latency_seconds = 0.2 # 200ms Simulated WiFi Latency
        self.latest_frame = None
        self.default_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    def push_frame(self, frame):
        now = time.time()
        self.frame_buffer.append((now, frame))
        
        # Pop frames older than latency
        while len(self.frame_buffer) > 1 and (now - self.frame_buffer[0][0]) >= self.latency_seconds:
             _, self.latest_frame = self.frame_buffer.popleft()
             
    def get_frame(self):
        if self.latest_frame is not None:
            # Draw HUD on frame
            frame_copy = self.latest_frame.copy()
            cv2.putText(frame_copy, f"Panda3D Sim | Latency: 200ms", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 1)
            return frame_copy
        return self.default_frame

if __name__ == "__main__":
    # Test block
    sim = MockTello3D()
    sim.connect()
    sim.streamon()
    sim.takeoff()
    
    fr = sim.get_frame_read()
    print("Starting preview...")
    for _ in range(500):
        frame = fr.get_frame()
        cv2.imshow("3D Sim Test", frame)
        if cv2.waitKey(20) & 0xFF == ord('q'):
            break
        # Spin drone
        sim.send_rc_control(0, 0, 0, 20)
        
    cv2.destroyAllWindows()
    sys.exit()
