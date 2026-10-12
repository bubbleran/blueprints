"""CARLA camera client for a soft UE.

Drives an ego vehicle on autopilot in a CARLA world, takes the frames of a camera
mounted on it, and posts them as JPEG to the YOLO edge app. The CARLA connection uses
the Pod network. The frames leave through the UE's 5G tunnel interface, so only the
UE -> edge-app hop crosses the RAN.

Settings come from environment variables, see the CONFIG block.
"""
import logging
import os
import queue
import random
import signal
import socket
import sys
import threading
import time

import carla
import cv2
import numpy as np
import requests
from requests.adapters import HTTPAdapter
from urllib3.connection import HTTPConnection

# ── CONFIG ─────────────────────────────────────────────────────────────────
CARLA_HOST = os.environ.get("CARLA_HOST", "carla")
CARLA_PORT = int(os.environ.get("CARLA_PORT", "2000"))
TM_PORT = int(os.environ.get("TM_PORT", "8000"))
CARLA_MAP = os.environ.get("CARLA_MAP", "")  # empty keeps the loaded map
YOLO_URL = os.environ.get("YOLO_URL", "http://yolo-edge:9000").rstrip("/")
CAMERA = os.environ.get("CAMERA", "front")  # the YOLO app accepts front or rear
# Identifies this vehicle's feed in the YOLO app. Sent as actor_id, and as truck_id for older apps.
ACTOR_ID = os.environ.get("ACTOR_ID", socket.gethostname())
INTERFACE = os.environ.get("INTERFACE_5G", "oaitun_ue1")  # empty: no binding
FPS = float(os.environ.get("FPS", "10"))
WIDTH = int(os.environ.get("WIDTH", "800"))
HEIGHT = int(os.environ.get("HEIGHT", "450"))
FOV = float(os.environ.get("FOV", "90"))
JPEG_QUALITY = int(os.environ.get("JPEG_QUALITY", "80"))
NPC_VEHICLES = int(os.environ.get("NPC_VEHICLES", "30"))
NPC_WALKERS = int(os.environ.get("NPC_WALKERS", "20"))
EGO_FILTER = os.environ.get("EGO_FILTER", "vehicle.tesla.model3")
SEED = int(os.environ.get("SEED", "0")) or None

log = logging.getLogger("carla-client")
stop = threading.Event()


