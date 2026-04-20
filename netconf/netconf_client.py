#!/usr/bin/env python3
"""
NETCONF client for SDR PHY configuration.

Connects to a netopeer2-server instance (which backs onto sysrepo) and
reads/modifies the sdr-phy YANG model over the standard NETCONF protocol.

Architecture:
    This client  →  netopeer2-server (port 830, SSH)
                         ↓
                     sysrepo (running datastore)
                         ↓
                   sdr_controller (C subscriber)
                         ↓
                   zmq_controller.py  →  PHY

Start the NETCONF server before using this client:
    sudo netopeer2-server -d -v2

Usage examples:
    python3 netconf_client.py get
    python3 netconf_client.py set noise 0.02
    python3 netconf_client.py set rate 200
    python3 netconf_client.py set-config '{"noise": 0.02, "rate": 200, "mod_scheme": 1}'
"""

import argparse
import getpass
import json
import os
import sys
import xml.etree.ElementTree as ET

from ncclient import manager

# -----------------------------------------------------------------
# YANG model constants
# -----------------------------------------------------------------

YANG_NS = "urn:sdr:phy"
PASSWORD_ENV_VAR = "NETCONF_PASSWORD"

# Map user-friendly canonical keys → YANG leaf names
KEY_TO_LEAF: dict[str, str] = {
    "noise":       "noise_level",
    "rate":        "packet_rate",
    "freq_offset": "frequency_offset",
    "mod_scheme":  "mod_scheme",
    "snr":         "snr",
    "ber_inject":  "ber_inject",
    "tx_gain":     "tx_gain",
    "rx_gain":     "rx_gain",
}

# Reverse: YANG leaf name → canonical key
LEAF_TO_KEY: dict[str, str] = {v: k for k, v in KEY_TO_LEAF.items()}

# Leaves whose values should be treated as integers
INT_LEAVES = {"mod_scheme", "packet_rate", "frequency_offset"}


# -----------------------------------------------------------------
# XML helpers
# -----------------------------------------------------------------

def _edit_config_xml(params: dict) -> str:
    """Build the <config> payload for an <edit-config> RPC."""
    leaves = ""
    for key, value in params.items():
        leaf = KEY_TO_LEAF.get(key, key)
        leaves += f"  <{leaf}>{value}</{leaf}>\n"
    return (
        '<config xmlns:xc="urn:ietf:params:xml:ns:netconf:base:1.0">'
        f'<phy xmlns="{YANG_NS}">\n'
        f"{leaves}"
        "</phy>"
        "</config>"
    )


def _subtree_filter() -> tuple:
    """Return a (type, xml) tuple for the entire <phy> container."""
    return ("subtree", f'<phy xmlns="{YANG_NS}"/>')


# -----------------------------------------------------------------
# Client class
# -----------------------------------------------------------------

class SDRNetconfClient:
    """
    NETCONF client scoped to the sdr-phy YANG model.

    Parameters
    ----------
    host : str
        Hostname / IP of the NETCONF server (default ``127.0.0.1``).
    port : int
        SSH port (default ``830`` — standard NETCONF port).
    username : str
        SSH username (default: current OS user).
    password : str | None
        SSH password.  Leave ``None`` to use key-based auth.
    key_filename : str | None
        Path to a private key file.  ``None`` means let paramiko
        search ``~/.ssh``.
    hostkey_verify : bool
        Whether to verify the server host key (default ``False``
        for local / lab use).
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 830,
        username: str | None = None,
        password: str | None = None,
        key_filename: str | None = None,
        hostkey_verify: bool = False,
    ):
        self.host = host
        self.port = port
        self.username = username or os.environ.get("USER", getpass.getuser())
        self.password = password
        self.key_filename = key_filename
        self.hostkey_verify = hostkey_verify
        self._mgr: manager.Manager | None = None

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "SDRNetconfClient":
        self.connect()
        return self

    def __exit__(self, *_) -> None:
        self.disconnect()

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Open the NETCONF session."""
        password = self.password or os.environ.get(PASSWORD_ENV_VAR)
        look_for_keys = self.key_filename is not None
        if password is None and not look_for_keys:
            if not sys.stdin.isatty():
                raise RuntimeError(
                    "No NETCONF password available in a non-interactive session. "
                    f"Set {PASSWORD_ENV_VAR} or pass --password."
                )
            password = getpass.getpass(f"Password for {self.username}@{self.host}: ")
        self._mgr = manager.connect(
            host=self.host,
            port=self.port,
            username=self.username,
            password=password,
            key_filename=self.key_filename,
            hostkey_verify=self.hostkey_verify,
            look_for_keys=look_for_keys,
            allow_agent=False,
        )

    def disconnect(self) -> None:
        """Close the NETCONF session."""
        if self._mgr:
            self._mgr.close_session()
            self._mgr = None

    # ------------------------------------------------------------------
    # NETCONF operations
    # ------------------------------------------------------------------

    def get_config(self) -> dict:
        """
        Return the current running configuration as a canonical-key dict.

        Example return value::

            {
                "noise":       0.02,
                "rate":        100,
                "freq_offset": 0,
                "mod_scheme":  3,
                "snr":         30.0,
                "ber_inject":  0.0,
                "tx_gain":     10.0,
                "rx_gain":     10.0,
            }
        """
        reply = self._mgr.get_config(
            source="running",
            filter=_subtree_filter(),
        )
        return self._parse_phy_xml(reply.data_xml)

    def set_param(self, key: str, value) -> None:
        """
        Set a single PHY parameter.

        ``key`` can be a canonical name (``noise``, ``rate``, …) or a
        YANG leaf name (``noise_level``, ``packet_rate``, …).
        """
        self.set_config({key: value})

    def set_config(self, params: dict) -> None:
        """
        Apply multiple PHY parameters in a single ``<edit-config>``.

        ``params`` is a dict of canonical keys (or YANG leaf names)
        to values, matching the format used by the rest of the stack::

            client.set_config({"noise": 0.02, "rate": 200, "mod_scheme": 1})
        """
        config_xml = _edit_config_xml(params)
        self._mgr.edit_config(target="running", config=config_xml)

    def get_capabilities(self) -> list[str]:
        """Return the server's advertised NETCONF capabilities."""
        return list(self._mgr.server_capabilities)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_phy_xml(data_xml: str) -> dict:
        """Parse the <data> XML returned by <get-config> into a dict."""
        try:
            root = ET.fromstring(data_xml)
        except ET.ParseError:
            return {}

        ns = {"s": YANG_NS}
        phy = root.find(".//s:phy", ns)
        if phy is None:
            return {}

        result: dict = {}
        for child in phy:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            key = LEAF_TO_KEY.get(tag, tag)
            text = child.text
            if tag in INT_LEAVES:
                try:
                    result[key] = int(text)
                    continue
                except (ValueError, TypeError):
                    pass
            try:
                result[key] = float(text)
            except (ValueError, TypeError):
                result[key] = text

        return result


