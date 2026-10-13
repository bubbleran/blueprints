"""CARLA viewer: watch the simulation from a browser.

Follows a vehicle in a running CARLA world with two cameras, one chasing it from behind and
one looking straight down at it, and serves both as MJPEG streams on a small web page. The
viewer never advances the simulation: in synchronous mode it receives its frames on the
ticks of the client that drives the world.

    GET /                 page with both views
    GET /chase.mjpg       chase camera stream
    GET /top.mjpg         top-down camera stream
    GET /health           status: CARLA connection, followed vehicle
"""
import json
import logging
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import carla
import cv2
import numpy as np

def port_env(name, default):
    """Reads a port from the environment. Kubernetes also defines <SERVICE>_PORT as
    tcp://<ip>:<port> for every Service in the namespace, so a Service named carla sets
    CARLA_PORT to that form: take the number after the last colon."""
    value = os.environ.get(name, str(default)).strip()
    return int(value.rsplit(":", 1)[-1])


CARLA_HOST = os.environ.get("CARLA_HOST", "carla")
CARLA_PORT = port_env("CARLA_PORT", 2000)
FOLLOW_ROLE = os.environ.get("FOLLOW_ROLE", "hero")  # role_name of the vehicle to follow
PORT = int(os.environ.get("PORT", "8080"))
FPS = float(os.environ.get("FPS", "10"))
WIDTH = int(os.environ.get("WIDTH", "960"))
HEIGHT = int(os.environ.get("HEIGHT", "540"))
TOP_HEIGHT = float(os.environ.get("TOP_HEIGHT", "45"))  # metres above the vehicle
JPEG_QUALITY = int(os.environ.get("JPEG_QUALITY", "75"))

log = logging.getLogger("carla-viewer")
lock = threading.Lock()
frames = {"chase": None, "top": None}
status = {"carla": "connecting", "following": None, "map": None}

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>CARLA viewer</title>
<style>
body{margin:0;background:#0f1115;color:#e6e6e6;font:14px system-ui,sans-serif}
header{padding:12px 16px} h1{font-size:16px;margin:0} .m{color:#9aa0a6}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,520px),1fr));gap:12px;padding:0 16px 16px}
figure{margin:0;background:#171a21;border-radius:8px;overflow:hidden}
img{display:block;width:100%;aspect-ratio:16/9;object-fit:contain;background:#000}
figcaption{padding:8px 10px}
</style></head><body><header><h1>CARLA viewer</h1><div class="m" id="s">connecting</div></header>
<div class="grid">
<figure><img src="chase.mjpg" alt="chase camera"><figcaption>Chase camera</figcaption></figure>
<figure><img src="top.mjpg" alt="top-down camera"><figcaption>Top-down camera</figcaption></figure>
</div>
<script>
async function poll(){try{const h=await (await fetch('health')).json();
document.getElementById('s').textContent=h.following?`following ${h.following} on ${h.map}`:`CARLA ${h.carla}, waiting for a vehicle with role ${h.role}`;}catch(e){}
setTimeout(poll,3000)} poll();
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/health":
            with lock:
                body = json.dumps({"ok": True, "role": FOLLOW_ROLE, **status}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path in ("/chase.mjpg", "/top.mjpg"):
            self.stream(self.path[1:].split(".")[0])
        else:
            self.send_error(404)

    def stream(self, view):
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        last = None
        try:
            while True:
                with lock:
                    jpeg = frames[view]
                if jpeg is not None and jpeg is not last:
                    last = jpeg
                    self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                                     + str(len(jpeg)).encode() + b"\r\n\r\n" + jpeg + b"\r\n")
                time.sleep(0.03)
        except (BrokenPipeError, ConnectionResetError):
            pass


def on_image(view):
    def callback(image):
        bgra = np.frombuffer(image.raw_data, dtype=np.uint8).reshape(image.height, image.width, 4)
        ok, enc = cv2.imencode(".jpg", bgra[:, :, :3], [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
        if ok:
            with lock:
                frames[view] = enc.tobytes()
    return callback


def camera_blueprint(world, fov):
    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(WIDTH))
    bp.set_attribute("image_size_y", str(HEIGHT))
    bp.set_attribute("fov", str(fov))
    bp.set_attribute("sensor_tick", str(1.0 / FPS))
    return bp


def follow_loop():
    """Attaches the two cameras to the followed vehicle, and again whenever it changes."""
    while True:
        cameras, target = [], None
        try:
            client = carla.Client(CARLA_HOST, CARLA_PORT)
            client.set_timeout(20.0)
            world = client.get_world()
            with lock:
                status.update(carla="connected", map=world.get_map().name.split("/")[-1])
            while True:
                vehicles = [v for v in world.get_actors().filter("vehicle.*")
                            if v.attributes.get("role_name") == FOLLOW_ROLE]
                if target is None or target.id not in {v.id for v in vehicles}:
                    for cam in cameras:
                        cam.stop()
                        cam.destroy()
                    cameras, target = [], None
                    with lock:
                        status["following"] = None
                    if vehicles:
                        target = vehicles[0]
                        chase = world.spawn_actor(camera_blueprint(world, 90), carla.Transform(
                            carla.Location(x=-7.0, z=3.5), carla.Rotation(pitch=-12.0)), attach_to=target,
                            attachment_type=carla.AttachmentType.SpringArmGhost)
                        top = world.spawn_actor(camera_blueprint(world, 80), carla.Transform(
                            carla.Location(z=TOP_HEIGHT), carla.Rotation(pitch=-90.0)), attach_to=target)
                        chase.listen(on_image("chase"))
                        top.listen(on_image("top"))
                        cameras = [chase, top]
                        with lock:
                            status["following"] = f"{target.type_id} (id {target.id})"
                        log.info("following %s id %d", target.type_id, target.id)
                time.sleep(2)
        except RuntimeError as err:
            log.warning("CARLA %s:%d: %s", CARLA_HOST, CARLA_PORT, err)
            with lock:
                status.update(carla=f"unreachable ({str(err)[:80]})", following=None)
            for cam in cameras:
                try:
                    cam.destroy()
                except RuntimeError:
                    pass
            time.sleep(5)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
    threading.Thread(target=follow_loop, daemon=True).start()
    log.info("serving on :%d, following role %s on %s:%d", PORT, FOLLOW_ROLE, CARLA_HOST, CARLA_PORT)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
