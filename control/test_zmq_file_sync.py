#!/usr/bin/env python3

import socket
import tempfile
import threading
import time
from pathlib import Path

import control.controller as controller_module
import control.zmq_controller as zmq_controller_module
from control.zmq_client import ControllerClient


def _free_tcp_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_for(predicate, timeout=2.0, interval=0.05):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def main():
    with tempfile.TemporaryDirectory() as tmpdir:
        control_file = Path(tmpdir) / "phy_control.txt"
        fallback_file = Path(tmpdir) / "phy_cotrol.txt"

        original_control_file = controller_module.CONTROL_FILE
        original_fallback_file = controller_module.FALLBACK_CONTROL_FILE
        original_req_rep_addr = zmq_controller_module.REQ_REP_ADDR
        original_pub_addr = zmq_controller_module.PUB_ADDR
        original_control_pub_addr = zmq_controller_module.CONTROL_PUB_ADDR
        original_pull_addr = zmq_controller_module.PULL_ADDR

        controller = None
        try:
            controller_module.CONTROL_FILE = str(control_file)
            controller_module.FALLBACK_CONTROL_FILE = str(fallback_file)

            zmq_controller_module.REQ_REP_ADDR = f"tcp://127.0.0.1:{_free_tcp_port()}"
            zmq_controller_module.PUB_ADDR = f"tcp://127.0.0.1:{_free_tcp_port()}"
            zmq_controller_module.CONTROL_PUB_ADDR = f"tcp://127.0.0.1:{_free_tcp_port()}"
            zmq_controller_module.PULL_ADDR = f"tcp://127.0.0.1:{_free_tcp_port()}"

            controller = zmq_controller_module.ZMQController()
            thread = threading.Thread(target=controller.start, daemon=True)
            thread.start()

            with ControllerClient(req_rep_addr=zmq_controller_module.REQ_REP_ADDR, timeout=2000) as client:
                client.set_param("noise", 0.7, source="test-zmq-file-sync")

            synced = _wait_for(
                lambda: control_file.exists() and "noise=0.7" in control_file.read_text(encoding="utf-8"),
            )
            if not synced:
                raise AssertionError("ZMQ controller did not mirror updates to the control file")

            print("OK: ZMQ controller keeps the legacy control file synchronized")
        finally:
            if controller is not None:
                controller.stop()

            controller_module.CONTROL_FILE = original_control_file
            controller_module.FALLBACK_CONTROL_FILE = original_fallback_file
            zmq_controller_module.REQ_REP_ADDR = original_req_rep_addr
            zmq_controller_module.PUB_ADDR = original_pub_addr
            zmq_controller_module.CONTROL_PUB_ADDR = original_control_pub_addr
            zmq_controller_module.PULL_ADDR = original_pull_addr


if __name__ == "__main__":
    main()