FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

# The CARLA client must match the server version.
ARG CARLA_VERSION=0.9.16
RUN pip install "carla==${CARLA_VERSION}" numpy opencv-python-headless requests

WORKDIR /app
COPY carla_client.py /app/carla_client.py

CMD ["python", "/app/carla_client.py"]
