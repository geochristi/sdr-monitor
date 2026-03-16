"""
Embedded Python Blocks:

Each time this file is saved, GRC will instantiate the first class it finds
to get ports and parameters of your block. The arguments to __init__  will
be the parameters. All of them are required to have default values!
"""

import json
from time import time

import numpy as np
from gnuradio import gr
import pmt

CONTROL_FILE = "/home/georgia/Desktop/SDR/control/phy_control.txt"

# BER comparator
class blk(gr.sync_block):  # other base classes are basic_block, decim_block, interp_block
    """Compare TX/RX byte streams and publish BER metrics."""

    def __init__(self):  # only default arguments here
        """arguments to this function show up as parameters in GRC"""
        gr.sync_block.__init__(
            self,
            name='ber_comparator',   # will show up in GRC
            in_sig=[np.uint8, np.uint8],  # two input streams of bytes
            out_sig=None
        )

        # Metrics output
        self.message_port_register_out(pmt.intern('metrics'))

        # Running totals (lifetime)
        self.total_bits = 0
        self.total_bit_errors = 0

        # Windowed BER state
        self.window_symbols = 0
        self.window_errors = 0
        self.WINDOW_SIZE = 1000

        # Controlled BER injection (0.0 .. 1.0 probability per compared symbol).
        self.ber_inject = 0.0
        self._last_poll = 0.0
        self.poll_interval = 0.2

    def _update_ber_inject_from_file(self):
        now = time()
        if now - self._last_poll < self.poll_interval:
            return

        self._last_poll = now
        try:
            with open(CONTROL_FILE, "r") as f:
                for line in f:
                    if line.startswith("ber_inject="):
                        value = float(line.split("=", 1)[1].strip())
                        self.ber_inject = max(0.0, min(value, 1.0))
                        break
        except Exception:
            pass


    def work(self, input_items, output_items):
        # Receive synchronized TX/RX streams.
        tx = input_items[0]
        rx = input_items[1]
        self._update_ber_inject_from_file()
        # print("TX:", tx[:10])
        # print("RX:", rx[:10])
        n = min(len(tx), len(rx))
        print("[BER] work() items:", n)
        if n == 0:
            return 0
        

        # Compare only the common region if buffers differ in length.
        tx_view = tx[:n]
        rx_view = rx[:n]

        if self.ber_inject > 0.0:
            rx_eval = rx_view.copy()
            inject_mask = np.random.random(n) < self.ber_inject
            rx_eval[inject_mask] = np.bitwise_xor(rx_eval[inject_mask], np.uint8(1))
        else:
            rx_eval = rx_view

        bit_errors = int(np.sum(tx_view != rx_eval))

        # Update running totals.
        self.total_bits += n
        self.total_bit_errors += bit_errors

        print(f"[BER] chunk errors: {bit_errors}/{n}")
        print(f"[BER] totals: bits={self.total_bits}, errors={self.total_bit_errors}")
        # with open("/tmp/phy_stats.txt", "w") as f:
        #     f.write(f"{self.total_bits},{self.total_bit_errors}\n")
            
        self.window_symbols += n
        self.window_errors += bit_errors

        # Publish BER once enough symbols have been collected.
        if self.window_symbols >= self.WINDOW_SIZE:
            ber = self.window_errors / self.window_symbols
            
            print("[BER] window ber:", ber)
                
            # Send metrics as a dictionary
            metrics = {
                'ber': ber,
                'bits': self.total_bits,
                'errors': self.total_bit_errors,
                'timestamp': time()
            }

            msg_json = json.dumps(metrics).encode('utf-8')
            u8vec = pmt.init_u8vector(len(msg_json), list(msg_json))
            self.message_port_pub(pmt.intern('metrics'), u8vec)

            # Reset window counters after publishing.
            self.window_symbols = 0
            self.window_errors = 0
            
        return n

