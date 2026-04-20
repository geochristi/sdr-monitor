#!/usr/bin/env python3

import json
import socket

import pmt

import control.zmq_controller as zmq_controller_module


def _free_tcp_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main():
    original_req_rep_addr = zmq_controller_module.REQ_REP_ADDR
    original_pub_addr = zmq_controller_module.PUB_ADDR
    original_control_pub_addr = zmq_controller_module.CONTROL_PUB_ADDR
    original_pull_addr = zmq_controller_module.PULL_ADDR

    zmq_controller_module.REQ_REP_ADDR = f"tcp://127.0.0.1:{_free_tcp_port()}"
    zmq_controller_module.PUB_ADDR = f"tcp://127.0.0.1:{_free_tcp_port()}"
    zmq_controller_module.CONTROL_PUB_ADDR = f"tcp://127.0.0.1:{_free_tcp_port()}"
    zmq_controller_module.PULL_ADDR = f"tcp://127.0.0.1:{_free_tcp_port()}"

    controller = zmq_controller_module.ZMQController()
    try:
        plain_metrics = {"bits": 12, "errors": 1}
        decoded_plain = controller._decode_metrics_message(
            json.dumps(plain_metrics).encode("utf-8")
        )
        assert decoded_plain == plain_metrics

        pmt_metrics = {"bits": 34, "errors": 2}
        payload = json.dumps(pmt_metrics).encode("utf-8")
        wire = pmt.serialize_str(pmt.init_u8vector(len(payload), list(payload)))
        decoded_pmt = controller._decode_metrics_message(wire)
        assert decoded_pmt == pmt_metrics

        print("OK: metrics decoder accepts plain JSON and PMT-wrapped JSON")
    finally:
        controller.stop()
        zmq_controller_module.REQ_REP_ADDR = original_req_rep_addr
        zmq_controller_module.PUB_ADDR = original_pub_addr
        zmq_controller_module.CONTROL_PUB_ADDR = original_control_pub_addr
        zmq_controller_module.PULL_ADDR = original_pull_addr


if __name__ == "__main__":
    main()