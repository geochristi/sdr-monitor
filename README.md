# SDR Monitor

SDR Monitor is a Python-based software-defined radio monitoring and control project.
It combines a GNU Radio PHY simulation with a small management plane so you can:

- publish PHY telemetry (SNR, BER, RSSI, etc.),
- process and alarm on metrics in Python,
- expose selected PHY values through SNMP,
- change PHY noise through `snmpset` for closed-loop experiments,
- reset effective BER counters via SNMP.

## What This Project Is

This repository is an end-to-end lab environment for experimenting with SDR observability and control.
The current working path is:

1. GNU Radio PHY produces runtime statistics.
2. Telemetry is published over ZeroMQ (`tcp://127.0.0.1:5556`).
3. A Python control loop consumes telemetry and computes alarms.
4. SNMP `pass_persist` exposes PHY OIDs for GET/GETNEXT and allows SET on noise and BER reset.

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
  - SNMP walk/getnext/get
  - SNMP set for:
    - noise (`phyNoise.0`)
    - effective BER baseline reset (`phyResetBER.0`, write `1`)
- In progress/placeholders:
  - `management/netconf_server.py`
  - `management/snmp_agent.py`
  - parts of adaptive/scheduler modules

## Prerequisites

- Linux environment
- Python 3.10+
- GNU Radio 3.10+ (`gnuradio-companion`, GNU Radio Python modules)
- Net-SNMP tools (`snmpd`, `snmpwalk`, `snmpset`, `snmpget`)
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

This subscribes to ZMQ telemetry (`tcp://127.0.0.1:5556`), updates filtered metrics, and prints alarms.

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

### 4) Query and control via SNMP

Read BER:

```bash
snmpget -v2c -c public localhost .1.3.6.1.4.1.53864.1.4.0
```

Walk PHY subtree:

```bash
snmpwalk -v2c -c public localhost .1.3.6.1.4.1.53864
```

Set PHY noise (integer scaled by 10):

```bash
snmpset -v2c -c private localhost .1.3.6.1.4.1.53864.1.1.0 i 5
```

Reset effective BER counters baseline:

```bash
snmpset -v2c -c private localhost .1.3.6.1.4.1.53864.1.5.0 i 1
```

Read reset OID (always returns `0`):

```bash
snmpget -v2c -c public localhost .1.3.6.1.4.1.53864.1.5.0
```

## OID Map

- `.1.3.6.1.4.1.53864.1.1.0` → `phyNoise.0` (read/write, scaled integer)
- `.1.3.6.1.4.1.53864.1.2.0` → `phyBits.0` (read-only, effective bits)
- `.1.3.6.1.4.1.53864.1.3.0` → `phyErrors.0` (read-only, effective errors)
- `.1.3.6.1.4.1.53864.1.4.0` → `phyBER.0` (read-only string)
- `.1.3.6.1.4.1.53864.1.5.0` → `phyResetBER.0` (read/write; write `1` resets baseline, read returns `0`)

## Key Files

- `snmp/oids.py`: SNMP OID constants.
- `snmp/phy_snmp.py`: SNMP `pass_persist` handler (`get`, `getnext`, `set`).
- `snmp/mib/PHY-MIB.txt`: MIB definition.
- `control/main.py`: runtime control/monitoring loop.
- `phy_metrics/metrics_engine.py`: filters metrics and runs alarm checks.

## Notes

- SNMP config binds to localhost for local testing.
- SNMP values are sourced from live ZMQ telemetry through `transport/zmq_sub.py`.
- BER reset is baseline-based in SNMP view (effective counters), because upstream telemetry counters are cumulative.
- Noise control state is stored in:
  - `/home/georgia/Desktop/SDR/control/phy_control.txt`
