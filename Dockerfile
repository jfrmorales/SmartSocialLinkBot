# Usa una imagen base de Python
FROM python:3.10-slim

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar los archivos necesarios
COPY requirements.txt .
COPY *.py .
COPY config/.env ./config/.env

# Instalar las dependencias del bot
RUN pip install --no-cache-dir -r requirements.txt

# Configurar el comando de inicio del contenedor
CMD ["python", "main.py"]
