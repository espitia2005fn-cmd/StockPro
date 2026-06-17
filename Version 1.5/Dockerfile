FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

ENV FLASK_DEBUG=0
# ⚠️ IMPORTANTE: Define SECRET_KEY como variable de entorno al ejecutar el contenedor
# docker run -e SECRET_KEY="clave-segura-aqui" -p 5000:5000 stockpro
# Si no se define, Flask generará una automáticamente con os.urandom(24).hex()

CMD ["python", "run.py"]
