"""YOLO edge app: object detection on camera frames pushed by UEs.

A client (a camera on a UE, a CARLA vehicle, a test script) posts JPEG frames. The app
runs YOLO on each frame, keeps the latest raw and annotated frame per actor and camera,
and serves them as images, MJPEG streams and JSON detections.

    POST /ingest/frame/{camera}        multipart: frame=<jpeg>, actor_id=<id>, ts=<unix time>
    GET  /                             page with every live feed
    GET  /actors                       actors, cameras and last-seen times
    GET  /frame/{actor}/{camera}.jpg   latest frame (annotated unless ?annotated=0)
    GET  /stream/{actor}/{camera}.mjpg live MJPEG stream of the annotated frames
    GET  /detections/{actor}           latest detections per camera
    GET  /health                       liveness and the loaded model
"""
import argparse
import html
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

import cv2
import numpy as np
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse

# Feeds not updated for this long are hidden from the page and /actors.
STALE_AFTER_S = 60.0


@dataclass
class Feed:
    raw: bytes
    annotated: bytes
    detections: dict
    ts: float
    received: float
    frames: int = 0


@dataclass
class State:
    model: Optional[object] = None
    model_name: Optional[str] = None
    device: Optional[str] = None
    conf: float = 0.35
    imgsz: int = 640
    jpeg_quality: int = 85
    feeds: Dict[Tuple[str, str], Feed] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)
    infer_lock: threading.Lock = field(default_factory=threading.Lock)


state = State()


def load_model(path: Optional[str], device: Optional[str]):
    if not path:
        return
    from ultralytics import YOLO  # imported here so the app also runs without the inference stack

    state.model = YOLO(path)
    state.model_name = path
    state.device = device
    # One warm-up pass, so the first real frame does not pay for initialization.
    state.model.predict(np.zeros((state.imgsz, state.imgsz, 3), np.uint8), imgsz=state.imgsz,
                        device=device, verbose=False)
    # Report the device the predictor actually picked (cpu or cuda:N), not the request.
    state.device = str(state.model.predictor.device)


def detect(img: np.ndarray) -> Tuple[dict, np.ndarray]:
    if state.model is None:
        return {"total": 0, "objects": {}}, img
    with state.infer_lock:
        result = state.model.predict(img, conf=state.conf, imgsz=state.imgsz, device=state.device,
                                     verbose=False)[0]
    objects: Dict[str, dict] = {}
    for cls, conf in zip(result.boxes.cls.tolist(), result.boxes.conf.tolist()):
        name = result.names[int(cls)]
        entry = objects.setdefault(name, {"count": 0, "best_conf": 0.0})
        entry["count"] += 1
        entry["best_conf"] = round(max(entry["best_conf"], conf), 4)
    return {"total": sum(o["count"] for o in objects.values()), "objects": objects}, result.plot()


def live_feeds():
    now = time.time()
    with state.lock:
        return {k: v for k, v in state.feeds.items() if now - v.received < STALE_AFTER_S}


app = FastAPI(title="YOLO edge app")
# Read-only endpoints may be embedded by other pages (dashboards, the MX-UI).
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"])


@app.get("/health")
def health():
    return {"ok": True, "model": state.model_name, "device": state.device, "feeds": len(live_feeds())}


@app.post("/ingest/frame/{camera}")
def ingest_frame(
    camera: str,
    frame: UploadFile = File(...),
    actor_id: Optional[str] = Form(default=None),
    truck_id: Optional[str] = Form(default=None),  # older clients send truck_id
    ts: float = Form(default=0.0),
):
    actor = actor_id or truck_id or "default"
    raw = frame.file.read()
    img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR) if raw else None
    if img is None:
        raise HTTPException(400, "frame is not a decodable image")
    detections, annotated = detect(img)
    ok, enc = cv2.imencode(".jpg", annotated, [int(cv2.IMWRITE_JPEG_QUALITY), state.jpeg_quality])
    now = time.time()
    with state.lock:
        previous = state.feeds.get((actor, camera))
        state.feeds[(actor, camera)] = Feed(
            raw=raw, annotated=enc.tobytes() if ok else raw, detections=detections,
            ts=ts or now, received=now, frames=(previous.frames if previous else 0) + 1)
    return {"ok": True, "actor_id": actor, "camera": camera, "detections": detections}


