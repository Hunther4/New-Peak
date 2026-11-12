# Despliegue de New Peak en Hugging Face Spaces (24/7 Gratuito)

Esta guía explica cómo desplegar New Peak en Hugging Face Spaces utilizando Docker. Permite disponer de la aplicación completa (Frontend React, Backend FastAPI y base de datos SQLite) disponible 24/7 de forma gratuita, accesible desde cualquier dispositivo y lista para instalar como PWA en tu teléfono móvil.

---

### Paso 1: Crear el Space en Hugging Face

1. Inicia sesión o regístrate en [Hugging Face](https://huggingface.co/).
2. Ingresa a la sección de creación de Spaces: [https://huggingface.co/new-space](https://huggingface.co/new-space).
3. Completa los campos solicitados:
   - **Space name**: Asigna un nombre (por ejemplo, `new-peak` o `paes-peak`).
   - **License**: Selecciona la licencia del proyecto (por ejemplo, `mit`).
   - **Select the Space SDK**: Selecciona **Docker** (opción `Blank`).
   - **Space hardware**: Selecciona la opción gratuita `CPU basic · 2 vCPU · 16 GB · Free`.
   - **Space visibility**: Selecciona `Public` para acceder sin restricciones o `Private` si deseas limitar el acceso a tu cuenta.
4. Haz clic en el botón **Create Space**.

---

### Paso 2: Subir o Vincular el Repositorio

Puedes subir el código directamente mediante Git o configurar sincronización continua desde tu repositorio de GitHub (`Hunther4/New-Peak`).

#### Opción A: Subir directamente con Git (Recomendada)

Desde tu terminal local, dentro del directorio del proyecto (`New Peak`):

```bash
# 1. Agrega el remoto de Hugging Face Spaces (reemplaza <tu-usuario> y <nombre-space>)
git remote add space https://huggingface.co/spaces/<tu-usuario>/<nombre-space>

# 2. Sube la rama principal a Hugging Face
git push space main
```

> **Nota de autenticación:** Si Git solicita credenciales al ejecutar `git push`, introduce tu nombre de usuario de Hugging Face y utiliza como contraseña un **User Access Token** (con permisos de escritura `Write`), el cual puedes generar en Hugging Face desde **Settings > Access Tokens**.

#### Opción B: Sincronización automática desde GitHub

Si deseas que cada cambio enviado a tu repositorio en GitHub (`Hunther4/New-Peak`) se sincronice automáticamente con tu Space:

1. En tu repositorio de GitHub, dirígete a **Settings > Secrets and variables > Actions**.
2. Haz clic en **New repository secret** y crea un secreto llamado `HF_TOKEN` con tu Access Token de Hugging Face (permiso `write`).
3. Puedes utilizar un flujo de trabajo de GitHub Actions (`.github/workflows/sync_hf.yml`) que ejecute:
   ```bash
   git push https://<tu-usuario>:$HF_TOKEN@huggingface.co/spaces/<tu-usuario>/<nombre-space> main:main --force
   ```

#### Variables de Entorno y Secretos (Opcional)

En la pestaña **Settings** de tu Space, en el apartado **Variables and secrets**, puedes configurar las siguientes variables según lo requieras:

- `PEAK_API_KEY`: Clave fija para autenticar llamadas a la API (si no se define, se genera automáticamente una clave al iniciar).
- `GROQ_API_KEY`: Clave de API de Groq para aceleración de inferencia del tutor de IA.
- `OPENROUTER_API_KEY`: Clave de API de OpenRouter como proveedor alternativo de modelos de lenguaje.

---

### Paso 3: Acceder e Instalar la PWA en el Teléfono Móvil

Cuando el contenedor termine de compilar e iniciar, el estado en la parte superior cambiará a **Running**.

1. **Obtener la URL pública directa del Space:**
   - Cada Space cuenta con un dominio directo con el siguiente formato:
     ```text
     https://<tu-usuario>-<nombre-space>.hf.space
     ```
   - También puedes obtener el enlace directo haciendo clic en los tres puntos verticales (`⋮`) en la esquina superior derecha del Space y seleccionando **Embed this Space** > **Direct URL**.

2. **Instalar la aplicación (PWA) en tu teléfono móvil:**
   - Abre la URL directa en el navegador web de tu teléfono móvil (Google Chrome en Android o Safari en iOS).
   - **En Android (Chrome):** Presiona el menú de opciones (`⋮`) en la esquina superior derecha y selecciona **Instalar aplicación** o **Agregar a la pantalla principal**.
   - **En iOS (Safari):** Presiona el botón de **Compartir** (icono de cuadro con flecha hacia arriba) y selecciona **Agregar al inicio**.

3. **Uso continuo:**
   - Ahora puedes abrir New Peak directamente desde el icono en la pantalla de inicio de tu teléfono, disfrutando de la interfaz en pantalla completa con soporte sin conexión y disponibilidad 24/7 sin mantener tu computadora encendida.

---

### Resumen Técnico de Configuración del Contenedor

- **Usuario no-root:** El contenedor se ejecuta con el usuario sin privilegios `user` (UID 1000) de acuerdo con los lineamientos de Hugging Face Spaces.
- **Puerto expuesto:** El servicio escucha y responde en el puerto `7860` (`PORT=7860`).
- **Base de datos SQLite:** La base de datos opera en `/data/peak.db`, asegurando permisos de lectura y escritura para el usuario `user`.
- **Archivos estáticos y uploads:** Los directorios `/app/uploads/avatars` y `/app/uploads/questions` cuentan con permisos asignados para almacenar avatares y diagramas generados.
