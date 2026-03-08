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
        self.WINDOW_SIZE = 10000


    def work(self, input_items, output_items):
        # Receive synchronized TX/RX streams.
        tx = input_items[0]
        rx = input_items[1]
        # print("TX:", tx[:10])
        # print("RX:", rx[:10])
        n = min(len(tx), len(rx))
        print("[BER] work() items:", n)
        if n == 0:
            return 0
        

        # Compare only the common region if buffers differ in length.
        tx_view = tx[:n]
        rx_view = rx[:n]
        bit_errors = int(np.sum(tx_view != rx_view))

        # Update running totals.
        self.total_bits += n
        self.total_bit_errors += bit_errors

        print(f"[BER] chunk errors: {bit_errors}/{n}")
        print(f"[BER] totals: bits={self.total_bits}, errors={self.total_bit_errors}")
        with open("/tmp/phy_stats.txt", "w") as f:
            f.write(f"{self.total_bits},{self.total_bit_errors}\n")
            
        self.window_symbols += n
        self.window_errors += bit_errors

        # Publish BER once enough symbols have been collected.
        if self.window_symbols >= self.WINDOW_SIZE:
            ber = self.window_errors / self.window_symbols
            
            print("[BER] window ber:", ber)
                
            # Send metrics as a dictionary
            metrics = {
                'ber': ber,
                # 'total_bits': self.total_bits,
                # 'error_bits': self.error_bits,
                'timestamp': time()
            }

            msg_json = json.dumps(metrics).encode('utf-8')
            u8vec = pmt.init_u8vector(len(msg_json), list(msg_json))
            self.message_port_pub(pmt.intern('metrics'), u8vec)

            # Reset window counters after publishing.
            self.window_symbols = 0
            self.window_errors = 0
            
        return n