def get_feed(actor: str, camera: str) -> Feed:
    with state.lock:
        feed = state.feeds.get((actor, camera))
    if feed is None:
        raise HTTPException(404, f"no frame from {actor}/{camera} yet")
    return feed


@app.get("/actors")
def actors():
    now = time.time()
    out: Dict[str, dict] = {}
    for (actor, camera), feed in sorted(live_feeds().items()):
        out.setdefault(actor, {})[camera] = {
            "last_seen_s": round(now - feed.received, 2), "frames": feed.frames, "detections": feed.detections}
    return out


@app.get("/detections/{actor}")
def detections(actor: str):
    feeds = {cam: f.detections for (a, cam), f in live_feeds().items() if a == actor}
    if not feeds:
        raise HTTPException(404, f"no frames from {actor}")
    return JSONResponse({"actor_id": actor, "cameras": feeds})


@app.get("/frame/{actor}/{camera}.jpg")
def frame(actor: str, camera: str, annotated: int = 1):
    feed = get_feed(actor, camera)
    return Response(feed.annotated if annotated else feed.raw, media_type="image/jpeg",
                    headers={"Cache-Control": "no-store"})


@app.get("/stream/{actor}/{camera}.mjpg")
def stream(actor: str, camera: str, annotated: int = 1):
    get_feed(actor, camera)  # 404 before starting the stream

    def frames():
        last = 0.0
        while True:
            with state.lock:
                feed = state.feeds.get((actor, camera))
            if feed is not None and feed.received != last:
                last = feed.received
                body = feed.annotated if annotated else feed.raw
                yield (b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                       + str(len(body)).encode() + b"\r\n\r\n" + body + b"\r\n")
            time.sleep(0.03)

    return StreamingResponse(frames(), media_type="multipart/x-mixed-replace; boundary=frame")


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>YOLO edge app</title>
<meta http-equiv="refresh" content="15">
<style>
body{{margin:0;background:#0f1115;color:#e6e6e6;font:14px system-ui,sans-serif}}
header{{padding:12px 16px}} h1{{font-size:16px;margin:0}} .m{{color:#9aa0a6}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,480px),1fr));gap:12px;padding:0 16px 16px}}
figure{{margin:0;background:#171a21;border-radius:8px;overflow:hidden}} img{{display:block;width:100%}}
figcaption{{padding:8px 10px}}
</style></head><body><header><h1>YOLO edge app</h1>
<div class="m">model {model} on {device}. Live feeds refresh continuously, the list every 15 s.</div></header>
<div class="grid">{cards}</div></body></html>"""


@app.get("/", response_class=HTMLResponse)
def index():
    cards = []
    for (actor, camera), feed in sorted(live_feeds().items()):
        a, c = html.escape(actor), html.escape(camera)
        objs = ", ".join(f"{html.escape(k)} {v['count']}" for k, v in feed.detections["objects"].items()) or "none"
        cards.append(f'<figure><img src="stream/{a}/{c}.mjpg" alt="{a} {c}">'
                     f"<figcaption><b>{a}</b> / {c} <span class=m>objects: {objs}</span></figcaption></figure>")
    if not cards:
        cards.append('<p class="m">No feed yet. POST JPEG frames to /ingest/frame/&lt;camera&gt;.</p>')
    return PAGE.format(model=html.escape(str(state.model_name)), device=html.escape(str(state.device or "auto")),
                       cards="".join(cards))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=9000)
    p.add_argument("--model", default=None, help="YOLO weights, e.g. /app/yolo11n.pt. Without it, frames pass through.")
    p.add_argument("--device", default=None, help="cpu, cuda or cuda:0. Default: GPU if PyTorch sees one.")
    p.add_argument("--conf", type=float, default=0.35, help="confidence threshold")
    p.add_argument("--imgsz", type=int, default=640, help="inference image size")
    args = p.parse_args()
    state.conf, state.imgsz = args.conf, args.imgsz
    load_model(args.model, args.device)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
