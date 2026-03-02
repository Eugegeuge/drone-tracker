# Estado del Arte: Sistema de Seguimiento Autónomo de UAVs Low-Cost

[cite_start]Este documento resume el marco teórico y el estado actual de la tecnología aplicada al desarrollo del proyecto **drone-tracker**, tomando como referencia metodologías de desarrollo para sistemas robóticos de bajo coste[cite: 27, 112].

---

## 1. Contexto y Robótica de Servicio
[cite_start]La integración de la robótica en entornos civiles ha impulsado el desarrollo de sistemas capaces de interactuar y reaccionar ante estímulos visuales en tiempo real[cite: 25, 27]. [cite_start]En el ámbito de los drones (UAVs), el seguimiento de objetivos es una de las áreas con mayor crecimiento por sus aplicaciones en seguridad, agricultura y cinematografía[cite: 63, 108].

## 2. Tecnologías de Detección y Seguimiento
El seguimiento visual se divide principalmente en dos vertientes tecnológicas:

* [cite_start]**Visión Computacional Tradicional:** Utiliza algoritmos como *Haar Cascades* o filtros de color para identificar patrones específicos en la imagen[cite: 311, 695]. [cite_start]Aunque son ligeros, pueden presentar inestabilidad ante cambios de iluminación[cite: 938, 974].
* [cite_start]**Aprendizaje Profundo (Deep Learning):** El uso de Redes Neuronales Convolucionales (CNN) permite una extracción de características mucho más robusta[cite: 331, 334]. [cite_start]Arquitecturas ligeras como **MobileNetV2** son ideales para dispositivos con capacidad computacional limitada, como la Raspberry Pi[cite: 354, 356, 374].



## 3. Plataformas de Hardware Low-Cost
[cite_start]Siguiendo la tendencia de democratización tecnológica, el uso de componentes asequibles permite crear prototipos funcionales con presupuestos reducidos[cite: 112, 114].

| Componente | Función en el Sistema | [cite_start]Justificación [cite: 202, 225] |
| :--- | :--- | :--- |
| **Raspberry Pi 4** | Unidad central de procesamiento | [cite_start]Alta versatilidad, bajo coste y soporte para Linux/ROS[cite: 201, 238]. |
| **Cámara USB / CSI** | Captura de vídeo | [cite_start]Compatibilidad *plug-and-play* y resolución suficiente para análisis facial/objetos[cite: 225, 229]. |
| **Microcontrolador (Arduino/MegaPi)** | Control de bajo nivel | [cite_start]Gestión de motores y sensores en tiempo real con baja latencia[cite: 403, 471]. |

## 4. Software y Middleware: ROS
[cite_start]El uso de **Robot Operating System (ROS)** es fundamental para la modularidad del sistema[cite: 272]. [cite_start]Permite la comunicación asíncrona entre el nodo de visión (captura y procesamiento) y el nodo de control (vuelo y motores) mediante el sistema de publicación/suscripción de tópicos[cite: 273, 278, 988].



* [cite_start]**Librerías clave:** OpenCV para el tratamiento de imágenes y TensorFlow/Keras para la ejecución de modelos de IA si fuera necesario[cite: 245, 301, 309].
* [cite_start]**Comunicación:** El protocolo *rosserial* o enlaces UART permiten conectar la lógica de alto nivel con el hardware del dron de forma eficiente[cite: 403, 487].

---

## 5. Referencias de Proyectos Similares
Existen diversas plataformas de bajo coste que sirven de precedente para este estudio:
* [cite_start]**JetBot:** Enfocado en IA mediante hardware de NVIDIA[cite: 132, 133].
* [cite_start]**OpenBot:** Utiliza la potencia de procesamiento de smartphones para la navegación[cite: 140, 141].
* [cite_start]**Makeblock Ultimate:** Sistema modular que permite la integración de Raspberry Pi para visión artificial[cite: 517, 522].

---
*Este documento forma parte de la documentación técnica del Trabajo de Fin de Grado (TFG).*
