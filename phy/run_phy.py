#!/usr/bin/env python3
import signal
import sys
from pathlib import Path

from PyQt5 import Qt

from phy_flowgraph import phy_flowgraph

# Allow importing the shared control client from workspace root.
WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from control.zmq_client import ControllerClient
from transport.zmq_sub import ControlUpdateSubscriber

CONTROL_FILE = "/home/georgia/Desktop/SDR/control/phy_control.txt"

# 0=BPSK, 1=QPSK, 2=8PSK, 3=16QAM, 4=64QAM
MOD_SCHEME_MAP = {
    0: ("PSK", 2),
    1: ("PSK", 4),
    2: ("PSK", 8),
    3: ("QAM", 16),
    4: ("QAM", 64),
}


class controlled_phy_flowgraph(phy_flowgraph):
    def __init__(self):
        super().__init__()

        # If the generated file contains temporary control polling, disable it.
        try:
            if hasattr(self, "_control_timer"):
                self._control_timer.stop()
        except Exception:
            pass

        self._last_mod_scheme = None
        self._control_subscriber = None

        self._init_controller_io()
        self._sync_initial_config()

        self._control_timer = Qt.QTimer(self)
        self._control_timer.timeout.connect(self._poll_controller_updates)
        self._control_timer.start(100)

    def _init_controller_io(self):
        try:
            self._control_subscriber = ControlUpdateSubscriber()

            # Disable file polling for direct-control mode.
            try:
                self.epy_block_3.use_file_control = False
                self.epy_block_0.use_file_control = False
                self.epy_block_1.use_file_control = False
            except Exception:
                pass

            print("[PHY] Connected to controller ZMQ interfaces")
        except Exception as exc:
            print(f"[PHY] Controller ZMQ unavailable, using file fallback: {exc}")
            self._control_subscriber = None

    def _read_control_values(self):
        values = {}
        try:
            with open(CONTROL_FILE, "r") as f:
                for line in f:
                    if "=" not in line:
                        continue
                    key, value = line.strip().split("=", 1)
                    values[key] = value
        except Exception:
            return values
        return values

    def _apply_mod_scheme(self, scheme):
        if scheme not in MOD_SCHEME_MAP:
            return

        mod_type, modulation = MOD_SCHEME_MAP[scheme]

        if self.mod_type != mod_type:
            self.set_mod_type(mod_type)
        if self.Modulation != modulation:
            self.set_Modulation(modulation)

        # Keep differential encoder/decoder modulus in sync for PSK profiles.
        try:
            modulus = modulation if mod_type == "PSK" else 1
            self.digital_diff_encoder_bb_0.set_modulus(modulus)
            self.digital_diff_decoder_bb_0.set_modulus(modulus)
        except Exception:
            pass

    def _apply_mod_scheme_from_control(self):
        values = self._read_control_values()
        raw = values.get("mod_scheme")
        if raw is None:
            return

        try:
            scheme = int(raw)
        except ValueError:
            return

        if scheme == self._last_mod_scheme:
            return

        self._apply_mod_scheme(scheme)
        self._last_mod_scheme = scheme

    def _apply_runtime_param(self, key, value):
        if key == "mod_scheme":
            scheme = int(value)
            if scheme != self._last_mod_scheme:
                self._apply_mod_scheme(scheme)
                self._last_mod_scheme = scheme
            return

        if key == "noise":
            self.epy_block_3.set_noise_voltage(float(value))
            return

        if key == "snr":
            self.epy_block_3.set_snr_db(float(value))
            return

        if key == "freq_offset":
            self.epy_block_3.set_freq_offset_hz(float(value))
            return

        if key == "rate":
            self.epy_block_0.set_packet_rate(int(value))
            return

        if key == "ber_inject":
            self.epy_block_1.set_ber_inject(float(value))
            return

    def _sync_initial_config(self):
        if self._control_subscriber is None:
            self._apply_mod_scheme_from_control()
            return

        try:
            with ControllerClient() as client:
                snapshot = client.get_all_params()
        except Exception:
            snapshot = {}

        if snapshot:
            for key, value in snapshot.items():
                try:
                    self._apply_runtime_param(key, value)
                except (ValueError, TypeError):
                    continue
            print("[PHY] Applied initial full config from controller snapshot")

    def _poll_controller_updates(self):
        if self._control_subscriber is None:
            self._apply_mod_scheme_from_control()
            return

        while True:
            update = self._control_subscriber.receive(timeout=1)
            if update is None:
                break

            topic = update.get("topic")
            key = update.get("param")
            value = update.get("value")
            try:
                self._apply_runtime_param(key, value)
                print(f"[PHY] Applied controller update: {topic} -> {key}={value}")
            except (ValueError, TypeError):
                continue

    def close_controller_io(self):
        if self._control_subscriber is not None:
            try:
                self._control_subscriber.close()
            except Exception:
                pass
            self._control_subscriber = None


def main():
    qapp = Qt.QApplication(sys.argv)

    tb = controlled_phy_flowgraph()

    tb.start()
    tb.show()

    def sig_handler(sig=None, frame=None):
        tb.close_controller_io()
        tb.stop()
        tb.wait()
        Qt.QApplication.quit()

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    timer = Qt.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    qapp.exec_()


if __name__ == "__main__":
    main()
