# Guía para subir el proyecto a GitHub

He detectado que aún no has configurado tu identidad en Git en este ordenador. Ejecuta estos comandos uno a uno en tu terminal:

1.  **Configura tu usuario** (sustituye tu email):
    ```bash
    git config user.name "Eugegeuge"
    git config user.email "TU_EMAIL_AQUI"
    ```

2.  **Guarda los archivos**:
    ```bash
    git add .
    git commit -m "Initial commit: Drone Tracker with Webcam"
    ```

3.  **Conecta con GitHub y Sube**:
    ```bash
    git branch -M main
    git remote add origin https://github.com/Eugegeuge/drone-tracker.git
    git push -u origin main
    ```
    *(Te pedirá tu usuario `Eugegeuge` y tu Token/Contraseña)*

¡Y listo! Ya tendrás el código en tu repositorio.
