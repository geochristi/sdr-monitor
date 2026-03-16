#!/usr/bin/env python3
import signal
import sys

from PyQt5 import Qt

from phy_flowgraph import phy_flowgraph

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

        self._control_timer = Qt.QTimer(self)
        self._control_timer.timeout.connect(self._apply_mod_scheme_from_control)
        self._control_timer.start(200)
        self._apply_mod_scheme_from_control()

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


def main():
    qapp = Qt.QApplication(sys.argv)

    tb = controlled_phy_flowgraph()

    tb.start()
    tb.show()

    def sig_handler(sig=None, frame=None):
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
