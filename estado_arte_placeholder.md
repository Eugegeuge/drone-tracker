# Estado del Arte: Sistema de Seguimiento Autónomo de UAVs Low-Cost

Este documento constituye el marco teórico preliminar para el desarrollo del proyecto **drone-tracker**, fundamentado en la investigación de sistemas robóticos de bajo coste y visión artificial.

---

## 1. Contexto y Robótica de Servicio
[cite_start]La robótica de servicio se orienta a la asistencia en tareas cotidianas en entornos no industriales, priorizando la interacción flexible con seres humanos[cite: 108, 109]. [cite_start]En el ámbito de los UAVs, el seguimiento autónomo es una extensión de esta disciplina, con aplicaciones en educación, seguridad y asistencia personalizada[cite: 26, 110].

## 2. Tecnologías de Detección y Seguimiento
[cite_start]El seguimiento visual en tiempo real requiere la combinación de visión por computador y aprendizaje profundo (Deep Learning)[cite: 27]. 

* [cite_start]**Redes Neuronales Convolucionales (CNN):** Son algoritmos avanzados diseñados específicamente para el procesamiento de imágenes y reconocimiento visual[cite: 331].
* [cite_start]**Arquitecturas Ligeras:** Modelos como **MobileNetV2** son fundamentales para sistemas embebidos debido a su estructura basada en convoluciones separables, que ofrece una alternativa muy eficiente[cite: 355, 356].



## 3. Plataformas de Hardware Low-Cost
[cite_start]La tendencia actual se basa en el uso de materiales asequibles y plataformas de código abierto para garantizar la accesibilidad[cite: 112, 113].

| Componente | Función en el Sistema | Referencia Técnica |
| :--- | :--- | :--- |
| **Raspberry Pi 4** | Cerebro del sistema / Procesamiento IA | [cite_start]Destaca por su versatilidad y capacidad de ejecución en tiempo real[cite: 201, 202]. |
| **Cámara Webcam** | Captura de datos visuales | [cite_start]Se seleccionan por su compatibilidad plug-and-play y relación calidad-precio[cite: 225, 232]. |
| **Nodos de Control** | Gestión de motores y sensores | [cite_start]Utilizan microcontroladores para atender interrupciones y ejecutar acciones físicas[cite: 471]. |



## 4. Software y Middleware: ROS (Robot Operating System)
[cite_start]El uso de ROS permite una creación modular de aplicaciones robóticas complejas[cite: 272]. 

* [cite_start]**Comunicación por Nodos:** Permite que los procesos se comuniquen mediante tópicos, facilitando la integración de la visión artificial con el control de vuelo[cite: 273, 275].
* [cite_start]**Protocolo Rosserial:** Facilita la comunicación estructurada entre el sistema ROS y microcontroladores, permitiendo que estos publiquen y se suscriban a tópicos[cite: 487, 488].



---

## 5. Referencias Académicas y Tecnológicas
* [cite_start]**Aldea Amoedo, N. (2025):** Desarrollo de un robot social low cost para aplicaciones de machine learning[cite: 4].
* **Sandler et al. (2018)[cite_start]:** MobileNetV2: Inverted Residuals and Linear Bottlenecks[cite: 1211].
* **Quigley et al. (2009)[cite_start]:** ROS: an open-source Robot Operating System[cite: 1207].

---
*Nota: Este documento es preliminar y está sujeto a cambios conforme avance la fase de implementación técnica del TFG.*
