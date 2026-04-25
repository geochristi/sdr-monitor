#!/usr/bin/env python3
"""
Single-run latency comparison for ZMQ, SNMP, and NETCONF.

This keeps all protocols in the same loop so conditions are as equal as possible.

Usage:
    python3 compare_protocols_one_run.py --runs 100

Prerequisites:
    - ZMQ controller running on tcp://127.0.0.1:5555
    - snmpd pass_persist handler running (for snmpset)
    - NETCONF server running (netopeer2 + sdr_controller bridge)
    - NETCONF_PASSWORD env var set if password auth is required
"""

import argparse
import shutil
import statistics
import subprocess
import time
from dataclasses import dataclass, field
from typing import Dict, List

from control.zmq_client import ControllerClient
from netconf.netconf_client import SDRNetconfClient

DEFAULT_SNMP_OID_MOD_SCHEME = ".1.3.6.1.4.1.53864.1.8.0"
DEFAULT_SNMP_OID_PACKET_RATE = ".1.3.6.1.4.1.53864.1.6.0"
DEFAULT_SNMP_OID_FREQ_OFFSET = ".1.3.6.1.4.1.53864.1.7.0"


@dataclass
class BenchResult:
    samples: List[float] = field(default_factory=list)
    errors: int = 0

    def add(self, seconds: float) -> None:
        self.samples.append(seconds)

    def fail(self) -> None:
        self.errors += 1

    @property
    def n(self) -> int:
        return len(self.samples)

    def summary_ms(self) -> str:
        if not self.samples:
            return "no successful samples"
        mean_ms = statistics.mean(self.samples) * 1000.0
        stdev_ms = statistics.stdev(self.samples) * 1000.0 if len(self.samples) > 1 else 0.0
        min_ms = min(self.samples) * 1000.0
        max_ms = max(self.samples) * 1000.0
        return (
            f"mean={mean_ms:.2f}ms std={stdev_ms:.2f}ms "
            f"min={min_ms:.2f}ms max={max_ms:.2f}ms n={self.n} errors={self.errors}"
        )


