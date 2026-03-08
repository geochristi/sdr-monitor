# SDR Monitor

SDR Monitor is a Python-based software-defined radio monitoring and control project.
It combines a GNU Radio PHY simulation with a small management plane so you can:

- publish PHY telemetry (SNR, BER, RSSI, etc.),
- process and alarm on metrics in Python,
- expose selected PHY values through SNMP,
- change PHY noise through `snmpset` for closed-loop experiments.

## What This Project Is

This repository is an end-to-end lab environment for experimenting with SDR observability and control.
The current working path is:

1. GNU Radio PHY produces runtime statistics.
2. Telemetry is published over ZeroMQ (`tcp://127.0.0.1:5556`).
3. A Python control loop consumes telemetry and computes alarms.
4. SNMP `pass_persist` exposes PHY OIDs for GET/GETNEXT and allows SET on noise.

## Repository Layout

- `phy/`: GNU Radio flowgraph and PHY-side scripts.
- `control/`: main loop that subscribes to telemetry and runs metrics/alarm logic.
- `phy_metrics/`: metric model, filters, and alarm detector.
- `transport/`: ZeroMQ subscriber/publisher transport helpers.
- `snmp/`: SNMP configuration, OID mapping, and `phy_snmp.py` `pass_persist` handler.
- `management/`: management-plane stubs (NETCONF/SNMP agent placeholders).
- `presentations/`: architecture and presentation notes.

## Current Status

- Working now:
	- PHY flowgraph execution (`phy/phy_flowgraph.grc`, `phy/phy_flowgraph.py`)
	- Metric subscription and processing (`python -m control.main`)
	- SNMP walk/getnext/get and SNMP set for noise via enterprise OID tree `.1.3.6.1.4.1.53864`
- In progress/placeholders:
	- `management/netconf_server.py`
	- `management/snmp_agent.py`
	- parts of adaptive/scheduler modules

## Prerequisites

- Linux environment
- Python 3.10+
- GNU Radio 3.10+ (`gnuradio-companion`, GNU Radio Python modules)
- Net-SNMP tools (`snmpd`, `snmpwalk`, `snmpset`)
- Python packages:
	- `pyzmq`
	- `numpy`

## Quick Start

### 1) Start SNMP daemon first

In one terminal:

```bash
sudo snmpd -f -Lo -C -c ~/Desktop/SDR/snmp/snmp_extend.conf
```

### 2) Run the telemetry/control loop

In another terminal:

```bash
cd ~/Desktop/SDR
python3 -m control.main
```

This subscribes to ZMQ telemetry (`tcp://127.0.0.1:5556`), updates filtered metrics, and prints alarms (for example low SNR or high BER).

Telemetry fields currently consumed include `ber`, `bits`, and `errors` (plus optional PHY fields such as `snr` and `rssi`).

### 3) Run the PHY flowgraph

In another terminal:

```bash
cd ~/Desktop/SDR/phy
gnuradio-companion phy_flowgraph.grc
```

From GRC, generate and run the flowgraph. Or run generated Python directly:

```bash
cd ~/Desktop/SDR/phy
python3 phy_flowgraph.py
```

### 4) Query via SNMP (`snmpget`/`snmpwalk`)

From another terminal, once all services above are running:

Read a single OID (`snmpget`):

```bash
snmpget -v2c -c public localhost .1.3.6.1.4.1.53864.1.4.0
```

Read PHY subtree:

```bash
snmpwalk -v2c -c public localhost .1.3.6.1.4.1.53864
```

Set PHY noise (integer scaled by 10):

```bash
snmpset -v2c -c private localhost .1.3.6.1.4.1.53864.1.1.0 i 5
```

This writes `noise=0.5` to `control/phy_control.txt`.

## Key Files

- `snmp/oids.py`: defines SNMP OIDs:
	- `.1.3.6.1.4.1.53864.1.1.0` (`noise`, read/write)
	- `.1.3.6.1.4.1.53864.1.2.0` (`bits`)
	- `.1.3.6.1.4.1.53864.1.3.0` (`errors`)
	- `.1.3.6.1.4.1.53864.1.4.0` (`ber`)
- `snmp/phy_snmp.py`: SNMP `pass_persist` handler for get/getnext/set.
- `control/main.py`: runtime control/monitoring loop.
- `phy_metrics/metrics_engine.py`: filters metrics and runs alarm checks.

## Notes

- SNMP config binds to localhost for local testing.
- SNMP values are sourced from live ZMQ telemetry through `transport/zmq_sub.py`.
- In the default BER block, `ber`/`bits`/`errors` are published when the BER window threshold is reached (`WINDOW_SIZE` in `phy/phy_flowgraph_epy_block_1.py`).
- Noise control state is stored in `control/phy_control.txt`.
