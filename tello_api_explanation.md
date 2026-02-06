# Explicación del Código y la API de DJI Tello

Este documento explica cómo el código de `tracker.py` se traduce en comandos reales para el dron utilizando la librería `djitellopy`.

## 1. Conexión e Inicialización
En el código:
```python
self.drone = Tello()
self.drone.connect()
```
**API `djitellopy`**:
-   `Tello()`: Crea una instancia de la clase que gestiona la comunicación UDP con el dron.
-   `connect()`: Envía el comando SDK `command` al dron para entrar en modo SDK. Sin esto, el dron no acepta órdenes. También verifica el nivel de batería.

## 2. Control de Movimiento (RC Control)
Esta es la parte más importante. En el código calculamos 4 variables:
-   `lr` (Left/Right): Velocidad lateral.
-   `fb` (Forward/Back): Velocidad de avance/retroceso.
-   `ud` (Up/Down): Velocidad vertical.
-   `yv` (Yaw Velocity): Velocidad de rotación.

Y se envían así:
```python
self.drone.send_rc_control(lr, fb, ud, yv)
```
**API `djitellopy`**:
-   `send_rc_control(left_right_velocity, forward_backward_velocity, up_down_velocity, yaw_velocity)`
-   **Valores**: Enteros entre **-100 y 100**.
-   **Comportamiento**:
    -   Envía el comando `rc a b c d` al dron continuamente.
    -   Si envías `0, 0, 0, 0`, el dron se queda en vuelo estacionario (hover).
    -   En nuestro código, si no detectamos a nadie, enviamos ceros (o no enviamos nada si no estamos volando).

### Lógica de Centrado (PID Simplificado)
-   **Yaw (`yv`)**:
    -   Error = `PosiciónX_Persona` - `Centro_Imagen`.
    -   Si la persona está a la derecha (Error > 0), giramos a la derecha (`yv` positivo).
    -   Referencia API: Rotación en sentido horario (positivo) o antihorario (negativo).

-   **Distancia (`fb`)**:
    -   Usamos el **Área** del recuadro de la persona como estimación de distancia.
    -   Si `Area < 30000` (lejos), avanzamos (`fb` positivo).
    -   Si `Area > 60000` (cerca), retrocedemos (`fb` negativo).

-   **Altura (`ud`)**:
    -   Error = `PosiciónY_Persona` - `Centro_Imagen`.
    -   En imagen, "abajo" es Y positivo.
    -   Si la persona está "abajo" en la imagen (Error > 0), el dron tiene que bajar.
    -   Referencia API: Velocidad vertical negativa es bajar.

## 3. Despegue y Aterrizaje
En el código:
```python
self.drone.takeoff()
self.drone.land()
```
**API `djitellopy`**:
-   `takeoff()`: Envía `takeoff`. El dron sube automáticamente a ~1.2 metros y se queda en estacionario.
-   `land()`: Envía `land`. El dron desciende lentamente hasta detectar el suelo y apaga motores.

## 4. Video (Cuando uses el dron real)
Aunque ahora usamos `cv2.VideoCapture(0)`, con el dron real sería:
```python
self.drone.streamon()
frame_read = self.drone.get_frame_read()
frame = frame_read.frame
```
**API `djitellopy`**:
-   `streamon()`: Envía el comando `streamon`. El dron empieza a enviar vídeo H.264 por el puerto UDP 11111.
-   `get_frame_read()`: Inicia un hilo en segundo plano que decodifica el vídeo continuamente para que siempre tengas el último *frame* disponible sin lag.