def run_once(
    runs: int,
    snmp_host: str,
    snmp_write_community: str,
    snmp_oid_mod_scheme: str,
    netconf_host: str,
    netconf_port: int,
    zmq_timeout_ms: int,
) -> Dict[str, BenchResult]:
    results: Dict[str, BenchResult] = {
        "zmq": BenchResult(),
        "snmp": BenchResult(),
        "netconf": BenchResult(),
    }

    if shutil.which("snmpset") is None:
        raise RuntimeError("snmpset not found in PATH. Install net-snmp tools.")

    zmq = ControllerClient(timeout=zmq_timeout_ms)
    netconf = SDRNetconfClient(host=netconf_host, port=netconf_port, hostkey_verify=False)

    try:
        netconf.connect()
    except Exception as exc:
        zmq.close()
        raise RuntimeError(
            "NETCONF connect failed. Ensure server is running and NETCONF_PASSWORD is set if needed."
        ) from exc

    try:
        # Warm-up to avoid first-request penalties skewing results too much.
        try:
            zmq.set_param("mod_scheme", 0, source="bench-warmup")
        except Exception:
            pass
        try:
            subprocess.run(
                [
                    "snmpset",
                    "-v2c",
                    "-c",
                    snmp_write_community,
                    snmp_host,
                    snmp_oid_mod_scheme,
                    "i",
                    "0",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception:
            pass
        try:
            netconf.set_param("mod_scheme", 0)
        except Exception:
            pass

        for i in range(runs):
            val = i % 5

            # 1) ZMQ baseline
            t0 = time.perf_counter()
            try:
                zmq.set_param("mod_scheme", val, source="bench-zmq")
                results["zmq"].add(time.perf_counter() - t0)
            except Exception:
                results["zmq"].fail()

            # 2) SNMP
            t0 = time.perf_counter()
            try:
                proc = subprocess.run(
                    [
                        "snmpset",
                        "-v2c",
                        "-c",
                        snmp_write_community,
                        snmp_host,
                        snmp_oid_mod_scheme,
                        "i",
                        str(val),
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if proc.returncode == 0:
                    results["snmp"].add(time.perf_counter() - t0)
                else:
                    results["snmp"].fail()
            except Exception:
                results["snmp"].fail()

            # 3) NETCONF
            t0 = time.perf_counter()
            try:
                netconf.set_param("mod_scheme", val)
                results["netconf"].add(time.perf_counter() - t0)
            except Exception:
                results["netconf"].fail()

    finally:
        try:
            netconf.disconnect()
        except Exception:
            pass
        zmq.close()

    return results


def run_multi_param_once(
    runs: int,
    snmp_host: str,
    snmp_write_community: str,
    snmp_oid_mod_scheme: str,
    snmp_oid_packet_rate: str,
    snmp_oid_freq_offset: str,
    netconf_host: str,
    netconf_port: int,
    zmq_timeout_ms: int,
) -> Dict[str, BenchResult]:
    """
    Compare latency when setting multiple parameters in one logical operation.

    - ZMQ: 3 sequential set_param calls in one timed block.
    - SNMP: 3 sequential snmpset calls in one timed block.
    - NETCONF: 1 set_config call with all 3 params in one edit-config RPC.
    """
    results: Dict[str, BenchResult] = {
        "zmq": BenchResult(),
        "snmp": BenchResult(),
        "netconf": BenchResult(),
    }

    if shutil.which("snmpset") is None:
        raise RuntimeError("snmpset not found in PATH. Install net-snmp tools.")

    zmq = ControllerClient(timeout=zmq_timeout_ms)
    netconf = SDRNetconfClient(host=netconf_host, port=netconf_port, hostkey_verify=False)

    try:
        netconf.connect()
    except Exception as exc:
        zmq.close()
        raise RuntimeError(
            "NETCONF connect failed. Ensure server is running and NETCONF_PASSWORD is set if needed."
        ) from exc

    try:
        # Warm-up operation for all protocols.
        try:
            zmq.set_param("mod_scheme", 0, source="bench-warmup")
            zmq.set_param("rate", 100, source="bench-warmup")
            zmq.set_param("freq_offset", 0, source="bench-warmup")
        except Exception:
            pass

        try:
            for oid, val in (
                (snmp_oid_mod_scheme, "0"),
                (snmp_oid_packet_rate, "100"),
                (snmp_oid_freq_offset, "0"),
            ):
                subprocess.run(
                    [
                        "snmpset",
                        "-v2c",
                        "-c",
                        snmp_write_community,
                        snmp_host,
                        oid,
                        "i",
                        val,
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
        except Exception:
            pass

        try:
            netconf.set_config({"mod_scheme": 0, "rate": 100, "freq_offset": 0})
        except Exception:
            pass

        for i in range(runs):
            mod_val = i % 5
            rate_val = 100 + (i % 10)
            freq_val = ((i % 9) - 4) * 100

            # 1) ZMQ multi-parameter operation (3 sets grouped in one timed block)
            t0 = time.perf_counter()
            try:
                zmq.set_param("mod_scheme", mod_val, source="bench-zmq-multi")
                zmq.set_param("rate", rate_val, source="bench-zmq-multi")
                zmq.set_param("freq_offset", freq_val, source="bench-zmq-multi")
                results["zmq"].add(time.perf_counter() - t0)
            except Exception:
                results["zmq"].fail()

            # 2) SNMP multi-parameter operation (3 snmpset grouped in one timed block)
            t0 = time.perf_counter()
            try:
                ok = True
                for oid, val in (
                    (snmp_oid_mod_scheme, str(mod_val)),
                    (snmp_oid_packet_rate, str(rate_val)),
                    (snmp_oid_freq_offset, str(freq_val)),
                ):
                    proc = subprocess.run(
                        [
                            "snmpset",
                            "-v2c",
                            "-c",
                            snmp_write_community,
                            snmp_host,
                            oid,
                            "i",
                            val,
                        ],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if proc.returncode != 0:
                        ok = False
                        break
                if ok:
                    results["snmp"].add(time.perf_counter() - t0)
                else:
                    results["snmp"].fail()
            except Exception:
                results["snmp"].fail()

            # 3) NETCONF multi-parameter operation (single edit-config)
            t0 = time.perf_counter()
            try:
                netconf.set_config(
                    {
                        "mod_scheme": mod_val,
                        "rate": rate_val,
                        "freq_offset": freq_val,
                    }
                )
                results["netconf"].add(time.perf_counter() - t0)
            except Exception:
                results["netconf"].fail()

    finally:
        try:
            netconf.disconnect()
        except Exception:
            pass
        zmq.close()

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare protocol latency in one run")
    parser.add_argument("--runs", type=int, default=100, help="Number of loop iterations")
    parser.add_argument("--snmp-host", default="localhost", help="SNMP agent host")
    parser.add_argument("--snmp-write-community", default="private", help="SNMP write community")
    parser.add_argument("--snmp-oid-mod-scheme", default=DEFAULT_SNMP_OID_MOD_SCHEME, help="OID for mod_scheme")
    parser.add_argument("--snmp-oid-packet-rate", default=DEFAULT_SNMP_OID_PACKET_RATE, help="OID for packet rate")
    parser.add_argument("--snmp-oid-freq-offset", default=DEFAULT_SNMP_OID_FREQ_OFFSET, help="OID for freq offset")
    parser.add_argument("--netconf-host", default="127.0.0.1", help="NETCONF host")
    parser.add_argument("--netconf-port", type=int, default=830, help="NETCONF port")
    parser.add_argument("--zmq-timeout-ms", type=int, default=5000, help="ZMQ request timeout in ms")
    args = parser.parse_args()

    if args.runs <= 0:
        raise SystemExit("--runs must be > 0")

    single_results = run_once(
        runs=args.runs,
        snmp_host=args.snmp_host,
        snmp_write_community=args.snmp_write_community,
        snmp_oid_mod_scheme=args.snmp_oid_mod_scheme,
        netconf_host=args.netconf_host,
        netconf_port=args.netconf_port,
        zmq_timeout_ms=args.zmq_timeout_ms,
    )

    multi_results = run_multi_param_once(
        runs=args.runs,
        snmp_host=args.snmp_host,
        snmp_write_community=args.snmp_write_community,
        snmp_oid_mod_scheme=args.snmp_oid_mod_scheme,
        snmp_oid_packet_rate=args.snmp_oid_packet_rate,
        snmp_oid_freq_offset=args.snmp_oid_freq_offset,
        netconf_host=args.netconf_host,
        netconf_port=args.netconf_port,
        zmq_timeout_ms=args.zmq_timeout_ms,
    )

    print(f"runs={args.runs}")

    print("\n[single-param operation: mod_scheme only]")
    for proto in ("zmq", "snmp", "netconf"):
        print(f"{proto}: {single_results[proto].summary_ms()}")

    print("\n[multi-param operation: mod_scheme + rate + freq_offset]")
    for proto in ("zmq", "snmp", "netconf"):
        print(f"{proto}: {multi_results[proto].summary_ms()}")


if __name__ == "__main__":
    main()
