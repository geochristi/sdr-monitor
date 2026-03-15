#!/usr/bin/env python3
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    from .oids import *
except ImportError:
    from oids import *

from transport.zmq_sub import ZMQSubscriber
from phy_metrics.metrics_engine import PhyMetricsEngine

subscriber = ZMQSubscriber()
engine = PhyMetricsEngine()

CONTROL_FILE = "/home/georgia/Desktop/SDR/control/phy_control.txt"
noise_value = 0.0
reset_bits_base = 0
reset_errors_base = 0

# Ensure control file exists with a default value
if not os.path.exists(CONTROL_FILE):
    try:
        with open(CONTROL_FILE, "w") as f:
            f.write("noise=0.1\n")
    except Exception:
        pass

# NOTE: Avoid printing to stdout. pass_persist uses stdout for the SNMP protocol.
# Debug messages must go to stderr or a log file.
def update_metrics():
    #while True:
    data = subscriber.receive(timeout=0)
    if data is not None:
        engine.update(data)

def read_noise():
    global noise_value
    try:
        with open(CONTROL_FILE) as f:
            for line in f:
                k, v = line.strip().split("=")
                if k == "noise":
                    noise_value = float(v)
    except:
        pass
    return noise_value


def write_noise(value):
    global noise_value
    noise_value = value
    with open(CONTROL_FILE, "w") as f:
        f.write(f"noise={noise_value}\n")

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

    elif oid_n == normalize_oid(OID_BITS):
        return "integer", bits

    elif oid_n == normalize_oid(OID_ERRORS):
        return "integer", errors

    elif oid_n == normalize_oid(OID_BER):
        return "string", str(round(ber, 6))

    elif oid_n == normalize_oid(OID_RESET_BER):
        return "integer", 0

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
            write_noise(value)
            return True
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
