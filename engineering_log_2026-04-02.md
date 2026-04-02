# Engineering Log - 2026-04-02

## Resumen de la Jornada: Drone Tracker & Distance Estimation

Hoy se ha desarrollado e integrado un sistema completo de estimación de distancia y seguimiento facial para el dron DJI Tello y Webcam.

### Hitos Alcanzados:

1.  **Estimación de Distancia (Pinhole Model):**
    *   Implementación de la lógica matemática basada en el modelo de cámara estenopeica.
    *   Calibración de la constante física `S_REAL` a **0.185m** (altura del rostro detectado por MediaPipe) para mejorar la precisión.
    *   Filtrado de señal mediante **Media Móvil Exponencial (EMA)** con $\alpha=0.3$ para eliminar el ruido del sensor.

2.  **Infraestructura y Dependencias:**
    *   Configuración del entorno virtual (`venv`) y actualización de `requirements.txt`.
    *   Migración a la API moderna de **Mediapipe Tasks** debido a la falta de soporte de `solutions` en el entorno local.
    *   Integración del modelo `face_detector.tflite`.

3.  **Control de Vuelo Híbrido:**
    *   Fusión de la lógica de teleoperación manual (Flechas + Shift) mediante `pynput`.
    *   Implementación de un **Sistema de Seguimiento 3D (PID)** que controla:
        *   **Eje Z (Pitch):** Mantenimiento de distancia a 1.5m.
        *   **Eje X (Yaw):** Rotación para centrar el rostro horizontalmente.
        *   **Eje Y (Throttle):** Ajuste de altura para centrar el rostro verticalmente.
    *   Optimización de la frecuencia de comandos a **20Hz** para prevenir la saturación del buffer UDP y el sobrecalentamiento del dron.

4.  **Telemetría y HUD:**
    *   Visualización en tiempo real de la batería y la distancia al suelo (sensor TOF) en la ventana de vídeo.
    *   Indicadores visuales de modo (AUTO/MANUAL) y velocidades comandadas.

---
**Próximos pasos:** Probar la estabilidad del seguimiento en entornos con luz variable y ajustar las constantes Kp del PID si es necesario.
