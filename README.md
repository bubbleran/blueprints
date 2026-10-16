# BubbleRAN Telco Blueprints

This repository contains a collection of telco blueprints for deploying various 5G networks in [BubbleRAN](https://bubbleran.com/) platforms, and edge applications that run next to them.

## Repository Structure

The network blueprints are organized by vendor and hardware to make them easy to find and use:

```
apps/
├───carla/
└───yolo-edge/
network/
├───Amarisoft/
├───LITEON_AIO/
├───OAI/
│   ├───benetel/
│   ├───benetel-liteon/
│   ├───liteon/
│   ├───rf-sim/
│   ├───usrp/
│   └───zmq/
├───srsRAN/
├───Terminals/
└───utils/
```

-   `apps/`: Edge applications, each with its source, Dockerfile and the specs to build it into your cluster-local registry with the BubbleRAN CDK.
-   `network/`: The main directory containing all network blueprints.
-   `network/<VENDOR>/`: Contains blueprints for a specific vendor, such as Amarisoft, OAI, or srsRAN.
-   `network/OAI/<HARDWARE>/`: Contains blueprints for OpenAirInterface (OAI) tailored for specific hardware.
-   `network/Terminals/`: Terminal (UE) templates to add to a network that does not ship its own.
-   `utils/`: Contains utility scripts.

## How to Use

To deploy a network, use the `brc` command-line tool with the desired blueprint. For example, to deploy a basic Amarisoft network, you would run:

```bash
brc install network network/Amarisoft/01-amr-basic.yaml
```

Some blueprints also include their Terminal, and `brc install network` installs both. Their `readiness-check` makes the
Terminal ready only once every UE pings the UPF gateway of its slice from its own tunnel. Once it is ready, test the
connectivity of a UE with:

```bash
brc test rtt ue1 gateway -- -c 5
brc test throughput ue1 dl gateway -- --time 10
```

Here `ue1` is the name of the Terminal. For a Terminal that runs several UEs (`ue-count`), name the UE after the Terminal,
for example `brc test rtt ues ue3 gateway` for the third UE of the Terminal `ues` in
[OAI/rf-sim/07-5g-sa-rfsim-multi-ue.yaml](network/OAI/rf-sim/07-5g-sa-rfsim-multi-ue.yaml). Without it, the first UE is
tested. `kubectl get terminal ues -o yaml` lists every UE in `status.ues`.

For more detailed instructions and information on the available commands, please refer to the [official BubbleRAN documentation](https://bubbleran.com/docs).

To build and run an edge application, follow the README in its directory, for example [apps/yolo-edge](apps/yolo-edge/README.md).

## Available Blueprints

This repository includes blueprints for the following vendors and platforms:

-   **Amarisoft**
-   **LITEON AIO**
-   **OpenAirInterface (OAI)**
    -   Benetel
    -   Benetel-Liteon
    -   Liteon
    -   RF-Sim: monolithic gNB, CU-DU, multi-UE, two PDU sessions, NTN (GEO and LEO), O-RAN with FlexRIC and xApps
    -   USRP
    -   ZMQ: SISO and MIMO 2x2
-   **srsRAN**

## Available Edge Applications

-   **[YOLO edge app](apps/yolo-edge/README.md)**: object detection on camera frames sent by UEs over the 5G network, on CPU or NVIDIA GPU.
-   **[CARLA camera feed over 5G](apps/carla/README.md)**: the CARLA driving simulator as the camera of a soft UE, streaming over 5G to the YOLO edge app.
