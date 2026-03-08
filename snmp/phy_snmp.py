#!/usr/bin/env python3
import os
import sys

try:
    from .oids import *
except ImportError:
    from oids import *

STATS_FILE = "/tmp/phy_stats.txt"
CONTROL_FILE = "/home/georgia/Desktop/SDR/control/phy_control.txt"


def read_stats():
    try:
        with open(STATS_FILE) as f:
            bits, errors = f.readline().strip().split(",")
            return int(bits), int(errors)
    except:
        return 0, 0

def read_noise():
    try:
        with open(CONTROL_FILE) as f:
            for line in f:
                if line.startswith("noise="):
                    return float(line.split("=")[1])
    except:
        pass
    return 0


def write_noise(value):
    with open(CONTROL_FILE, "w") as f:
        f.write(f"noise={value}\n")

def compute_ber(bits, errors):
    ber = errors / bits if bits > 0 else 0.0
    return str(round(ber,6))

def handle_get(oid):
    bits, errors = read_stats()
    if oid.startswith(OID_NOISE):
        return "integer", int(read_noise() * 10)  # Scale noise by 10 for better SNMP representation

    elif oid == OID_BITS:
        return "integer", bits

    elif oid == OID_ERRORS:
        return "integer", errors
    # TODO IF-MIB is currently used by the system and we need to bypass it
    # elif oid == ".1.3.6.1.2.1.2.2.1.10.1":   # ifInOctets
    #     # ifinOctets is bits/8 since it's counting bytes, not bits
    #     bits, errors = read_stats()
    #     octets = bits // 8
    #     return "integer", octets

    # elif oid == ".1.3.6.1.2.1.2.2.1.14.1": # ifInErrors
    #     bits, errors = read_stats()
    #     return "integer", errors

    elif oid == OID_BER:
        return "string", compute_ber(bits, errors)

    return None
def oid_to_tuple(oid):
    return tuple(int(x) for x in oid.strip(".").split("."))


def oid_gt(a, b):
    return oid_to_tuple(a) > oid_to_tuple(b)

def handle_getnext(oid):
    sorted_oids = sorted(OIDS, key=oid_to_tuple)
    for o in sorted_oids:
        if oid_gt(o, oid):
            value = handle_get(o)
            if value:
                typ, val = value
                return o, typ, val
    return None

def handle_set(oid, value):
    if oid == OID_NOISE:
        try:
            write_noise(value / 10) # because noise usually is < 1
            return True
        except ValueError:
            return False
    return False

def main():
    while True:

        cmd = sys.stdin.readline().strip()

        if not cmd:
            continue
        
        if cmd == "PING":
            print("PONG")
            sys.stdout.flush()
            continue


        elif cmd == "get":
            oid = sys.stdin.readline().strip()
            result = handle_get(oid)
            if result:
                typ, val = result
                print(oid)
                print(typ)
                print(val)
            else:
                print("NONE")
        
        elif cmd == "getnext":
            oid = sys.stdin.readline().strip()
            result = handle_getnext(oid)
            if result:
                o, typ, val = result
                print(o)
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
