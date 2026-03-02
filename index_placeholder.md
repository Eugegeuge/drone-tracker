# Índice General del Proyecto: drone-tracker

[cite_start]Este documento define la estructura técnica del Trabajo Fin de Grado (TFG), siguiendo el modelo de desarrollo de sistemas robóticos de bajo coste[cite: 6].

---

## 1. Introducción
* **1.1. [cite_start]Contexto Tecnológico:** Evolución de la robótica y los UAVs[cite: 62, 63].
* **1.2. [cite_start]Motivación:** Importancia de la interacción autónoma y el procesamiento en tiempo real[cite: 25, 26].
* **1.3. [cite_start]Objetivos del Proyecto:** [cite: 164, 165]
    * Desarrollo de un sistema de seguimiento de objetivos.
    * Integración en el ecosistema ROS (Robot Operating System).
    * Optimización para hardware embebido de bajo coste.

## 2. Marco Teórico (Estado del Arte)
* **2.1. [cite_start]Robótica de Servicio y UAVs:** Definición y aplicaciones actuales[cite: 106, 107, 108].
* **2.2. [cite_start]Plataformas Low-Cost:** Comparativa de soluciones existentes (JetBot, OpenBot, Thymio, etc.)[cite: 115, 116, 132, 140, 149].
* **2.3. [cite_start]Algoritmos de Visión y Aprendizaje Profundo:** [cite: 287, 288]
    * [cite_start]Redes Neuronales Convolucionales (CNN)[cite: 330, 331].
    * [cite_start]Arquitecturas eficientes para sistemas embebidos: MobileNet V2[cite: 354, 355].

## 3. Metodología
* **3.1. [cite_start]Arquitectura del Sistema:** Diagrama de bloques y flujo de datos[cite: 176, 196].
* **3.2. [cite_start]Hardware:** [cite: 198]
    * Unidad de procesamiento: Raspberry Pi 4 Model B[cite: 200, 201].
    * [cite_start]Sistema de captura: Cámara con soporte plug-and-play[cite: 224, 225].
* **3.3. [cite_start]Software:** [cite: 235, 236]
    * Lenguaje de programación: Python[cite: 263, 265].
    * [cite_start]Middleware: Robot Operating System (ROS)[cite: 271, 272].
    * [cite_start]Librerías: OpenCV y TensorFlow/Keras[cite: 294, 301, 308].



## 4. Desarrollo Técnico
* **4.1. [cite_start]Nodo de Visión:** Lógica de detección y tracking del objetivo (`tracker.py`)[cite: 695].
* **4.2. [cite_start]Control de Vuelo:** Gestión de comandos y comunicación con el dron (`drone.py`)[cite: 532, 533].
* **4.3. [cite_start]Comunicación Serie:** Protocolos USB-TTL/UART y gestión de mensajes en ROS[cite: 402, 403, 487].

## 5. Resultados y Evaluación
* **5.1. [cite_start]Pruebas de Inferencia:** Análisis de tiempos de respuesta y estabilidad (ms/step)[cite: 952, 1046, 1047].
* **5.2. [cite_start]Precisión del Sistema:** Evaluación en entornos reales y condiciones variables[cite: 731, 732].
* **5.3. [cite_start]Presupuesto:** Desglose económico y comparativa con plataformas comerciales[cite: 1126, 1129, 1133].

## 6. Conclusiones y Trabajo Futuro
* **6.1. [cite_start]Análisis de Objetivos:** Valoración del sistema funcional desarrollado[cite: 1139, 1140].
* **6.2. [cite_start]Limitaciones:** Restricciones de hardware y condiciones externas[cite: 1149, 1152].
* **6.3. [cite_start]Líneas de Investigación Futura:** Sensores adicionales y optimización de modelos[cite: 1157, 1159].

---
*Este índice constituye la base estructural de la memoria técnica del TFG.*
