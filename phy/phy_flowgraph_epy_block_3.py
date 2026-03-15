"""
Embedded Python Blocks:

Each time this file is saved, GRC will instantiate the first class it finds
to get ports and parameters of your block. The arguments to __init__  will
be the parameters. All of them are required to have default values!
"""

import numpy as np
from gnuradio import gr
import time

CONTROL_FILE = "/home/georgia/Desktop/SDR/control/phy_control.txt"


class blk(gr.sync_block):
    """Adds controllable complex Gaussian noise to a complex stream"""

    def __init__(self, noise_voltage=0.0, poll_interval=0.2):
        gr.sync_block.__init__(
            self,
            name='SNMP Noise Control',
            in_sig=[np.complex64],
            out_sig=[np.complex64]
        )
        self.noise_voltage = float(noise_voltage)
        self.last_noise = float(noise_voltage)
        self.poll_interval = float(poll_interval)
        self._last_poll = 0.0

    def _update_noise_from_file(self):
        now = time.monotonic()
        if now - self._last_poll < self.poll_interval:
            return

        self._last_poll = now

        try:
            with open(CONTROL_FILE) as f:
                for line in f:
                    if line.startswith("noise="):
                        noise_value = float(line.split("=", 1)[1].strip())
                        if noise_value != self.last_noise:
                            self.noise_voltage = noise_value
                            self.last_noise = noise_value
                        break
        except Exception:
            pass

    def work(self, input_items, output_items):
        self._update_noise_from_file()

        in0 = input_items[0]
        out = output_items[0]

        if self.noise_voltage <= 0.0:
            out[:] = in0
            return len(out)

        sigma = self.noise_voltage / np.sqrt(2.0)
        
        noise_real = np.random.normal(0.0, sigma, len(in0)).astype(np.float32)
        noise_imag = np.random.normal(0.0, sigma, len(in0)).astype(np.float32)

        out[:] = in0 + noise_real + 1j * noise_imag
        return len(out)