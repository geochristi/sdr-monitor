#!/usr/bin/env python3

try:
    with open("/tmp/phy_stats.txt") as f:
        content = f.read().strip()
        bits, errors = content.split(",")

        bits = float(bits)
        errors = float(errors)

        if bits == 0:
            print(0)
        else:
            print(errors / bits)

except:
    print(0)