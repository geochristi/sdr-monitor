# netconf

NETCONF/sysrepo integration for the SDR PHY layer. Allows remote configuration of PHY parameters via the `sdr-phy` YANG model.

## Files

| File | Description |
|---|---|
| `sdr-phy.yang` | YANG data model defining the configurable PHY parameters |
| `sysrepo_sdr_controller.c` | Sysrepo subscriber — listens for config changes and writes them to the PHY control file |
| `sdr_controller` | Compiled binary of `sysrepo_sdr_controller.c` |

## YANG model (`sdr-phy`)

Namespace: `urn:sdr:phy`  
Container: `phy`

| Leaf | Type | Default | Description |
|---|---|---|---|
| `frequency` | decimal64 | 2400000000 | Carrier frequency in Hz → converted to `freq_offset` in Hz relative to 2.4 GHz |
| `modulation` | string | BPSK | Modulation scheme string → mapped to `mod_scheme` (0–4) |
| `packet_rate` | uint32 | 100 | Packet rate in pps → written as `rate` |
| `noise_level` | decimal64 | 0 | Noise amplitude → written as `noise` |
| `tx_gain` | decimal64 | 10 | TX gain (logged, not forwarded to control file) |
| `rx_gain` | decimal64 | 10 | RX gain (logged, not forwarded to control file) |

Modulation string mapping:

| YANG value | `mod_scheme` |
|---|---|
| BPSK / 2PSK | 0 |
| QPSK / 4PSK | 1 |
| 8PSK | 2 |
| 16QAM / QAM16 | 3 |
| 64QAM / QAM64 | 4 |

## Controller (`sysrepo_sdr_controller.c`)

Subscribes to the `sdr-phy` module in the sysrepo running datastore. On every `SR_EV_CHANGE` and `SR_EV_DONE` event, it iterates changed leaves and writes mapped values atomically to the PHY control file.

Write path:
1. Primary: `/home/georgia/Desktop/SDR/control/phy_control.txt`
2. Fallback: `/home/georgia/Desktop/SDR/phy_cotrol.txt` (used if primary directory is not writable)

Writes are atomic — values are written to a temp file in the same directory, fsynced, then renamed into place. A `.lock` file is used with `flock` to serialize concurrent writers.

### Build

```bash
cd netconf
gcc -o sdr_controller sysrepo_sdr_controller.c $(pkg-config --cflags --libs sysrepo)
```

### Install YANG model

```bash
sysrepoctl --install sdr-phy.yang
```

### Run

```bash
./sdr_controller
```

The process must be running before issuing any `sysrepocfg` commands.

### Apply configuration

```bash
sysrepocfg --import=config.json -d running -m sdr-phy -f json
```

Example `config.json`:

```json
{
  "sdr-phy:phy": {
    "frequency": 2450000000,
    "modulation": "16QAM",
    "packet_rate": 200,
    "noise_level": 0.1
  }
}
```

After a successful import the controller prints:

```
WROTE freq_offset=1000000 to control file
WROTE mod_scheme=3 to control file
WROTE rate=200 to control file
WROTE noise=0.100000 to control file
```

`frequency` mapping details:

- `freq_offset = round(frequency_hz - 2400000000)`
- clamped to `[-1000000, 1000000]` to match controller bounds
