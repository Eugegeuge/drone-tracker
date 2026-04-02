# Resumen de Proyecto: TFG Drone Tracker

## 1. Descripción General
El objetivo de este Trabajo de Fin de Grado es el diseño e implementación de un sistema de **seguimiento autónomo de personas en tiempo real** utilizando un dron comercial de bajo coste (**DJI Tello**). El sistema utiliza visión artificial para detectar al objetivo y algoritmos de control para que el dron mantenga una distancia y posición constante respecto a él.

## 2. Tecnologías Utilizadas
- **Lenguaje:** Python 3
- **Visión Artificial:** OpenCV (Haar Cascades / YOLOv8)
- **Control:** Lógica Proporcional (con planes de implementar PID)
- **Simulación:** Simulador cinemático 2D propio (`mock_tello.py`) con FPV proyectado y mapa interactivo.
- **Drone API:** `djitellopy`
- **Documentación:** LaTeX (plantilla EPS Universidad de Alicante), compilado con XeLaTeX.

## 3. Estado Actual del Proyecto
- **Simulador:** Muy avanzado. Permite probar la lógica de seguimiento sin el dron físico. Incluye un mapa donde se puede mover al "objetivo" con el ratón y ver cómo reacciona el dron en una ventana de cámara virtual.
- **Software (`tracker.py`):** Estructura base completa. Detecta caras/personas y envía comandos de velocidad (`rc_control`) al dron (o al simulador).
- **Informe:** Estructura de LaTeX configurada para el **Grado en Ingeniería Robótica**. Capítulos de Introducción, Objetivos y Marco Teórico ya tienen borradores iniciales basados en la investigación previa.

## 4. Próximos pasos definidos
1. Migrar la detección de Haar Cascades a **YOLOv8** (más robusto).
2. Implementar un controlador **PID** completo para suavizar el vuelo.
3. Añadir lógicas de seguridad (aterrizaje automático si se pierde el objetivo).
4. Continuar con la redacción del desarrollo técnico y resultados en el informe.

---
*Este resumen ha sido generado para facilitar la transferencia de contexto a otras sesiones de asistencia o colaboradores.*
