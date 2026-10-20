# Terminals

Blueprints whose UE is software (RF simulator, ZMQ, NTN, OAI UE on a USRP) include their Terminal and install
it with the Network. Blueprints that run over the air with a real device (USRP, Benetel, Liteon, LiteON AIO,
Amarisoft) contain only the Network: add a UE with [quectel.yaml](quectel.yaml).

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
| Quectel modem (COTS) | any, over the air | `terminal/quectel` | `oai` (`amr` for Amarisoft) | [quectel.yaml](quectel.yaml) |
| OAI soft UE | OAI, RF simulator | `terminal/oai-ue` | `oai` | [network/oai/rfsim/01-monolithic.yaml](../network/oai/rfsim/01-monolithic.yaml) |
| OAI soft UE | OAI, ZMQ | `terminal/oai-ue` | `oai` | [network/oai/zmq/01-monolithic.yaml](../network/oai/zmq/01-monolithic.yaml) |
| OAI soft UE | OAI, USRP | `terminal/oai-ue` | `oai` | [network/oai/usrp/05-b200-oai-ue.yaml](../network/oai/usrp/05-b200-oai-ue.yaml) |
| OAI NTN soft UE | OAI, RF simulator, NTN | `terminal/oai-ue-ntn` | `oai` | [network/oai/rfsim/09-ntn-geo.yaml](../network/oai/rfsim/09-ntn-geo.yaml) |
| OAI soft UE | OCUDU, ZMQ | `terminal/oai-ue-ocudu` | `oai` | [network/ocudu/zmq/01-monolithic.yaml](../network/ocudu/zmq/01-monolithic.yaml) |
| OAI NTN soft UE | OCUDU, ZMQ, NTN | `terminal/oai-ue-ntn` | `oai` | [network/ocudu/zmq/04-ntn-geo.yaml](../network/ocudu/zmq/04-ntn-geo.yaml) |

With ZMQ, the gNB or DU connects to the UE by the DNS name of its Element. The access section carries
`terminals.roles.athena.t9s.io/oai-ue: "<model>.<terminal>.<terminal>.t9s.local"`, so renaming the Terminal
means updating that annotation too.
