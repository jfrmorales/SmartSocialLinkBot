
# SmartSocialLinkBot

![SmartSocialLinkBot Logo](assets/logo.webp)

[![Support me on Ko-fi](https://storage.ko-fi.com/cdn/kofi2.png?v=3)](https://ko-fi.com/S6S119KZVL)

SmartSocialLinkBot es un bot para Telegram diseñado para manejar enlaces de redes sociales (Instagram, Twitter/X, TikTok) en grupos autorizados. Este bot puede corregir enlaces mal formateados, reemplazar dominios específicos y asegurar que los enlaces sean compartidos en el formato deseado.

SmartSocialLinkBot is a Telegram bot designed to handle social media links (Instagram, Twitter/X, TikTok) in authorized groups. This bot can fix malformed links, replace specific domains, and ensure links are shared in the desired format.

---

## Características principales / Key Features

### Gestión de grupos / Group Management
- **Lista blanca de grupos / White-listed Groups:** El bot funciona solo en los grupos autorizados previamente.
- **Registro automático de grupos / Automatic Group Registration:** Si el administrador del bot lo añade a un grupo, este se registra automáticamente en la base de datos.
- **Expulsión automática / Automatic Expulsion:** Si el bot es añadido a un grupo no autorizado, se expulsa automáticamente.

### Procesamiento de enlaces / Link Processing
- **Corrección de enlaces mal formateados / Malformed Link Correction:** Normaliza enlaces mal formados, por ejemplo:
  - `https://fixupfixupx.com` → `https://fixupx.com`
  - `https://instagram.com` → `https://ddinstagram.com`
- **Reemplazo de dominios / Domain Replacement:** Cambia automáticamente dominios de redes sociales según las reglas configuradas.
  - `instagram.com` → `ddinstagram.com`
  - `twitter.com` o `x.com` → `fixupx.com`
  - `tiktok.com` → `vxtiktok.com`

### Manejo de permisos / Permissions Handling
- **Edición o eliminación de mensajes / Message Editing or Deletion:** Si el bot tiene permisos para eliminar mensajes, elimina el original y envía uno nuevo con el enlace corregido.
- **Respuestas alternativas / Alternative Replies:** Si el bot no tiene permisos para eliminar mensajes, responde al mensaje original con el enlace corregido.

---

## Comandos disponibles / Available Commands

### Administrador / Admin
Estos comandos solo pueden ser ejecutados por el administrador registrado en el bot:

These commands can only be executed by the registered admin of the bot:

- `/menu` - Muestra un menú interactivo con botones para administrar el bot. / Displays an interactive menu with buttons to manage the bot.
- `/listar_grupos` - Lista todos los grupos donde el bot está autorizado. / Lists all groups where the bot is authorized.
- `/agregar_grupo <ID_GRUPO>` - Agrega manualmente un grupo a la lista autorizada. / Manually adds a group to the authorized list.
- `/eliminar_grupo <ID_GRUPO>` - Elimina un grupo de la lista autorizada y expulsa al bot del mismo. / Removes a group from the authorized list and expels the bot from it.
- `/help` - Muestra una lista de comandos disponibles. / Displays a list of available commands.

---

## Instalación / Installation

### Requisitos / Requirements
- Python 3.10 o superior / Python 3.10 or higher.
- MongoDB para almacenar la base de datos de grupos / MongoDB to store the group database.
- Docker y Docker Compose (opcional para despliegue) / Docker and Docker Compose (optional for deployment).

### Configuración / Setup
1. Clona este repositorio / Clone this repository:
   ```bash
   git clone <url_del_repositorio>
   cd SmartSocialLinkBot
   ```

2. Crea un archivo `.env` en el directorio `config` con el siguiente contenido / Create a `.env` file in the `config` directory with the following content:
   ```env
   BOT_TOKEN=<tu_bot_token / your_bot_token>
   ADMIN_ID=<tu_id_de_administrador / your_admin_id>
   MONGO_URI=<uri_de_mongodb / your_mongodb_uri>
   DB_NAME=telegram_bot
   ```

3. Instala las dependencias / Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Ejecuta el bot / Run the bot:
   ```bash
   python main.py
   ```

---

## Uso con Docker / Using Docker

1. Construye la imagen de Docker / Build the Docker image:
   ```bash
   docker build -t smartsociallinkbot .
   ```

2. Configura el archivo `docker-compose.yml` / Set up the `docker-compose.yml` file:
   ```yaml
   services:
     bot:
       build: .
       container_name: smartsociallinkbot
       env_file:
         - ./config/.env
       volumes:
         - ./config:/app/config:ro
       restart: always
     mongodb:
       image: mongo:5.0
       container_name: mongodb
       restart: always
       ports:
         - "27017:27017"
   ```

3. Inicia los contenedores / Start the containers:
   ```bash
   docker-compose up -d
   ```

---

## Arquitectura del proyecto / Project Architecture

```
SmartSocialLinkBot/
├── main.py                # Archivo principal para inicializar el bot / Main file to initialize the bot
├── commands.py            # Comandos del bot / Bot commands
├── handlers.py            # Lógica de procesamiento de mensajes / Message processing logic
├── db.py                  # Conexión y manejo de la base de datos / Database connection and handling
├── config/
│   └── .env               # Archivo de configuración del bot / Bot configuration file
├── requirements.txt       # Dependencias del proyecto / Project dependencies
├── Dockerfile             # Configuración para Docker / Docker configuration
└── docker-compose.yml     # Configuración para Docker Compose / Docker Compose configuration
```

---

## Funcionalidades futuras / Future Features
- Integración con nuevas redes sociales / Integration with new social networks.
- Analíticas de uso del bot / Bot usage analytics.

---

## Contribuciones / Contributions
¡Contribuciones son bienvenidas! Si tienes ideas o encuentras problemas, no dudes en abrir un issue o enviar un pull request.

Contributions are welcome! If you have ideas or encounter issues, feel free to open an issue or submit a pull request.

---

## Licencia / License
Este proyecto está licenciado bajo la [Licencia MIT / MIT License](LICENSE).
