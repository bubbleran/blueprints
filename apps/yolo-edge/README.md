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
brc cdk app status
brc cdk app logs
```

```
Pod      yolo-edge-55699d4b98-6prbq  Running  ready=true  restarts=0  node=mirin
         image registry.<cluster>.local:5000/telco-fabric/<org>/yolo-edge:latest
Service  yolo-edge  ClusterIP 10.102.201.39  http:9000
         in-cluster DNS yolo-edge.trirematics.svc.cluster.local
```

This runs the app in the `trirematics` namespace as a detached edge app, behind the
ClusterIP Service `yolo-edge` on port 9000. It is not part of any Network, so it keeps
running when Networks come and go. To run it as part of a Network instead, see
[Running it as part of a Network](#running-it-as-part-of-a-network).

## 4. Send frames

Any client that can reach the Service can post frames. To send them through the 5G
network, send from a UE and bind to its tunnel interface, `oaitun_ue1` for an OAI soft UE.
`brc cic <element> shell -- <command>` runs a command in the UE. The app serves a test
picture at `/sample.jpg`, so the UE needs no file and no internet access:

```bash
APP=http://yolo-edge.trirematics.svc.cluster.local:9000
brc cic <ue-element> shell -- "curl -s --interface oaitun_ue1 -o /tmp/sample.jpg $APP/sample.jpg && \
    curl -s --interface oaitun_ue1 -F frame=@/tmp/sample.jpg -F actor_id=car1 $APP/ingest/frame/front"
```

```
{"ok":true,"actor_id":"car1","camera":"front","detections":{"total":5,"objects":{"bus":{"count":1,"best_conf":0.9402},"person":{"count":4,"best_conf":0.8882}}}}
```

`<ue-element>` is the UE's Element name as `brc observe` lists it, for example
`oai-ue.ue-edge.ue-edge` for the Terminal `ue-edge`.

The frames then travel UE -> gNB -> UPF -> app. With the `oai-cn/minimal` core, the UPF
source-NATs this traffic, so the app sees the UPF Pod as the client.

`actor_id` names the sender (a vehicle, a camera, a UE). Each actor and camera pair is a
separate feed. Older clients that send `truck_id` are accepted too.

## 5. Watch the result

The app's page lists every live feed with its annotated stream and the detected objects.

Open the **YOLO Edge** tab under Services in the MX-UI: the spec registers it.

| Endpoint | Returns |
|---|---|
| `POST /ingest/frame/{camera}` | Runs detection on a frame. Form fields: `frame` (JPEG), `actor_id`, `ts` (optional). |
| `GET /` | Page with every live feed. |
| `GET /actors` | Actors, cameras, frame counts and the latest detections. |
| `GET /stream/{actor}/{camera}.mjpg` | Live MJPEG stream of the annotated frames. |
| `GET /frame/{actor}/{camera}.jpg` | Latest frame, annotated unless `?annotated=0`. |
| `GET /detections/{actor}` | Latest detections per camera. |
| `GET /health` | Status, model and the inference device actually in use. |
| `GET /sample.jpg` | A test picture, to try the app without a camera. |

Feeds that send nothing for 60 seconds are hidden.

## Running on an NVIDIA GPU

`app-gpu.yaml` builds with CUDA PyTorch wheels and asks for one GPU and the NVIDIA runtime:

```bash
brc cdk app build -f app-gpu.yaml
brc cdk app push -f app-gpu.yaml
brc cdk app deploy -f app-gpu.yaml
```

- The cluster must expose GPUs as `nvidia.com/gpu` (NVIDIA GPU Operator or device plugin) and
  have a `nvidia` RuntimeClass. `brc cdk app deploy` checks both before deploying and lists
  the GPU nodes it found.
- The CUDA version in `TORCH_INDEX_URL` must not be newer than the node driver supports. The
  node label `nvidia.com/cuda.runtime-version.full` gives that limit.
- Without `runtime-class: nvidia` the Pod still starts, but PyTorch sees no GPU and the app
  runs on the CPU without an error. `GET /health` shows the device actually used.
- The image is much larger, about 7 GB.

## Running it as part of a Network

A detached app runs until you delete it. To create and remove the app together with a
Network, run it as an Element of that Network instead. The CDK builds the
CompositionModel from the same `app.yaml`:

```bash
brc cdk app model build      # print the model, without installing it
brc cdk app model install
```

```
WARN resources are ignored: the Element gets the model's defaults
WARN the HTTP probes run curl inside the container, so the image must ship curl
INFO CompositionModel installed in namespace trirematics. Reference it from a Network's edge section as model: yolo-edge/yolo-edge
```

Then add the app to the `edge` section of a Network and install the Network as usual:

```yaml
spec:
    edge:
        -   name: yolo
            stack: 5g-sa
            model: yolo-edge/yolo-edge
```

The Element is called `yolo-edge.yolo.<network>`. Follow it with `brc observe`, and get its
address with `brc extract port yolo-edge.yolo.<network> http`.

A managed Element runs the image's own `CMD`, and Athena schedules it: the spec's `command`,
`args`, `env`, `resources`, `node-selector` and `runtime-class` do not apply, and the CDK
warns about the ones you set. Running `brc cdk app model install` again after a new push
restarts the running Elements on the new image.

Remove the app from every Network first, then the model: `brc cdk app model delete`.

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
