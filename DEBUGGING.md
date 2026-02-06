# Debugging Guide

## 1. Visual Debugging (The "Iron Man" HUD)
The easiest way to debug is to look at the window that opens up.
- **Green Box**: The person the drone is currently tracking.
- **Grey Box**: Other people detected but ignored.
- **Red Dot**: The center of the tracked person.
- **Green Dot**: The center of the camera frame.
- **Text Info**:
    - `TRACKING`: Confirms logic has selected a target.
    - `SEARCHING`: Logic cannot find a valid target.
    - `RC: ...`: Shows the exact values being sent to the drone.

## 2. Console Logging
The terminal will show real-time logs from the `MockTello` class.
- Watch for `[MockTello] RC Control: ...`.
- If you see `lr=0, fb=0, ud=0, yaw=0`, the drone is hovering.
- If values are changing, the PID/Logic is working.

## 3. VS Code Debugger (Recommended)
I have added a configuration file so you can use the built-in debugger.
1.  Go to the **Run and Debug** tab on the left (Play icon with a bug).
2.  Select **"Python: Debug Tracker"** from the dropdown.
3.  Click the green **Play** button.
4.  **Breakpoints**: Click to the left of the line numbers in `tracker.py` (e.g., line 85 where `error_x` is calculated) to pause execution and inspect variables.

## 4. Common Issues
- **"Could not open webcam"**: Check if another app is using it.
- **Drone not connecting**: Ensure you are on the Tello WiFi (when using real drone) and `USE_MOCK = False`.

## 5. Running from Terminal (Antigravity Users)
If you are not using VS Code, you can run and debug directly from your system terminal:

1.  Open a terminal in `/home/eugegeuge/Documents/tfg`.
2.  Run the following command (fixes common Linux display issues):
    ```bash
    export QT_QPA_PLATFORM=xcb
    source venv/bin/activate
    python3 tracker.py
    ```
3.  **To Debug**: Read the text output in the terminal.
    - `RC: lr=0...` means the logic is running.
    - If it crashes, the error will appear here.