class BoundAdapter(HTTPAdapter):
    """Binds every connection to one network interface (SO_BINDTODEVICE)."""

    def __init__(self, interface, **kwargs):
        self.socket_options = HTTPConnection.default_socket_options + [
            (socket.SOL_SOCKET, socket.SO_BINDTODEVICE, interface.encode())
        ]
        super().__init__(**kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs["socket_options"] = self.socket_options
        super().init_poolmanager(*args, **kwargs)


def wait_for_interface(name):
    path = f"/sys/class/net/{name}"
    while not stop.is_set() and not os.path.exists(path):
        log.info("waiting for %s", name)
        stop.wait(5)


def connect():
    while not stop.is_set():
        try:
            client = carla.Client(CARLA_HOST, CARLA_PORT)
            client.set_timeout(20.0)
            log.info("CARLA server %s, client %s", client.get_server_version(), client.get_client_version())
            return client
        except RuntimeError as err:
            log.warning("CARLA %s:%d not ready: %s", CARLA_HOST, CARLA_PORT, err)
            stop.wait(10)
    return None


def spawn_world(client, actors):
    world = client.get_world()
    if CARLA_MAP and not world.get_map().name.endswith(CARLA_MAP):
        world = client.load_world(CARLA_MAP)
    rng = random.Random(SEED)
    lib = world.get_blueprint_library()
    spawn_points = world.get_map().get_spawn_points()
    rng.shuffle(spawn_points)
    tm = client.get_trafficmanager(TM_PORT)
    tm.set_global_distance_to_leading_vehicle(2.5)

    ego_bp = (lib.filter(EGO_FILTER) or lib.filter("vehicle.*"))[0]
    ego_bp.set_attribute("role_name", "hero")
    ego = None
    for sp in spawn_points:
        ego = world.try_spawn_actor(ego_bp, sp)
        if ego:
            break
    if ego is None:
        raise RuntimeError("no free spawn point for the ego vehicle")
    actors.append(ego)
    ego.set_autopilot(True, TM_PORT)

    cars = [bp for bp in lib.filter("vehicle.*") if int(bp.get_attribute("number_of_wheels")) == 4]
    npcs = 0
    for sp in spawn_points[1:1 + NPC_VEHICLES]:
        npc = world.try_spawn_actor(rng.choice(cars), sp)
        if npc:
            npc.set_autopilot(True, TM_PORT)
            actors.append(npc)
            npcs += 1

    walkers = 0
    controller_bp = lib.find("controller.ai.walker")
    for _ in range(NPC_WALKERS):
        loc = world.get_random_location_from_navigation()
        if loc is None:
            continue
        walker = world.try_spawn_actor(rng.choice(lib.filter("walker.pedestrian.*")), carla.Transform(loc))
        if walker is None:
            continue
        ctrl = world.spawn_actor(controller_bp, carla.Transform(), attach_to=walker)
        ctrl.start()
        ctrl.go_to_location(world.get_random_location_from_navigation())
        actors.extend([ctrl, walker])
        walkers += 1

    cam_bp = lib.find("sensor.camera.rgb")
    cam_bp.set_attribute("image_size_x", str(WIDTH))
    cam_bp.set_attribute("image_size_y", str(HEIGHT))
    cam_bp.set_attribute("fov", str(FOV))
    cam_bp.set_attribute("sensor_tick", str(1.0 / FPS))
    cam = world.spawn_actor(cam_bp, carla.Transform(carla.Location(x=1.5, z=1.6)), attach_to=ego)
    actors.append(cam)
    log.info("map %s, ego %s, %d NPC vehicles, %d walkers, camera %dx%d at %.0f fps",
             world.get_map().name, ego.type_id, npcs, walkers, WIDTH, HEIGHT, FPS)
    return cam


def sender(frames, stats):
    session = requests.Session()
    if INTERFACE:
        session.mount("http://", BoundAdapter(INTERFACE))
    url = f"{YOLO_URL}/ingest/frame/{CAMERA}"
    while not stop.is_set():
        try:
            jpeg, ts = frames.get(timeout=1)
        except queue.Empty:
            continue
        if INTERFACE and not os.path.exists(f"/sys/class/net/{INTERFACE}"):
            stats["dropped"] += 1
            continue
        t0 = time.time()
        try:
            r = session.post(url, files={"frame": ("frame.jpg", jpeg, "image/jpeg")},
                             data={"actor_id": ACTOR_ID, "truck_id": ACTOR_ID, "ts": str(ts)}, timeout=5)
            r.raise_for_status()
            stats["sent"] += 1
            stats["bytes"] += len(jpeg)
            stats["rtt"] += time.time() - t0
            stats["objects"] = r.json().get("detections", {}).get("total", 0)
        except (requests.RequestException, OSError) as err:
            stats["errors"] += 1
            stats["last_error"] = str(err)[:200]
            stop.wait(1)


def report(stats):
    last = dict(stats)
    while not stop.wait(10):
        cur = dict(stats)
        sent = cur["sent"] - last["sent"]
        rtt = (cur["rtt"] - last["rtt"]) / sent * 1000 if sent else 0
        mbps = (cur["bytes"] - last["bytes"]) * 8 / 10 / 1e6
        log.info("sent %.1f fps, %.2f Mbit/s, rtt %.0f ms, objects %s, dropped %d, errors %d%s",
                 sent / 10, mbps, rtt, cur["objects"], cur["dropped"] - last["dropped"],
                 cur["errors"] - last["errors"],
                 f" (last: {cur['last_error']})" if cur["errors"] > last["errors"] else "")
        last = cur


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    log.info("CARLA %s:%d -> %s/ingest/frame/%s via %s as %s",
             CARLA_HOST, CARLA_PORT, YOLO_URL, CAMERA, INTERFACE or "default route", ACTOR_ID)
    if INTERFACE:
        wait_for_interface(INTERFACE)

    client = connect()
    if client is None:
        return
    actors = []
    frames = queue.Queue(maxsize=1)  # latest frame only, never queue up stale ones
    stats = {"sent": 0, "bytes": 0, "rtt": 0.0, "objects": 0, "dropped": 0, "errors": 0, "last_error": ""}

    def on_image(image):
        bgra = np.frombuffer(image.raw_data, dtype=np.uint8).reshape(image.height, image.width, 4)
        ok, enc = cv2.imencode(".jpg", bgra[:, :, :3], [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
        if not ok:
            return
        try:
            frames.get_nowait()
            stats["dropped"] += 1
        except queue.Empty:
            pass
        frames.put_nowait((enc.tobytes(), time.time()))

    try:
        cam = spawn_world(client, actors)
        cam.listen(on_image)
        threading.Thread(target=sender, args=(frames, stats), daemon=True).start()
        threading.Thread(target=report, args=(stats,), daemon=True).start()
        while not stop.wait(1):
            pass
    finally:
        log.info("destroying %d actors", len(actors))
        for a in actors:
            if a.type_id.startswith("sensor."):
                a.stop()
        client.apply_batch([carla.command.DestroyActor(a) for a in actors])


if __name__ == "__main__":
    main()
