# Introducción y Justificación Técnica

Este documento detalla los pilares fundamentales del proyecto **drone-tracker**, definiendo sus metas y la base tecnológica que lo sustenta.

---

## 1.3. Objetivos

El objetivo principal de este Trabajo de Fin de Grado es diseñar e implementar un sistema robótico aéreo capaz de realizar el seguimiento autónomo de un objetivo en tiempo real.

Para alcanzar este objetivo general, se plantean los siguientes objetivos específicos:

* **Investigación de plataformas:** Estudiar ejemplos de sistemas robóticos y plataformas de bajo coste existentes para establecer un marco de referencia.
* **Integración de visión artificial:** Desarrollar un sistema de detección de objetivos utilizando librerías de procesado de imagen como OpenCV.
* **Desarrollo de lógica de seguimiento:** Implementar algoritmos de control que permitan al dron reaccionar a la posición del objetivo captado por la cámara.
* **Optimización de recursos:** Priorizar el uso de herramientas de código abierto y hardware accesible para garantizar la replicabilidad del proyecto.
* **Evaluación de rendimiento:** Analizar la estabilidad del sistema y los tiempos de respuesta durante las pruebas de vuelo real.

---

## 3.4. Justificación de la Plataforma Tecnológica

El desarrollo de este proyecto se fundamenta en una arquitectura de bajo coste que prioriza la eficiencia sobre la complejidad de la infraestructura.

### 3.4.1. Dron DJI Tello y API de Python
* **Accesibilidad Low-Cost:** Al igual que otras plataformas educativas de bajo coste (como JetBot u Otto DIY), el Tello permite investigar en robótica avanzada con un presupuesto reducido.
* **Abstracción de Hardware:** La API permite centrarse en la lógica de alto nivel (visión y seguimiento) sin necesidad de gestionar protocolos de vuelo básicos.
* **Soporte de Desarrollo:** Python es el estándar por su gran ecosistema de bibliotecas para inteligencia artificial y robótica.

### 3.4.2. Procesamiento Centralizado
* **Capacidad Computacional:** Al ejecutar el algoritmo en un PC, se dispone de recursos superiores para procesar imágenes en tiempo real en comparación con sistemas embebidos limitados.
* **Visión por Computador:** El uso de OpenCV es fundamental para capturar y procesar el flujo de vídeo, permitiendo identificar objetivos de interés.

### 3.4.3. Viabilidad Académica
* **Estructura Modular:** El uso de scripts independientes facilita una separación de tareas clara, lo que simplifica la depuración y futuras ampliaciones del sistema.
