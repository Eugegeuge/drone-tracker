# Lecciones Aprendidas: Webots + YOLO Tracking (Mavic 2 Pro)

Este documento resume los retos técnicos superados para lograr que el dron Mavic 2 Pro vuele de forma autónoma con YOLOv8 en Webots.

## 1. Configuración de Entorno (Windows)
- **Error**: `ModuleNotFoundError: No module named 'controller'`.
- **Causa**: Python no conoce la ubicación de las librerías de Webots ni sus DLLs.
- **Solución**: 
  - Añadir `C:\Program Files\Webots\lib\controller\python` al `sys.path`.
  - Usar `os.add_dll_directory` para incluir los binarios de Webots (`msys64\mingw64\bin`) en el PATH de Windows.

## 2. Buffer de Imagen (OpenCV)
- **Error**: `img provided NumPy array marked as readonly` al usar `cv2.putText`.
- **Causa**: La API de Webots entrega la imagen de la cámara como un buffer de solo lectura.
- **Solución**: Hacer una copia explícita del frame antes de procesar: `frame = img[:, :, :3].copy()`.

## 3. Conflictos de Atributos
- **Error**: `AttributeError: property 'model' of 'WebotsYOLOTracker' object has no setter`.
- **Causa**: El objeto `Robot` de Webots ya tiene una propiedad interna llamada `model` (solo lectura).
- **Solución**: Renombrar la instancia de YOLO a `self.yolo_model`.

## 4. Hardware y Motores (Ejes)
- **Error**: El dron no se eleva o se voltea violentamente.
- **Descubrimiento (Mavic 2 Pro)**: 
  - Los motores no son todos iguales. En Webots, para este modelo, los motores **Frontal Derecha** y **Trasero Izquierda** deben tener la velocidad **invertida** (`-velocity`) para generar empuje hacia arriba.
  - El eje de altitud en el GPS suele ser el índice `[2]` (Z) en el Mavic.

## 5. Lógica PID (Signos de Control)
- **Error**: El dron amplifica las inclinaciones en lugar de corregirlas.
- **Lección**: El mezclador de motores del Mavic espera que los errores de Roll y Pitch se sumen o resten siguiendo el sistema de coordenadas de la IMU.
  - **Corrección**: Usar `(roll - target_roll)` y `(pitch - target_pitch)` con los signos exactos del controlador oficial en C para asegurar la estabilidad.

## 7. Gestión de Teclado (Debouncing)
- **Problema**: Al pulsar una tecla de tipo "toggle" (ej. 'T' para despegar o 'M' para auto), la acción se repite muchas veces ("spam") porque `keyboard.getKey()` devuelve la tecla en cada paso de simulación.
- **Solución**: Implementar una lógica de estado previo. Guardar `self.last_key` y solo ejecutar la acción si la tecla actual es distinta a la anterior: `if current_key == ord('T') and current_key != self.last_key:`.
