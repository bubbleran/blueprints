FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    YOLO_CONFIG_DIR=/tmp/Ultralytics

WORKDIR /app

# PyTorch wheel index: CPU by default. For an NVIDIA GPU use a CUDA build the node's
# driver supports, for example https://download.pytorch.org/whl/cu128 (see README).
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
# YOLO weights baked into the image, so the Pod needs no internet access at start.
ARG YOLO_WEIGHTS=yolo11n.pt

# OpenCV, pulled in by ultralytics, needs libGL and glib. curl serves the probes in a
# managed (CompositionModel) deployment.
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --index-url "$TORCH_INDEX_URL" torch torchvision
COPY requirements.txt /app/
RUN pip install -r /app/requirements.txt

RUN python -c "from ultralytics import YOLO; YOLO('$YOLO_WEIGHTS')" && mv "$YOLO_WEIGHTS" /app/model.pt

COPY app.py /app/app.py

EXPOSE 9000

# A managed deployment cannot override the command, so the default CMD runs inference.
CMD ["python", "/app/app.py", "--host", "0.0.0.0", "--port", "9000", "--model", "/app/model.pt"]
