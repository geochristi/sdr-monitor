#!/usr/bin/env python3
# Reads bits/errors from /tmp/phy_stats.txt and prints bits, errors, or BER based on argv[1], defaulting to 0 on bad input.
import sys

STATS_FILE = "/tmp/phy_stats.txt"


def read_stats():
    stats = {}

    try:
        with open(STATS_FILE) as f:
            line = f.readline().strip()
            if line:
                parts = line.split(",")
                if len(parts) >= 2:
                    bits, errors = parts[:2]
                    stats["bits"] = int(bits)
                    stats["errors"] = int(errors)
    except Exception:
        pass

    return stats


def main():
    stats = read_stats()

    if len(sys.argv) < 2:
        print(0)
        return

    key = sys.argv[1]

    if key == "bits":
        print(stats["bits"])

    elif key == "errors":
        print(stats["errors"])

    elif key == "ber":
        bits = stats["bits"]
        errors = stats["errors"]
        ber = errors / bits if bits > 0 else 0
        print(ber)

    else:
        print(0)


if __name__ == "__main__":
    main()