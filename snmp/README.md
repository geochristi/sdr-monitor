# SNMP (PHY metrics)

This folder contains the SNMP integration used to expose PHY metrics
from the GNU Radio physical layer.

## Files

- `snmp_extend.conf` - local `snmpd` configuration used for testing.
- `phy_snmp.py` - `pass_persist` script used by SNMP for PHY metric get/getnext/set.

```bash
sudo snmpd -f -Lo -C -c ~/Desktop/SDR/snmp/snmp_extend.conf
```

## Test

From another terminal, query the custom PHY enterprise subtree:

```bash
snmpwalk -v2c -c public localhost .1.3.6.1.4.1.53864
```

Set PHY noise (read-write community):

```bash
snmpset -v2c -c private localhost .1.3.6.1.4.1.53864.1.1.0 i 5
```

Notes on set value:

- `OID_NOISE` is `.1.3.6.1.4.1.53864.1.1.0`.
- `phy_snmp.py` stores noise as `value / 10` in `control/phy_control.txt`.
- Example: setting `i 5` writes `noise=0.5`.

## Notes

- `snmp_extend.conf` binds SNMP to `127.0.0.1` only.
- Community `public` is read-only and restricted to localhost.
- Community `private` is read-write and needed for `snmpset`.
- PHY metrics are currently read from `/tmp/phy_stats.txt`.
- OIDs are under `.1.3.6.1.4.1.53864` via `pass_persist`.