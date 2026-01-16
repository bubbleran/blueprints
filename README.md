# BubbleRAN Network Blueprints

This repository contains a collection of network blueprints for deploying various 5G networks in [BubbleRAN](https://bubbleran.com/) platforms.

## Repository Structure

The blueprints are organized by vendor and hardware to make them easy to find and use:

```
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