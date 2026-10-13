FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

# The CARLA client library must match the server version.
ARG CARLA_VERSION=0.9.16
RUN pip install "carla==${CARLA_VERSION}" numpy opencv-python-headless

WORKDIR /app
COPY viewer.py /app/viewer.py

EXPOSE 8080
CMD ["python", "/app/viewer.py"]
