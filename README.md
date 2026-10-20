# BubbleRAN Telco Blueprints

This repository contains a collection of telco blueprints for deploying various 5G networks in [BubbleRAN](https://bubbleran.com/) platforms, and edge applications that run next to them.

## Repository Structure

Network blueprints are organized as `networks/<ran>/<radio>/NN-<topology>[-<feature>].yaml`. srsRAN is deprecated and no longer included.

```
apps/                   edge applications
├── carla/
└── yolo-edge/
networks/
├── amarisoft/
├── liteon-aio/
├── oai/
│   ├── benetel/
│   ├── benetel-liteon/
│   ├── liteon/
│   ├── rfsim/
│   ├── usrp/           B200/B210 and N300
│   └── zmq/
└── ocudu/
    ├── benetel/
    ├── liteon/
    ├── usrp/           B200/B210 and N300
    └── zmq/
terminals/              Quectel and external Terminals, and the Terminal model table
utils/                  helper scripts
```

-   `apps/`: Edge applications, each with its source, Dockerfile and the specs to build it into your cluster-local registry with the BubbleRAN CDK.
-   `networks/<ran>/<radio>/`: Network blueprints for a RAN (`oai`, `ocudu`) on a radio (`rfsim`, `zmq`, `usrp`, or the O-RAN 7.2 RU vendor `benetel`, `liteon`). Amarisoft and the LiteON AIO bring their own radio, so their blueprints sit directly in `networks/amarisoft/` and `networks/liteon-aio/`. The topology words are fixed: `monolithic`, `cu-du`, `-oran` (FlexRIC), `-xapp` (FlexRIC and the monitoring xApp), `-ntn-geo`/`-ntn-leo`, `-2x2`.
-   `terminals/`: Blueprints with a soft UE (RF simulator, ZMQ, NTN, OAI UE on a USRP) include their Terminal. The over-the-air blueprints end with the `preferred-access` and `target-cores` to set in [terminals/quectel.yaml](terminals/quectel.yaml) (Quectel modem on a cluster node) or [terminals/external.yaml](terminals/external.yaml) (any other UE, only registers its SIM). See [terminals/README.md](terminals/README.md) for the naming rule and the Terminal model of each RAN and radio.
-   `utils/`: Helper scripts.

## How to Use

To deploy a network, use the `brc` command-line tool with the desired blueprint. For example, to deploy an OAI gNB and UE on the RF simulator, you would run:

```bash
brc install network networks/oai/rfsim/01-monolithic.yaml
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
[networks/oai/rfsim/07-multi-ue.yaml](networks/oai/rfsim/07-multi-ue.yaml). Without it, the first UE is
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
    -   USRP: B200/B210 and N300
    -   ZMQ: SISO and MIMO 2x2
-   **OCUDU**
    -   Benetel and Liteon (O-RAN 7.2): monolithic gNB, CU-DU, O-RAN with FlexRIC and xApps
    -   USRP: B200/B210 (monolithic gNB and CU-DU) and N300
    -   ZMQ with the OAI soft UE: SISO, MIMO 2x2, CU-DU and NTN (GEO)

## Available Edge Applications

-   **[YOLO edge app](apps/yolo-edge/README.md)**: object detection on camera frames sent by UEs over the 5G network, on CPU or NVIDIA GPU.
-   **[CARLA camera feed over 5G](apps/carla/README.md)**: the CARLA driving simulator as the camera of a soft UE, streaming over 5G to the YOLO edge app.

## Moved files

The blueprints moved to the lowercase layout above in October 2026. Their content did not change, apart from
the section names described in [terminals/README.md](terminals/README.md). Old paths map as follows.

| Old path | New path |
|---|---|
| `network/Amarisoft/01-amr-basic.yaml` | `networks/amarisoft/01-monolithic.yaml` |
| `network/Amarisoft/02-amr-ho-intra.yaml` | `networks/amarisoft/02-handover-intra.yaml` |
| `network/Amarisoft/03-amr-ho-inter.yaml` | `networks/amarisoft/03-handover-inter.yaml` |
| `network/LITEON_AIO/01-liteon-aio.yaml` | `networks/liteon-aio/01-aio.yaml` |
| `network/OAI/benetel-liteon/01-liteon-benetel-cu-du-oran.yaml` | `networks/oai/benetel-liteon/01-cu-du-oran-handover.yaml` |
| `network/OAI/benetel/01-benetel-monolithic.yaml` | `networks/oai/benetel/01-monolithic.yaml` |
| `network/OAI/benetel/02-benetel-cu-du.yaml` | `networks/oai/benetel/02-cu-du.yaml` |
| `network/OAI/benetel/03-benetel-cu-du-oran.yaml` | `networks/oai/benetel/03-cu-du-oran.yaml` |
| `network/OAI/benetel/04-benetel-monolithic-oran-xapp.yaml` | `networks/oai/benetel/04-monolithic-oran-xapp.yaml` |
| `network/OAI/liteon/01-liteon-monolithic.yaml` | `networks/oai/liteon/01-monolithic.yaml` |
| `network/OAI/liteon/02-liteon-cu-du.yaml` | `networks/oai/liteon/02-cu-du.yaml` |
| `network/OAI/liteon/03-liteon-cu-du-oran.yaml` | `networks/oai/liteon/03-cu-du-oran.yaml` |
| `network/OAI/liteon/04-liteon-cu-du-oran-xapp.yaml` | `networks/oai/liteon/04-cu-du-oran-xapp.yaml` |
| `network/OAI/liteon/05-two_liteon.yaml` | `networks/oai/liteon/05-two-ru.yaml` |
| `network/OAI/rf-sim/01-5g-sa-rfsim.yaml` | `networks/oai/rfsim/01-monolithic.yaml` |
| `network/OAI/rf-sim/02-5g-sa-rfsim-oran.yaml` | `networks/oai/rfsim/02-monolithic-oran.yaml` |
| `network/OAI/rf-sim/03-5g-sa-rfsim-oran-xapp.yaml` | `networks/oai/rfsim/03-monolithic-oran-xapp.yaml` |
| `network/OAI/rf-sim/04-5g-sa-rfsim-oran-xapp-mysql.yaml` | `networks/oai/rfsim/04-monolithic-oran-xapp-mysql.yaml` |
| `network/OAI/rf-sim/05-5g-sa-rfsim-open5gs.yaml` | `networks/oai/rfsim/05-monolithic-open5gs.yaml` |
| `network/OAI/rf-sim/06-5g-sa-rfsim-cu-du.yaml` | `networks/oai/rfsim/06-cu-du.yaml` |
| `network/OAI/rf-sim/07-5g-sa-rfsim-multi-ue.yaml` | `networks/oai/rfsim/07-multi-ue.yaml` |
| `network/OAI/rf-sim/08-5g-sa-rfsim-2-pdu.yaml` | `networks/oai/rfsim/08-two-pdu.yaml` |
| `network/OAI/rf-sim/09-5g-sa-rfsim-ntn-geo.yaml` | `networks/oai/rfsim/09-ntn-geo.yaml` |
| `network/OAI/rf-sim/10-5g-sa-rfsim-ntn-leo.yaml` | `networks/oai/rfsim/10-ntn-leo.yaml` |
| `network/OAI/rf-sim/11-5g-sa-rfsim-ntn-geo-n256.yaml` | `networks/oai/rfsim/11-ntn-geo-n256.yaml` |
| `network/OAI/usrp/01-5g-sa-usrp.yaml` | `networks/oai/usrp/01-b200.yaml` |
| `network/OAI/usrp/02-5g-sa-usrp-oran.yaml` | `networks/oai/usrp/02-b200-oran.yaml` |
| `network/OAI/usrp/03-5g-sa-usrp-ogs.yaml` | `networks/oai/usrp/03-b200-open5gs.yaml` |
| `network/OAI/usrp/04-5g-sa-usrp-oran-xapp.yaml` | `networks/oai/usrp/04-b200-oran-xapp.yaml` |
| `network/OAI/usrp/05-5g-sa-usrp-oai-ue.yaml` | `networks/oai/usrp/05-b200-oai-ue.yaml` |
| `network/OAI/usrp/06-5g-sa-n300.yaml` | `networks/oai/usrp/06-n300.yaml` |
| `network/OAI/usrp/07-5g-sa-n300-oran.yaml` | `networks/oai/usrp/07-n300-oran.yaml` |
| `network/OAI/zmq/01-5g-sa-zmq.yaml` | `networks/oai/zmq/01-monolithic.yaml` |
| `network/OAI/zmq/02-5g-sa-zmq-2x2.yaml` | `networks/oai/zmq/02-monolithic-2x2.yaml` |
| `network/OCUDU/benetel/01-benetel-monolithic.yaml` | `networks/ocudu/benetel/01-monolithic.yaml` |
| `network/OCUDU/benetel/02-benetel-cu-du.yaml` | `networks/ocudu/benetel/02-cu-du.yaml` |
| `network/OCUDU/benetel/03-benetel-cu-du-oran.yaml` | `networks/ocudu/benetel/03-cu-du-oran.yaml` |
| `network/OCUDU/benetel/04-benetel-monolithic-oran-xapp.yaml` | `networks/ocudu/benetel/04-monolithic-oran-xapp.yaml` |
| `network/OCUDU/liteon/01-liteon-monolithic.yaml` | `networks/ocudu/liteon/01-monolithic.yaml` |
| `network/OCUDU/liteon/02-liteon-cu-du.yaml` | `networks/ocudu/liteon/02-cu-du.yaml` |
| `network/OCUDU/liteon/03-liteon-cu-du-oran.yaml` | `networks/ocudu/liteon/03-cu-du-oran.yaml` |
| `network/OCUDU/liteon/04-liteon-cu-du-oran-xapp.yaml` | `networks/ocudu/liteon/04-cu-du-oran-xapp.yaml` |
| `network/OCUDU/liteon/05-two_liteon.yaml` | `networks/ocudu/liteon/05-two-ru.yaml` |
| `network/OCUDU/usrp/01-ocudu-b200.yaml` | `networks/ocudu/usrp/01-b200.yaml` |
| `network/OCUDU/usrp/02-ocudu-b200-cu-du.yaml` | `networks/ocudu/usrp/02-b200-cu-du.yaml` |
| `network/OCUDU/usrp/03-ocudu-n300.yaml` | `networks/ocudu/usrp/03-n300.yaml` |
| `network/OCUDU/zmq/01-ocudu-zmq.yaml` | `networks/ocudu/zmq/01-monolithic.yaml` |
| `network/OCUDU/zmq/02-ocudu-zmq-2x2.yaml` | `networks/ocudu/zmq/02-monolithic-2x2.yaml` |
| `network/OCUDU/zmq/03-ocudu-zmq-cu-du.yaml` | `networks/ocudu/zmq/03-cu-du.yaml` |
| `network/OCUDU/zmq/04-ocudu-zmq-ntn-geo.yaml` | `networks/ocudu/zmq/04-ntn-geo.yaml` |
| `network/Terminals/README.md` | `terminals/README.md` |
| `network/Terminals/terminal_quectel.yaml` | `terminals/quectel.yaml` |
| `network/srsRAN/01-5g-sa-srs-usrp.yaml` | removed, srsRAN is deprecated |
| `network/srsRAN/02-5g-sa-srs-usrp-oran.yaml` | removed, srsRAN is deprecated |
| `network/srsRAN/03-5g-sa-srs-usrp-oran-xapp.yaml` | removed, srsRAN is deprecated |
| `network/utils/get_arfcn.py` | `utils/get_arfcn.py` |