# -----------------------------------------------------------------
# CLI
# -----------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="netconf_client.py",
        description="NETCONF client for the SDR PHY sdr-phy YANG model.",
    )
    p.add_argument("--host", default="127.0.0.1", help="NETCONF server host (default: 127.0.0.1)")
    p.add_argument("--port", type=int, default=830, help="NETCONF server port (default: 830)")
    p.add_argument("--user", default=None, help="SSH username (default: current OS user)")
    p.add_argument("--password", default=None, help="SSH password (or set NETCONF_PASSWORD)")
    p.add_argument("--key", default=None, help="Path to SSH private key file")

    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("get", help="Print the current running configuration")
    sub.add_parser("capabilities", help="List server NETCONF capabilities")

    set_p = sub.add_parser("set", help="Set a single parameter: set <key> <value>")
    set_p.add_argument("key", help="Parameter name (e.g. noise, rate, mod_scheme)")
    set_p.add_argument("value", help="New value")

    sc_p = sub.add_parser(
        "set-config",
        help='Set multiple parameters from a JSON object: set-config \'{"noise":0.02,"rate":200}\'',
    )
    sc_p.add_argument("json_params", help="JSON object of key→value pairs")

    return p


def _coerce(value: str):
    """Try to parse a CLI string as int, then float, then keep as string."""
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def main() -> int:
    args = _build_parser().parse_args()

    client = SDRNetconfClient(
        host=args.host,
        port=args.port,
        username=args.user,
        password=args.password,
        key_filename=args.key,
    )

    try:
        client.connect()
    except Exception as exc:
        print(f"Connection failed: {exc}", file=sys.stderr)
        print(
            "\nServer startup:\n"
            "  cd netconf && ./start_netopeer2.sh\n\n"
            "Client auth:\n"
            "  python3 netconf/netconf_client.py --password '<linux-password>' get\n"
            f"  or export {PASSWORD_ENV_VAR}='<linux-password>'",
            file=sys.stderr,
        )
        return 1

    try:
        if args.cmd == "get":
            config = client.get_config()
            if not config:
                print("(no config returned — phy container may be empty)")
            else:
                col = max(len(k) for k in config) + 2
                for key, val in sorted(config.items()):
                    print(f"  {key:<{col}}{val}")

        elif args.cmd == "capabilities":
            for cap in sorted(client.get_capabilities()):
                print(cap)

        elif args.cmd == "set":
            client.set_param(args.key, _coerce(args.value))
            print(f"OK — {args.key} = {args.value}")

        elif args.cmd == "set-config":
            try:
                params = json.loads(args.json_params)
            except json.JSONDecodeError as exc:
                print(f"Invalid JSON: {exc}", file=sys.stderr)
                return 1
            client.set_config(params)
            print(f"OK — applied {len(params)} parameter(s)")

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        client.disconnect()

    return 0


if __name__ == "__main__":
    sys.exit(main())
