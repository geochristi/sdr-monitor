# PHY GNU Radio Quick Start

This folder contains the GNU Radio PHY flowgraph and Python examples.

## Prerequisites

- GNU Radio 3.10+ installed (`gnuradio-companion`, `python3`, and GNU Radio Python modules)
- Python packages used by blocks/scripts:
	- `numpy`
	- `pyzmq`

## Open in GNU Radio Companion (GRC)

From this folder:

```bash
cd ~/Desktop/SDR/phy
gnuradio-companion phy_flowgraph.grc
```

In GRC:

1. Open `phy_flowgraph.grc`.
2. Click **Generate** to regenerate Python if needed.
3. Click **Run** to execute the flowgraph from GRC.

## Run the generated flowgraph from terminal

```bash
cd ~/Desktop/SDR/phy
python3 run_phy.py
```

Notes:

- The script runs until closed with Ctrl+C.
- ZMQ publishers in the flowgraph publish on:
	- `tcp://127.0.0.1:5555`
	- `tcp://127.0.0.1:5556`

## Run the example script

`example_flowgraph.py` starts the same flowgraph and changes noise voltage over time.

```bash
cd ~/Desktop/SDR/phy
grcc phy_flowgraph.grc
python3 example_flowgraph.py
```

What it does:

- Starts `phy_flowgraph`
- Sets noise to `0.0`, then `2.0`, then back to `0.0`
- Stops and waits for clean shutdown

## Optional: Run mock metrics publisher

If you want sample telemetry without the flowgraph:

```bash
cd ~/Desktop/SDR/phy
python3 mock_publisher.py
```

This publishes random JSON metrics once per second on `tcp://127.0.0.1:5556`.

## Ports and Integration (Important)

The flowgraph uses two ZMQ PUB endpoints:

- `tcp://127.0.0.1:5555`
- `tcp://127.0.0.1:5556`

For this project, the SNMP/monitor subscriber is expected to read telemetry from:

- `tcp://127.0.0.1:5556`

If you change the endpoint in GNU Radio, update the subscriber config too, otherwise metrics and BER/reset behavior in SNMP will appear broken.

## Control file used by PHY blocks

The Embedded Python blocks read:

- `/home/georgia/Desktop/SDR/control/phy_control.txt`

Format:

```txt
noise=0.0
snr=30.0
ber_inject=0.0
rate=50
freq_offset=0
mod_scheme=3
```

Runtime meaning:

- `noise`: explicit additive noise voltage.
- `snr`: target SNR-based AWGN level (dB).
- `ber_inject`: probability of injected symbol mismatch in BER comparator.

SNMP `set` updates this file and the flowgraph applies changes during runtime.