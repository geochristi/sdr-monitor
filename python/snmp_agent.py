from pysnmp.entity import engine, config
from pysnmp.carrier.asyncore.dgram import udp
from pysnmp.entity.rfc3413 import context, cmdrsp
from pysnmp.smi import builder
from pysnmp.proto.rfc1902 import OctetString

import shared_state
import socket
import threading


snmpEngine = engine.SnmpEngine()

config.addV1System(snmpEngine, 'public', 'public')

config.addVacmUser(
    snmpEngine,
    2,
    'public',
    'noAuthNoPriv',
    (1,3,6),
    (1,3,6),
    (1,3,6)
)

config.addSocketTransport(
    snmpEngine,
    udp.domainName,
    udp.UdpTransport().openServerMode(('127.0.0.1', 2001))
)

snmpContext = context.SnmpContext(snmpEngine)

# ---- Custom OID ----
mibBuilder = snmpContext.getMibInstrum().getMibBuilder()

(MibScalar, MibScalarInstance) = mibBuilder.importSymbols(
    'SNMPv2-SMI',
    'MibScalar',
    'MibScalarInstance'
)
ENTERPRISE_BASE = (1,3,6,1,4,1,53864)
avgPowerOid = ENTERPRISE_BASE + (1,)
latest_avg_power = 0.0

def udp_listener():
    global latest_avg_power
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 9999))

    while True:
        data, _ = sock.recvfrom(1024)
        try:
            latest_avg_power = float(data.decode())
        except:
            pass

threading.Thread(target=udp_listener, daemon=True).start()

# Δηλώνουμε το scalar
mibBuilder.exportSymbols(
    '__MY_MIB',
    MibScalar(avgPowerOid, OctetString()).setMaxAccess('readonly')
)

# Custom dynamic instance
class AvgPowerInstance(MibScalarInstance):
    def readGet(self, name, *args):
        return name, OctetString(str(latest_avg_power))

# Δηλώνουμε το instance (.0)
mibBuilder.exportSymbols(
    '__MY_MIB',
    AvgPowerInstance(avgPowerOid, (0,), OctetString("0"))
)

# ---- Register responder ----
cmdrsp.GetCommandResponder(snmpEngine, snmpContext)

print("SNMP agent running on UDP 2001")

snmpEngine.transportDispatcher.jobStarted(1)
snmpEngine.transportDispatcher.runDispatcher()
