import cv2
import time
from djitellopy import Tello
from pynput import keyboard

# --- Configuración de Control (Estilo Webots) ---
SPEED = 50
keys_pressed = set()

def on_press(key):
    try:
        # Si es una tecla con carácter (a, b, c...), la pasamos a minúscula
        if hasattr(key, 'char') and key.char:
            keys_pressed.add(keyboard.KeyCode.from_char(key.char.lower()))
        else:
            keys_pressed.add(key)
    except Exception:
        pass

def on_release(key):
    try:
        # Eliminar tanto la versión original como la posible minúscula
        if hasattr(key, 'char') and key.char:
            k = keyboard.KeyCode.from_char(key.char.lower())
            if k in keys_pressed: keys_pressed.remove(k)
        if key in keys_pressed:
            keys_pressed.remove(key)
    except Exception:
        pass

# Iniciar el escuchador de teclado en segundo plano
listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()

def get_tello_controls():
    lr, fb, ud, yv = 0, 0, 0, 0
    
    # Detectar Shift (Cualquiera de los dos)
    shift = any(k in keys_pressed for k in [keyboard.Key.shift, keyboard.Key.shift_r])
    
    # Flecha Arriba
    if keyboard.Key.up in keys_pressed:
        if shift: ud = SPEED  # Shift + Up = Subir
        else: fb = SPEED      # Up = Adelante
        
    # Flecha Abajo
    if keyboard.Key.down in keys_pressed:
        if shift: ud = -SPEED # Shift + Down = Abajo
        else: fb = -SPEED     # Down = Atrás

    # Flecha Izquierda
    if keyboard.Key.left in keys_pressed:
        if shift: lr = -SPEED # Shift + Left = Izquierda (Strafe)
        else: yv = -SPEED     # Left = Girar Izquierda (Yaw)

    # Flecha Derecha
    if keyboard.Key.right in keys_pressed:
        if shift: lr = SPEED  # Shift + Right = Derecha (Strafe)
        else: yv = SPEED      # Right = Girar Derecha (Yaw)

    return lr, fb, ud, yv

def main():
    print("--- DJI Tello: Teleop Estilo Webots ---")
    print("Controles:")
    print("- Flechas: Mover (Adelante/Atrás) y Girar (Izquierda/Derecha)")
    print("- Shift + Flechas: Subir/Bajar y Desplazamiento Lateral")
    print("- T: Despegar")
    print("- L: Aterrizar")
    print("- Q / ESC: Salir y Aterrizar")
    
    drone = Tello()
    try:
        drone.connect()
        print(f"Batería: {drone.get_battery()}%")
        drone.streamon()
    except Exception as e:
        print(f"Error al conectar: {e}")
        return

    frame_reader = drone.get_frame_read()
    is_flying = False

    while True:
        frame = frame_reader.frame
        if frame is None:
            continue
            
        frame = cv2.resize(frame, (640, 480))
        h, w, _ = frame.shape
        
        # Procesar Teclado Externo (pynput)
        lr, fb, ud, yv = get_tello_controls()
        
        # Acciones Especiales (Teclas únicas)
        # Nota: pynput.keyboard.KeyCode.from_char('t') para letras
        t_key = keyboard.KeyCode.from_char('t')
        l_key = keyboard.KeyCode.from_char('l')
        q_key = keyboard.KeyCode.from_char('q')
        
        if keyboard.Key.esc in keys_pressed or q_key in keys_pressed:
            print("Saliendo...")
            drone.land()
            break
            
        if t_key in keys_pressed and not is_flying:
            print("Despegando...")
            drone.takeoff()
            is_flying = True
            # Limpiar tecla para evitar repetición
            if t_key in keys_pressed: keys_pressed.remove(t_key)
            
        if l_key in keys_pressed and is_flying:
            print("Aterrizando...")
            drone.land()
            is_flying = False
            if l_key in keys_pressed: keys_pressed.remove(l_key)

        # Enviar comandos si está volando
        if is_flying:
            drone.send_rc_control(lr, fb, ud, yv)
        else:
            # En tierra enviamos 0 para seguridad
            drone.send_rc_control(0, 0, 0, 0)

        # HUD
        bat = drone.get_battery()
        color = (0, 255, 0) if bat > 20 else (0, 0, 255)
        cv2.putText(frame, f"BATERIA: {bat}%", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(frame, f"MODO: {'VUELO' if is_flying else 'TIERRA'}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        if shift := any(k in keys_pressed for k in [keyboard.Key.shift, keyboard.Key.shift_r]):
            cv2.putText(frame, "SHIFT ACTIVO (Altura/Lateral)", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        cv2.imshow("Tello Teleop (Flechas + Shift)", frame)
        
        # cv2.waitKey es necesario para que la ventana se actualice, pero no lo usamos para control
        if cv2.waitKey(1) & 0xFF == ord('q'):
            drone.land()
            break

    drone.streamoff()
    cv2.destroyAllWindows()
    listener.stop()

if __name__ == "__main__":
    main()
