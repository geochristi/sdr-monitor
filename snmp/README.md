# SNMP (PHY metrics)

This folder contains the SNMP integration that exposes GNU Radio PHY metrics via `snmpd` `pass_persist`.

## Files

- `snmp_extend.conf` - local `snmpd` config for testing
- `phy_snmp.py` - `pass_persist` handler (`get`, `getnext`, `set`)
- `oids.py` - OID constants used by the handler
- `mib/PHY-MIB.txt` - MIB definition

## Run SNMP Agent (test mode)

```bash
sudo snmpd -f -Lo -C -c ~/Desktop/SDR/snmp/snmp_extend.conf
```

## OID Map (enterprise: `.1.3.6.1.4.1.53864`)

- `phyNoise.0`    → `.1.3.6.1.4.1.53864.1.1.0` (read-write, integer scaled by 10)
- `phyBits.0`     → `.1.3.6.1.4.1.53864.1.2.0` (read-only)
- `phyErrors.0`   → `.1.3.6.1.4.1.53864.1.3.0` (read-only)
- `phyBER.0`      → `.1.3.6.1.4.1.53864.1.4.0` (read-only string)
- `phyResetBER.0` → `.1.3.6.1.4.1.53864.1.5.0` (read-write, write `1` to reset effective counters; read returns `0`)

## Test

Walk subtree:

```bash
snmpwalk -v2c -c public localhost .1.3.6.1.4.1.53864
```

Set noise:

```bash
snmpset -v2c -c private localhost .1.3.6.1.4.1.53864.1.1.0 i 5
```

Reset BER/counters baseline:

```bash
snmpset -v2c -c private localhost .1.3.6.1.4.1.53864.1.5.0 i 1
```

Read back reset OID:

```bash
snmpget -v2c -c public localhost .1.3.6.1.4.1.53864.1.5.0
```

## Behavior Notes

- `phyNoise.0` stores `value/10` to:
  - `/home/georgia/Desktop/SDR/control/phy_control.txt`
  - Example: `i 5` → `noise=0.5`
- Metrics are consumed from the ZMQ subscriber path used by `phy_snmp.py` (`transport/zmq_sub.py` + `phy_metrics`), not from `/tmp/phy_stats.txt`.
- `snmp_extend.conf` binds to `127.0.0.1` for local testing.
- `public` is read-only; `private` is required for `snmpset`.