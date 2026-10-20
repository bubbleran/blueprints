# Terminals

Blueprints whose UE is software (RF simulator, ZMQ, NTN, OAI UE on a USRP) include their Terminal and install
it with the Network. Blueprints that run over the air with a real device (USRP, Benetel, Liteon, LiteON AIO,
Amarisoft) contain only the Network: add a UE with [quectel.yaml](quectel.yaml) for a Quectel modem
connected to a cluster node, or [external.yaml](external.yaml) for any UE the cluster does not run (phone,
modem on another host), which only registers its SIM in the core.

Every blueprint uses the same section names, so a Terminal only needs the network name:

| Section | Name |
|---|---|
| Access, monolithic gNB | `gnb` (`gnb-1`, `gnb-2` when there are several) |
| Access, CU/DU split | `cu-du` (and `du` for an extra DU) |
| Core | `core` |
| Network | `<ran>-<radio>`, for example `oai-usrp`, `ocudu-benetel`, `ocudu-zmq`; `amarisoft` and `liteon-aio` for the blueprints with their own radio |

The Terminal points to them with `preferred-access: <access>.<network>` and `target-cores: [core.<network>]`.

The Terminal model depends on the UE and on the RAN it attaches to:

| UE | RAN and radio | `model` | `vendor` | Example |
|---|---|---|---|---|
| Quectel modem on a cluster node | any, over the air | `terminal/quectel` | `oai` (`amr` for Amarisoft) | [quectel.yaml](quectel.yaml) |
| Phone or modem outside the cluster | any, over the air | `terminal/external` | `oai` (`amr` for Amarisoft) | [external.yaml](external.yaml) |
| OAI soft UE | OAI, RF simulator | `terminal/oai-ue` | `oai` | [networks/oai/rfsim/01-monolithic.yaml](../networks/oai/rfsim/01-monolithic.yaml) |
| OAI soft UE | OAI, ZMQ | `terminal/oai-ue` | `oai` | [networks/oai/zmq/01-monolithic.yaml](../networks/oai/zmq/01-monolithic.yaml) |
| OAI soft UE | OAI, USRP | `terminal/oai-ue` | `oai` | [networks/oai/usrp/05-b200-oai-ue.yaml](../networks/oai/usrp/05-b200-oai-ue.yaml) |
| OAI NTN soft UE | OAI, RF simulator, NTN | `terminal/oai-ue-ntn` | `oai` | [networks/oai/rfsim/09-ntn-geo.yaml](../networks/oai/rfsim/09-ntn-geo.yaml) |
| OAI soft UE | OCUDU, ZMQ | `terminal/oai-ue-ocudu` | `oai` | [networks/ocudu/zmq/01-monolithic.yaml](../networks/ocudu/zmq/01-monolithic.yaml) |
| OAI NTN soft UE | OCUDU, ZMQ, NTN | `terminal/oai-ue-ntn` | `oai` | [networks/ocudu/zmq/04-ntn-geo.yaml](../networks/ocudu/zmq/04-ntn-geo.yaml) |

With ZMQ, the gNB or DU connects to the UE by the DNS name of its Element. The access section carries
`terminals.roles.athena.t9s.io/oai-ue: "<model>.<terminal>.<terminal>.t9s.local"`, so renaming the Terminal
means updating that annotation too.
