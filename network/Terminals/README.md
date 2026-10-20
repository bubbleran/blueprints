# Terminals

Blueprints whose UE is software (RF simulator, ZMQ, NTN, OAI UE on a USRP) include their Terminal and install
it with the Network. Blueprints that run over the air with a real device (USRP, Benetel, Liteon, LiteON AIO,
Amarisoft) contain only the Network: add a UE with [terminal_quectel.yaml](terminal_quectel.yaml).

Every blueprint uses the same section names, so a Terminal only needs the network name:

| Section | Name |
|---|---|
| Access, monolithic gNB | `gnb` (`gnb-1`, `gnb-2` when there are several) |
| Access, CU/DU split | `cu-du` (and `du` for an extra DU) |
| Core | `core` |
| Network | `<ran>-<radio>`, for example `oai-usrp`, `ocudu-benetel`, `srsran-usrp` |

The Terminal points to them with `preferred-access: <access>.<network>` and `target-cores: [core.<network>]`.

The Terminal model depends on the UE and on the RAN it attaches to:

| UE | RAN and radio | `model` | `vendor` | Example |
|---|---|---|---|---|
| Quectel modem (COTS) | any, over the air | `terminal/quectel` | `oai` (`amr` for Amarisoft) | [terminal_quectel.yaml](terminal_quectel.yaml) |
| OAI soft UE | OAI, RF simulator | `terminal/oai-ue` | `oai` | [OAI/rf-sim/01-5g-sa-rfsim.yaml](../OAI/rf-sim/01-5g-sa-rfsim.yaml) |
| OAI soft UE | OAI, ZMQ | `terminal/oai-ue` | `oai` | [OAI/zmq/01-5g-sa-zmq.yaml](../OAI/zmq/01-5g-sa-zmq.yaml) |
| OAI soft UE | OAI, USRP | `terminal/oai-ue` | `oai` | [OAI/usrp/05-5g-sa-usrp-oai-ue.yaml](../OAI/usrp/05-5g-sa-usrp-oai-ue.yaml) |
| OAI NTN soft UE | OAI, RF simulator, NTN | `terminal/oai-ue-ntn` | `oai` | [OAI/rf-sim/09-5g-sa-rfsim-ntn-geo.yaml](../OAI/rf-sim/09-5g-sa-rfsim-ntn-geo.yaml) |
| OAI soft UE | OCUDU, ZMQ | `terminal/oai-ue-ocudu` | `oai` | [OCUDU/zmq/01-ocudu-zmq.yaml](../OCUDU/zmq/01-ocudu-zmq.yaml) |
| OAI NTN soft UE | OCUDU, ZMQ, NTN | `terminal/oai-ue-ntn` | `oai` | [OCUDU/zmq/04-ocudu-zmq-ntn-geo.yaml](../OCUDU/zmq/04-ocudu-zmq-ntn-geo.yaml) |

With ZMQ, the gNB or DU connects to the UE by the DNS name of its Element. The access section carries
`terminals.roles.athena.t9s.io/oai-ue: "<model>.<terminal>.<terminal>.t9s.local"`, so renaming the Terminal
means updating that annotation too.
