#!/usr/bin/env python3
import os
import sys
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    from .oids import *
except ImportError:
    from oids import *

from transport.zmq_sub import ZMQSubscriber
from phy_metrics.metrics_engine import PhyMetricsEngine
from control.zmq_client import ControllerClient

logging.getLogger("control.zmq_client").setLevel(logging.CRITICAL)

subscriber = ZMQSubscriber()
engine = PhyMetricsEngine()
# Use ZMQ client to communicate with controller daemon
client = None

noise_value = 0.0
snr_value = 30.0
rate_value = 0
freq_offset_value = 0
mod_scheme_value = 3
ber_inject_value = 0.0
reset_bits_base = 0
reset_errors_base = 0

def get_client():
    global client
    if client is None:
        try:
            client = ControllerClient(timeout=5000)
        except Exception:
            return None
    return client


# NOTE: Avoid printing to stdout. pass_persist uses stdout for the SNMP protocol.
# Debug messages must go to stderr or a log file.
def update_metrics():
    # Drain all queued samples so computations use the latest PHY counters.
    # Reading only one queued message can leave stale pre-reset data in flight.
    while True:
        data = subscriber.receive(timeout=0)
        if data is None:
            break
        engine.update(data)

def read_control_values():
    """Read all control values from the ZMQ controller."""
    try:
        c = get_client()
        if c is None:
            return {}
        return c.get_all_params()
    except Exception:
        return {}

def write_control_values(values):
    """Write control values to the ZMQ controller."""
    try:
        c = get_client()
        if c is None:
            return False
        for key, value in values.items():
            c.set_param(key, value, source="snmp")
        return True
    except Exception:
        return False


def read_noise():
    global noise_value
    try:
        values = read_control_values()
        if "noise" in values:
            noise_value = float(values["noise"])
    except Exception:
        pass
    return noise_value

def read_snr():
    global snr_value
    try:
        values = read_control_values()
        if "snr" in values:
            snr_value = float(values["snr"])
    except Exception:
        pass
    return snr_value

def read_rate():
    global rate_value
    try:
        values = read_control_values()
        if "rate" in values:
            rate_value = int(values["rate"])
    except Exception:
        pass
    return rate_value

def read_freq_offset():
    global freq_offset_value
    try:
        values = read_control_values()
        if "freq_offset" in values:
            freq_offset_value = int(values["freq_offset"])
    except Exception:
        pass
    return freq_offset_value

def read_mod_scheme():
    global mod_scheme_value
    try:
        values = read_control_values()
        if "mod_scheme" in values:
            mod_scheme_value = int(values["mod_scheme"])
    except Exception:
        pass
    return mod_scheme_value

def read_ber_inject():
    global ber_inject_value
    try:
        values = read_control_values()
        if "ber_inject" in values:
            ber_inject_value = float(values["ber_inject"])
    except Exception:
        pass
    return ber_inject_value

def write_noise(value):
    global noise_value
    noise_value = value
    return write_control_values({"noise": noise_value})

def write_snr(value):
    global snr_value
    snr_value = value
    return write_control_values({"snr": snr_value})

def write_rate(value):
    global rate_value
    rate_value = int(value)
    return write_control_values({"rate": rate_value})

def write_freq_offset(value):
    global freq_offset_value
    freq_offset_value = int(value)
    return write_control_values({"freq_offset": freq_offset_value})

def write_mod_scheme(value):
    global mod_scheme_value
    mod_scheme_value = int(value)
    return write_control_values({"mod_scheme": mod_scheme_value})

def write_ber_inject(value):
    global ber_inject_value
    ber_inject_value = float(value)
    return write_control_values({"ber_inject": ber_inject_value})

def compute_ber(bits, errors):
    ber = errors / bits if bits > 0 else 0.0
    return str(round(ber,6))

def normalize_oid(oid: str) -> str:
    oid = oid.strip()
    return oid[:-2] if oid.endswith(".0") else oid

def instance_oid(oid: str) -> str:
    oid = normalize_oid(oid)
    return oid + ".0"

def get_effective_metrics():
    bits_raw = engine.get_metrics("bits") or 0
    errors_raw = engine.get_metrics("errors") or 0

    bits = max(0, bits_raw - reset_bits_base)
    errors = max(0, errors_raw - reset_errors_base)
    ber = (errors / bits) if bits > 0 else 0.0
    return bits, errors, ber

