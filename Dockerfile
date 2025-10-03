# Dockerfile
FROM python:3.11-slim

# Prevents Python from writing .pyc and buffers
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instala deps del sistema necesarios para pip y curl (healthcheck)
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential curl \
 && rm -rf /var/lib/apt/lists/*

# Copia requirements e instala dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el código
COPY . .

# Crea usuario no-root y carpeta de uploads
RUN useradd -m appuser \
 && mkdir -p /app/uploads \
 && chown -R appuser:appuser /app

USER appuser

# Exponer puerto
EXPOSE 5000

# Healthcheck (opcional, requiere curl en la imagen)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://192.168.178.139:5000/ || exit 1

# Ejecutar con Gunicorn (3 workers por defecto; ajustá según CPU)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "3", "app:app"]
