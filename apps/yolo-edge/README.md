# YOLO edge app

An object-detection service that runs at the edge of a BubbleRAN cluster. Clients, typically
UEs sending camera frames over the 5G network, post JPEG frames. The app runs
[YOLO](https://docs.ultralytics.com/) on each frame and serves the annotated frames as live
streams, plus the detections as JSON.

The image is built from this directory and stored in your cluster's own registry with the
[BubbleRAN CDK](https://bubbleran.com/docs/user-guide/cdk-guide/cdk-overview), then deployed
next to the RAN and the core.

| File | Purpose |
|---|---|
| `app.py` | The service (FastAPI). |
| `Dockerfile` | Builds the image, with the YOLO weights baked in. |
| `requirements.txt` | Python dependencies, except PyTorch, which the Dockerfile installs. |
| `app.yaml` | CDK spec for the CPU variant. |
| `app-gpu.yaml` | CDK spec for an NVIDIA GPU. |

## Prerequisites

- A BubbleRAN cluster with the cluster-local registry, `registry.<cluster>.local:5000`, which
  gaia installs when the cluster is provisioned with the registry feature.
- `brc` with the `cdk app` commands (`brc cdk app --help`), run on the control-plane node.
- A `brc login` done once, so the `bubbleran-hub` secret exists. The CDK reads the registry
  credentials from it.
- `docker` on that node, with internet access for the build (PyPI, the PyTorch index and the
  YOLO weights).

`<cluster>` and `<org>` below are the cluster name of your kubeconfig. The image lands at
`registry.<cluster>.local:5000/telco-fabric/<org>/yolo-edge:latest`.

## 1. Build the image

```bash
git clone https://github.com/bubbleran/blueprints.git
cd blueprints/apps/yolo-edge
brc cdk app build
```

The build takes a few minutes and produces an image of about 1.9 GB (CPU variant).

Check the image before pushing it:

```bash
docker run --rm -d --name yolo-test -p 19000:9000 registry.<cluster>.local:5000/telco-fabric/<org>/yolo-edge:latest
curl -s localhost:19000/health
curl -sL -o bus.jpg https://ultralytics.com/images/bus.jpg
curl -s -F frame=@bus.jpg -F actor_id=test localhost:19000/ingest/frame/front
docker rm -f yolo-test
```

```
{"ok":true,"model":"/app/model.pt","device":"cpu","feeds":0}
{"ok":true,"actor_id":"test","camera":"front","detections":{"total":5,"objects":{"bus":{"count":1,"best_conf":0.9402},"person":{"count":4,"best_conf":0.8882}}}}
```

## 2. Push it to the cluster-local registry

```bash
brc cdk app push
```

The image stays in your cluster. The CDK logs in with the `bubbleran-hub` credentials.

## 3. Deploy it

```bash
brc cdk app deploy
kubectl get deploy,svc,pod -n trirematics -l cdk.bubbleran.io/edge-app=yolo-edge
```

This runs the app in the `trirematics` namespace as a detached edge app, behind the
ClusterIP Service `yolo-edge` on port 9000. It is not part of any Network, so it keeps
running when Networks come and go.

## 4. Send frames

Any client that can reach the Service can post frames:

```bash
curl -s -F frame=@bus.jpg -F actor_id=car1 http://yolo-edge.trirematics.svc.cluster.local:9000/ingest/frame/front
```

To send them through the 5G network instead of the Pod network, send from a UE and bind
to its tunnel interface. For an OAI soft UE that is `oaitun_ue1`:

```bash
kubectl cp bus.jpg trirematics/<ue-pod>:/tmp/bus.jpg -c image
kubectl exec -n trirematics deploy/<ue-deployment> -c image -- \
    curl -s --interface oaitun_ue1 -F frame=@/tmp/bus.jpg -F actor_id=car1 \
    http://yolo-edge.trirematics.svc.cluster.local:9000/ingest/frame/front
```

The frames then travel UE -> gNB -> UPF -> app. With the `oai-cn/minimal` core, the UPF
source-NATs this traffic, so the app sees the UPF Pod as the client.

`actor_id` names the sender (a vehicle, a camera, a UE). Each actor and camera pair is a
separate feed. Older clients that send `truck_id` are accepted too.

## 5. Watch the result

The app's page lists every live feed with its annotated stream and the detected objects.

- **MX-UI:** the spec registers a **YOLO Edge** tab under Services.
- **Port-forward:** run
  `kubectl -n trirematics port-forward svc/yolo-edge 9000:9000`, then open
  `http://localhost:9000/`.

| Endpoint | Returns |
|---|---|
| `POST /ingest/frame/{camera}` | Runs detection on a frame. Form fields: `frame` (JPEG), `actor_id`, `ts` (optional). |
| `GET /` | Page with every live feed. |
| `GET /actors` | Actors, cameras, frame counts and the latest detections. |
| `GET /stream/{actor}/{camera}.mjpg` | Live MJPEG stream of the annotated frames. |
| `GET /frame/{actor}/{camera}.jpg` | Latest frame, annotated unless `?annotated=0`. |
| `GET /detections/{actor}` | Latest detections per camera. |
| `GET /health` | Status, model and the inference device actually in use. |

Feeds that send nothing for 60 seconds are hidden.

## Running on an NVIDIA GPU

`app-gpu.yaml` builds with CUDA PyTorch wheels and asks for one GPU and the NVIDIA runtime:

```bash
brc cdk app build -f app-gpu.yaml
brc cdk app push -f app-gpu.yaml
brc cdk app deploy -f app-gpu.yaml
```

- The cluster must expose GPUs as `nvidia.com/gpu` (NVIDIA GPU Operator or device plugin) and
  have a `nvidia` RuntimeClass: `kubectl get runtimeclass`.
- The CUDA version in `TORCH_INDEX_URL` must not be newer than the node driver supports. The
  node label `nvidia.com/cuda.runtime-version.full` gives that limit.
- Without `runtime-class: nvidia` the Pod still starts, but PyTorch sees no GPU and the app
  runs on the CPU without an error. `GET /health` shows the device actually used.
- The image is much larger, about 7 GB.

## Updating

Rebuild, push and deploy again. The specs set `image-pull-policy: Always`, so the Pod pulls the
new `:latest` image on restart:

```bash
brc cdk app build && brc cdk app push && brc cdk app deploy
```

Change the model with the `YOLO_WEIGHTS` build argument in the spec (for example
`yolo11s.pt`), and the threshold or the image size with `--conf` and `--imgsz` through the
spec's `args`.

## Removing

```bash
brc cdk app delete yolo-edge
```

This removes the Deployment and the Service. The image stays in the registry.