def handle_get(oid):
    update_metrics()
    oid_n = normalize_oid(oid)
    bits, errors, ber = get_effective_metrics()

    if oid_n == normalize_oid(OID_NOISE):
        return "integer", int(read_noise() * 10)

    elif oid_n == normalize_oid(OID_SNR):
        return "integer", int(read_snr() * 10)

    elif oid_n == normalize_oid(OID_BITS):
        return "integer", bits

    elif oid_n == normalize_oid(OID_ERRORS):
        return "integer", errors

    elif oid_n == normalize_oid(OID_BER):
        return "string", str(round(ber, 6))

    elif oid_n == normalize_oid(OID_RESET_BER):
        return "integer", 0

    elif oid_n == normalize_oid(OID_PACKET_RATE):
        return "integer", read_rate()

    elif oid_n == normalize_oid(OID_FREQ_OFFSET):
        return "integer", read_freq_offset()

    elif oid_n == normalize_oid(OID_MOD_SCHEME):
        return "integer", read_mod_scheme()

    elif oid_n == normalize_oid(OID_BER_INJECT):
        return "integer", int(read_ber_inject() * 1000000)

    return None

def oid_to_tuple(oid):
    return tuple(int(x) for x in oid.strip(".").split("."))


def oid_gt(a, b):
    return oid_to_tuple(a) > oid_to_tuple(b)

def handle_getnext(oid):
    oid_n = normalize_oid(oid)
    sorted_oids = sorted([normalize_oid(o) for o in OIDS], key=oid_to_tuple)
    for o in sorted_oids:
        if oid_gt(o, oid_n):
            value = handle_get(o)
            if value:
                typ, val = value
                return o, typ, val
    return None

def handle_set(oid, value):
    global reset_bits_base, reset_errors_base
    oid_n = normalize_oid(oid)

    if oid_n == normalize_oid(OID_NOISE):
        try:
            value = max(0.0, min(value / 10, 10.0))
            return write_noise(value)
        except ValueError:
            return False

    elif oid_n == normalize_oid(OID_SNR):
        try:
            value = max(0.0, min(value / 10, 60.0))
            return write_snr(value)
        except ValueError:
            return False

    elif oid_n == normalize_oid(OID_RESET_BER):
        if int(value) == 1:
            update_metrics()
            reset_bits_base = engine.get_metrics("bits") or 0
            reset_errors_base = engine.get_metrics("errors") or 0
            try:
                engine.reset_ber()  # optional; keep if implemented
            except Exception:
                pass
            return True
        return False

    elif oid_n == normalize_oid(OID_PACKET_RATE):
        try:
            value = max(0, min(int(value), 1000000))
            return write_rate(value)
        except ValueError:
            return False

    elif oid_n == normalize_oid(OID_FREQ_OFFSET):
        try:
            value = max(-1000000, min(int(value), 1000000))
            return write_freq_offset(value)
        except ValueError:
            return False

    elif oid_n == normalize_oid(OID_MOD_SCHEME):
        try:
            # 0=BPSK, 1=QPSK, 2=8PSK, 3=16QAM, 4=64QAM
            value = max(0, min(int(value), 4))
            return write_mod_scheme(value)
        except ValueError:
            return False

    elif oid_n == normalize_oid(OID_BER_INJECT):
        try:
            value = max(0.0, min(float(value) / 1000000.0, 1.0))
            return write_ber_inject(value)
        except ValueError:
            return False

    return False

def main():
    while True:
        cmd = sys.stdin.readline()
        if not cmd:
            break

        cmd = cmd.strip()

        if cmd == "PING":
            print("PONG")
            sys.stdout.flush()
            continue

        elif cmd == "get":
            oid = sys.stdin.readline().strip()
            result = handle_get(oid)
            if result:
                typ, val = result
                print(instance_oid(oid))   # fixed: no double .0
                print(typ)
                print(val)
            else:
                print("NONE")

        elif cmd == "getnext":
            oid = sys.stdin.readline().strip()
            result = handle_getnext(oid)
            if result:
                o, typ, val = result
                print(instance_oid(o))
                print(typ)
                print(val)
            else:
                print("NONE")

        elif cmd == "set":
            oid = sys.stdin.readline().strip()
            line = sys.stdin.readline().strip()
            typ, val = line.split(" ", 1)
            if typ == "integer":
                try:
                    val = int(val)
                except ValueError:
                    print("ERROR")
                    continue
            else:
                print("ERROR")
                continue

            success = handle_set(oid, val)
            print("DONE" if success else "ERROR")    

        sys.stdout.flush()


if __name__ == "__main__":
    main()
