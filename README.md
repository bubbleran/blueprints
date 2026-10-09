# BubbleRAN Telco Blueprints

This repository contains a collection of telco blueprints for deploying various 5G networks in [BubbleRAN](https://bubbleran.com/) platforms, and edge applications that run next to them.

## Repository Structure

The network blueprints are organized by vendor and hardware to make them easy to find and use:

```
apps/
└───yolo-edge/
network/
├───Amarisoft/
├───LITEON_AIO/
├───OAI/
│   ├───benetel/
│   ├───benetel-liteon/
│   ├───liteon/
│   ├───rf-sim/
│   └───usrp/
├───srsRAN/
└───utils/
```

-   `apps/`: Edge applications, each with its source, Dockerfile and the specs to build it into your cluster-local registry with the BubbleRAN CDK.
-   `network/`: The main directory containing all network blueprints.
-   `network/<VENDOR>/`: Contains blueprints for a specific vendor, such as Amarisoft, OAI, or srsRAN.
-   `network/OAI/<HARDWARE>/`: Contains blueprints for OpenAirInterface (OAI) tailored for specific hardware.
-   `utils/`: Contains utility scripts.

## How to Use

To deploy a network, use the `brc` command-line tool with the desired blueprint. For example, to deploy a basic Amarisoft network, you would run:

```bash
brc install network network/Amarisoft/01-amr-basic.yaml
```

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
    -   RF-Sim
    -   USRP
-   **srsRAN**

## Available Edge Applications

-   **[YOLO edge app](apps/yolo-edge/README.md)**: object detection on camera frames sent by UEs over the 5G network, on CPU or NVIDIA GPU.
