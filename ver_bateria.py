from djitellopy import Tello

print("Iniciando conexión con el Tello...")
try:
    drone = Tello()
    drone.connect()
    
    bateria = drone.get_battery()
    print("="*30)
    print(f"🔋 Batería del Tello: {bateria}%")
    print("="*30)
    
except Exception as e:
    print(f"Error al conectar: {e}")
    print("Asegúrate de estar conectado a la red Wi-Fi del Tello (TELLO-XXXXXX).")
