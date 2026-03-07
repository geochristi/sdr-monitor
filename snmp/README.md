# SNMP (PHY metrics)

This folder contains SNMP integration files for exposing PHY stats.

## Files

- `snmp_extend.conf` : local `snmpd` config used for testing.
- `phy_snmp.py` : script used by the SNMP setup.

## Start SNMP agent

Run `snmpd` in foreground with logs to stdout:

```bash
sudo snmpd -f -Lo -C -c ~/Desktop/SDR/snmp/snmp_extend.conf
```

## Test

From another terminal, query the extend subtree:

```bash
snmpwalk -v2c -c public localhost .1.3.6.1.4.1.8072.1.3
```

## Notes

- `snmp_extend.conf` binds SNMP to `127.0.0.1` only.
- Community is `public` and read-only for localhost.