# Engineering Log - TFG Drone Project

## Session 1: Initial Setup and Person Tracker Prototype
**Date**: 2026-01-27

### Context
The objective of this session was to establish the development environment and create a proof-of-concept for the person tracking system. The specific goals were to:
1.  Research and select the appropriate tools for the DJI Tello drone and object detection.
2.  Implement a computer vision prototype to detect a person and calculate control signals for centering.

### Changes
1.  **Dependency Management**:
    - **Action**: Created a Python virtual environment (`venv`).
    - **Reasoning**: The system Python environment is externally managed (PEP 668), preventing direct `pip install`. A virtual environment is best practice to isolate project dependencies and avoid system conflicts.
    - **Dependencies Installed**: `ultralytics` (for YOLO), `djitellopy` (for future Tello control), `opencv-python` (for computer vision).

2.  **Implementation of `tracker.py`**:
    - **Action**: Created a Python script that captures webcam video, runs YOLOv8 inference, and calculates control commands.
    - **Reasoning**:
        - Used `YOLO('yolov8n.pt')`: The "nano" model is chosen for its speed, which is critical for real-time control on a laptop or eventually on an edge device.
        - **Control Logic**: Implemented a simple proportional controller logic.
            - Calculated the center of the detected person's bounding box.
            - Compared it to the frame center to determine `error_x` and `error_y`.
            - Mapped these errors to simulated drone commands (Yaw Left/Right, Up/Down).
            - Used bounding box area as a proxy for distance to simulate Forward/Back commands.
    - **Output**: The script visualizes the detection and prints the intended commands to the screen, allowing for verification without the physical drone.

### Next Steps
- Connect to the actual DJI Tello drone.
- Replace the print statements in `tracker.py` with actual `djitellopy` commands.
- Tune the control thresholds and PID gains for smooth flight.

## Session 2: Simulation and Robustness
**Date**: 2026-01-27

### Context
To proceed with development without the physical hardware, we needed a robust simulation layer. The previous "print to console" approach was insufficient for testing the actual control logic structure. We also identified a need to improve the person selection logic to handle multiple subjects.

### Changes
1.  **Created `mock_tello.py`**:
    - **Action**: Implemented a `MockTello` class that mirrors the `djitellopy.Tello` interface.
    - **Reasoning**: This allows the main application code to remain agnostic to whether it is running on real hardware or in simulation. We can simply toggle a `USE_MOCK` flag.
    - **Features**: Simulates connection, battery status, video stream (wrapping the webcam), and logs RC control commands.

2.  **Enhanced `tracker.py`**:
    - **Action**: Integrated `MockTello` and upgraded the tracking algorithm.
    - **Logic Improvement**:
        - **Target Selection**: Now iterates through all detected persons and selects the one with the **largest bounding box area**. This assumes the largest subject is the closest/primary user.
        - **Visual Feedback**: Added a green bounding box and "TRACKING" label for the selected subject, distinguishing it from other detections.
        - **Control Integration**: Now calls `drone.send_rc_control()` with calculated PID values.
    - **Verification**: Confirmed that the system runs, connects to the "mock" drone, and generates varying control signals based on the user's position in the webcam feed.

### Next Steps
- Implement a more advanced PID controller (currently simple Proportional).
- Add safety features (e.g., auto-land if no person detected for X seconds).

## Session 3: Virtual World Simulation
**Date**: 2026-01-27

### Context
The user requested a more realistic simulation where the camera feed reacts to the drone's movements. This is crucial for validating the control loop visually, as a static webcam feed does not provide feedback on whether the "Yaw Right" command actually centers the target.

### Changes
1.  **Asset Generation**:
    - **Action**: Created `generate_assets.py` to programmatically create a `background.png` (grid map) and `person.png` (simple sprite).
    - **Reasoning**: Avoided external dependencies/downloads.

2.  **Advanced `MockTello`**:
    - **Physics Engine**: Implemented a 2D kinematic model. The drone has a position `(x, y)` and orientation `yaw`. Velocity commands (`send_rc_control`) update these state variables over time.
    - **Camera Simulator**:
        - Instead of the webcam, the `MockFrameReader` now generates frames by "looking at" the 2D map.
        - It uses `cv2.warpAffine` to rotate the map around the drone's position (simulating yaw) and crops the view to simulate the camera's field of view.
    - **Result**: When the drone rotates, the world appears to rotate in the opposite direction in the camera feed, correctly simulating a first-person view (FPV).

### Verification
- Running `tracker.py` now opens a window showing the virtual world.
- If the logic sends a "Yaw" command, the view rotates, and the target moves across the screen, closing the control loop visually.

## Session 4: Interactive Simulation
**Date**: 2026-01-27

### Context
The user requested a way to dynamically test the tracking logic by moving the target (person) around the virtual world. This allows for comprehensive testing of the control loop (e.g., placing the target at the edge of the FOV to verify yaw correction) without needing complex automated test scripts.

### Changes
1.  **Refactored `MockTello`**:
    - **Dynamic Rendering**: Removed the static baking of the person sprite into the background. The `MockFrameReader` now composes the scene (Background + Person + Drone) every frame.
    - **Map Visualization**: Added `get_map_draw()` which returns a top-down view of the entire simulation world, including the drone's position, heading, FOV cone, and the target person.
    - **Interaction**: Added `set_person_pos(x, y)` to allow external control of the target's location.

2.  **Updated `tracker.py`**:
    - **Dual Window Display**: Now opens two windows:
        1.  `Tello Tracker`: The simulated camera feed (First Person View).
        2.  `Simulation Map`: The top-down "God View" of the world.
    - **Mouse Interaction**: Implemented a mouse callback on the "Simulation Map" window. Clicking anywhere on the map instantly moves the target person to that location.

### Verification
- Verified that clicking on the map moves the person.
- Verified that the "Tello Tracker" view updates immediately to show the person in the new location (relative to the drone).
- Validated that the drone's control logic responds to the new position (e.g., yawing to face the person if they are moved to the side).
