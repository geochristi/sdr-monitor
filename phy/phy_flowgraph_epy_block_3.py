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
    """Adds AWGN and frequency offset with runtime control from control file."""

    def __init__(self, noise_voltage=0.0, snr_db=30.0, poll_interval=0.2, sample_rate=100000.0):
        gr.sync_block.__init__(
            self,
            name='SNMP Noise Control',
            in_sig=[np.complex64],
            out_sig=[np.complex64]
        )
        self.noise_voltage = float(noise_voltage)
        self.last_noise_voltage = float(noise_voltage)
        self.snr_db = float(snr_db)
        self.last_snr_db = float(snr_db)
        self.freq_offset_hz = 0.0
        self.last_freq_offset_hz = 0.0
        self.sample_rate = max(1.0, float(sample_rate))
        self.phase_inc = 0.0
        self.phase = 0.0
        self.poll_interval = float(poll_interval)
        self._last_poll = 0.0

    def _update_from_file(self):
        now = time.monotonic()
        if now - self._last_poll < self.poll_interval:
            return

        self._last_poll = now

        try:
            with open(CONTROL_FILE) as f:
                for line in f:
                    if line.startswith("snr="):
                        snr_value = float(line.split("=", 1)[1].strip())
                        if snr_value != self.last_snr_db:
                            self.snr_db = snr_value
                            self.last_snr_db = snr_value
                    elif line.startswith("noise="):
                        noise_value = float(line.split("=", 1)[1].strip())
                        if noise_value != self.last_noise_voltage:
                            self.noise_voltage = noise_value
                            self.last_noise_voltage = noise_value
                    elif line.startswith("freq_offset="):
                        freq_offset = float(line.split("=", 1)[1].strip())
                        if freq_offset != self.last_freq_offset_hz:
                            self.freq_offset_hz = freq_offset
                            self.last_freq_offset_hz = freq_offset
                            self.phase_inc = (2.0 * np.pi * self.freq_offset_hz) / self.sample_rate
        except Exception:
            pass

    def work(self, input_items, output_items):
        self._update_from_file()

        in0 = input_items[0]
        out = output_items[0]
        n = len(in0)

        if n == 0:
            return 0

        if self.phase_inc != 0.0:
            phases = self.phase + self.phase_inc * np.arange(n, dtype=np.float32)
            rot = np.exp(1j * phases).astype(np.complex64)
            sig = in0 * rot
            self.phase = float((phases[-1] + self.phase_inc) % (2.0 * np.pi))
        else:
            sig = in0

        sigma_snr = 0.0
        if self.snr_db < 80.0:
            sig_power = float(np.mean(np.abs(sig) ** 2)) if n > 0 else 0.0
            if sig_power > 0.0:
                snr_linear = 10.0 ** (self.snr_db / 10.0)
                if snr_linear > 0.0:
                    noise_power = sig_power / snr_linear
                    sigma_snr = float(np.sqrt(noise_power / 2.0))

        sigma_noise = max(0.0, float(self.noise_voltage)) / np.sqrt(2.0)
        sigma = float(np.sqrt((sigma_snr ** 2) + (sigma_noise ** 2)))

        if sigma <= 0.0:
            out[:] = sig
            return len(out)
        
        noise_real = np.random.normal(0.0, sigma, len(in0)).astype(np.float32)
        noise_imag = np.random.normal(0.0, sigma, len(in0)).astype(np.float32)

        out[:] = sig + noise_real + 1j * noise_imag
        return len(out)