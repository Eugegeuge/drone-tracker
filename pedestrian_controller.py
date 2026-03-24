"""
Controlador de Webots para la PERSONA (Pedestrian).
Hace que camine en un círculo infinito para que el dron tenga algo que seguir.
Asigna este script al campo 'controller' del nodo Pedestrian en Webots.
"""

from controller import Supervisor
import math

class PedestrianCircularMovement(Supervisor):
    def __init__(self):
        super().__init__()
        self.time_step = int(self.getBasicTimeStep())
        self.radius = 3.0  # Radio del círculo en metros
        self.speed = 0.5   # Velocidad angular aprox (rad/s)
        
    def run(self):
        # 1. Obtener el nodo de la propia persona (Supervisor)
        self_node = self.getSelf()
        if not self_node:
            print("ERROR: No se pudo obtener el nodo de la persona. Asegúrate de que el controller esté asignado.")
            return

        # 2. Obtener los campos de posición y rotación
        trans_field = self_node.getField("translation")
        rot_field = self_node.getField("rotation")
        
        print("Iniciando caminata circular de la persona...")

        angle = 0.0
        while self.step(self.time_step) != -1:
            t = self.getTime()
            
            # 3. Calcular nueva posición circular
            angle = t * self.speed
            x = self.radius * math.cos(angle)
            z = self.radius * math.sin(angle)
            
            # Actualizar posición (Manteniendo la Y en el suelo)
            # Nota: Si el suelo no está en 0.0, ajusta el valor medio (0.12 aprox para el humano estándar)
            current_pos = trans_field.getSFVec3f()
            trans_field.setSFVec3f([x, current_pos[1], z])
            
            # 4. Actualizar rotación para que siempre mire 'hacia adelante'
            # (El eje de rotación en Webots suele ser [0, 1, 0, ángulo])
            rot_field.setSFRotation([0, 1, 0, -angle])

if __name__ == '__main__':
    controller = PedestrianCircularMovement()
    controller.run()
