class PIDController:
    """
    Controlador genérico Proporcional-Integral-Derivativo (PID)
    Diseñado para sistemas de tracking o control físico de robots.
    """
    def __init__(self, kp, ki=0.0, kd=0.0):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        
        self.prev_error = 0.0
        self.integral = 0.0

    def compute(self, error, dt=1.0):
        """
        Calcula la salida del PID basándose en el error actual.
        Para pasos fijos de simulación (ej. Webots), dt puede ser 1.0.
        Para sistemas en tiempo real, pasa el diferencial de tiempo en segundos.
        """
        self.integral += error * dt
        derivative = (error - self.prev_error) / dt
        
        output = (self.kp * error) + (self.ki * self.integral) + (self.kd * derivative)
        self.prev_error = error
        
        return output

    def reset_integral(self):
        """Limpia la integral acumulada para evitar el 'windup' si el dron se atasca"""
        self.integral = 0.0
        self.prev_error = 0.0
