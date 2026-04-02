# Guía de Puesta en Marcha: DJI Tello

¡Genial que ya tengas el dron! Aquí tienes los pasos para encenderlo y conectarlo a tu ordenador.

## 1. Encendido
1.  Inserta la **batería** en el dron.
2.  Busca el botón en el lateral del dron.
3.  Púlsalo una vez brevemente y verás que no hace nada... **Tienes que pulsarlo y soltarlo**.
    *   *Nota*: A veces hay que pulsarlo una vez rápido y luego dejarlo pulsado unos segundos hasta que las luces parpadeen.
    *   Lo normal en el Tello es **un botón lateral**: Púlsalo. Las luces (LEDs) al lado de la cámara deberían parpadear (inicialmente en colores variados, luego parpadearán en **amarillo rápido** indicando que está listo para conectar pero no conectado).

## 2. Conexión Wi-Fi
El Tello crea su propia red Wi-Fi para comunicarse.
1.  Ve a la configuración de Wi-Fi de tu ordenador (Ubuntu).
2.  Busca una red que se llame algo como `TELLO-XXXXXX`.
3.  Conéctate a ella.
    *   No tiene contraseña por defecto.
    *   Es normal que tu ordenador diga "Sin conexión a Internet". Es correcto.

## 3. Preparación del Entorno
Una vez conectado al Wi-Fi del Tello:
1.  Asegúrate de tener luz suficiente (el Tello usa una cámara inferior para estabilizarse, si está muy oscuro no volará bien).
2.  Pon el dron en el suelo, en una zona despejada (al menos 2x2 metros).

## 4. Ejecución del Código (Una vez conectado al WiFi)
Abre tu terminal en la carpeta del proyecto y ejecuta:
```bash
./venv/bin/python3 tracker.py
```

## Preguntas Frecuentes

### ¿Necesito la app del móvil?
**No**. Para este programa, tu ordenador actúa como el mando a través del Wi-Fi. No necesitas tener la app de Tello abierta (de hecho, si la tienes abierta podría interferir, ciérrala).

### ¿Necesito conectar algún cable?
**No**. La comunicación es 100% por Wi-Fi.

### ¿Qué pasa si el script falla al arrancar?
-   Asegúrate de estar **conectado al WiFi del Tello**.
-   Asegúrate de que no tienes un Firewall bloqueando las conexiones (en Ubuntu suele estar abierto por defecto, pero si usas `ufw`, permite el tráfico UDP).

