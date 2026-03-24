# Resumen de Sesión: Desarrollo de la Primera Simulación Webots (24 de Marzo de 2026)

Este documento recopila todo el progreso, los retos técnicos superados y las decisiones arquitectónicas tomadas durante la integración del dron autónomo con YOLOv8 en el simulador 3D **Webots**.

## 1. Migración y Entorno de Simulación
* **Evaluación Inicial**: Se analizó la viabilidad de continuar con simuladores en 2D customizados (`mock_tello.py`) o saltar a plataformas 3D como ROS/Gazebo. Finalmente optamos por **Webots** debido a su ligereza, instalación en un solo clic y su potente API en Python nativo para Windows.
* **Resolución de Dependencias (Windows)**: Hubo un gran bloqueo inicial provocado por un fallo al enlazar Python local con las DLLs compiladas de Webots (MingW64). Lo solucionamos introduciendo en `webots_yolo_tracker.py` una inyección dinámica en `os.environ['PATH']` y `os.add_dll_directory` para que Python detectara el motor físico automáticamente.

## 2. El Vuelo Base: Porting del DJI Mavic 2 Pro (De C a Python)
El modelo `Mavic 2 Pro` de Webots viene con un script estabilizador oficial en lenguaje C. Nuestros intentos iniciales de volar el dron con lógicas propias resultaron en comportamientos caóticos. Para lograr un vuelo comercial perfecto, hicimos una **traducción matemática 1:1 absoluta** del C a nuestro Python:
* **Físicas Nativas**: Se implementó la lectura en bruto del giroscopio (`gyro`) y la unidad inercial (`imu`) para calcular el *Roll*, *Pitch*, *Yaw* y la aceleración instantánea.
* **Mezcla de Motores**: Descubrimos con la ingeniería inversa del C que en Webots, los motores derechos (`front_right` y `rear_left`) giran invertidos. Se replicó la compleja ecuación de cálculo de velocidades (`m1`, `-m2`, `-m3`, `m4`).
* **Hardware Auxiliar**: Añadimos estabilización en tiempo real al cardán (gimbal) de la cámara mediante compensación giroscópica de `roll` y `pitch`, y sincronizamos el parpadeo de LEDs.
* **Control Manual Profesional**: Se replicó el "buffer" del teclado original para procesar combinaciones de teclas simultáneas (`Shift + Flechas`), permitiendo pilotar el dron manualmente de forma intuitiva e idéntica al oficial.

## 3. Integración de Visión y Rendimiento
* **Latencia / Frame Skipping**: El bucle físico de Webots ocurre cada 32 milisegundos. Ejecutar la inferencia neuronal en cada paso provocaba un lag fatal, congelando el dron en el aire. Se resolvió creando un *Frame Skip* donde YOLO solo analiza **1 frame por cada 5 pasos físicos**, devolviendo el control instintivo al simulador.
* **API de Cámara**: Corregimos los errores de lectura de *buffers* de Webots a OpenCV convirtiendo matrices `BGRA` crudas a matrices reescribibles `BGR` con `.copy()`.

## 4. Evolución de la Inteligencia: YOLOv8 Pose
* **De Bounding Boxes a Esqueletos**: Inicialmente usábamos el centro de una "caja" (Bounding Box). Sin embargo, esto causaba inestabilidad cuando el peatón estiraba los brazos o piernas, desviando el centro y desestabilizando al dron. Lo mejoramos actualizando a la red neuronal de Postura (`yolov8n-pose.pt`).
* **Punto de Anclaje Estable**: Extraemos únicamente los *Keypoints* de los hombros (Puntos 5 y 6 en formato COCO), nos cercioramos de que son visibles en la cámara, calculamos el punto medio exacto y "anclamos" el dron visualmente al **pecho rígido de la persona**.
* **Filtro Estricto**: Añadimos un umbral mínimo de confianza del 70% (`conf > 0.70`). Si el objeto parece remotamente dudoso, el dron simplemente entra en "hover" estacionario.

## 5. Arquitectura del Control Automático (PID Modular)
* **Del Control Bang-Bang al Control Continuo**: Anteriormente el Dron operaba con condiciones absolutas (ej. si no está en el centro, gira siempre a velocidad 1.3). Ese comportamiento errático *On/Off* lo reemplazamos por algoritmos Proporcionales y Derivativos (PD) continuos e independientes para Yaw (px), Pitch (área detectada) y Altitud (py).
* **Módulo Independiente (`pid_controller.py`)**: Extraímos esta matemática pura a un módulo de clase Genérico. Esto **desacopla el cerebro del TFG respecto al simulador**. Podrá reutilizarse mañana en ROS, en otro simulador o en tu placa física (Raspberry Pi, Arduino) si fuera necesario.

## Conclusión de la Sesión
Comenzamos el día con un script fallido en un entorno 2D y lo hemos concluido con un simulador fotorealista 3D donde la cámara, la física del dron y la visión artificial del esqueleto humano corren en perfecta sintonía y con bajo consumo de CPU. Se han dejado las bases PID separadas y listas para experimentación matemática avanzada.
