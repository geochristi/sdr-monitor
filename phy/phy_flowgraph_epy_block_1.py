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
    """Embedded Python Block example - a simple multiply const"""

    def __init__(self):  # only default arguments here
        """arguments to this function show up as parameters in GRC"""
        gr.sync_block.__init__(
            self,
            name='ber_comparator',   # will show up in GRC
            in_sig=[np.uint8, np.uint8],  # two input streams of bytes
            out_sig=None
        )
        # Two message inputs
        # self.message_port_register_in(pmt.intern('tx'))
        # self.message_port_register_in(pmt.intern('rx'))

        # self.set_msg_handler(pmt.intern('tx'), self.handle_tx)
        # self.set_msg_handler(pmt.intern('rx'), self.handle_rx)

        # Metrics output
        self.message_port_register_out(pmt.intern('metrics'))
        from collections import deque
        self.tx_fifo = deque()
        self.total_bits = 0
        self.error_bits = 0
        self.window_symbols = 0
        self.window_errors = 0
        self.WINDOW_SIZE = 10000


    def work(self, input_items, output_items):
        # This block is triggered by incoming messages, so we don't need to do anything here
        tx = input_items[0]
        rx = input_items[1]
        print("TX:", tx[:10])
        print("RX:", rx[:10])
        n = min(len(tx), len(rx))
        print("WORK called with", n, "items")

        errors = 0
        for i in range(n):
            # diff = tx[i] ^ rx[i]
            # errors += bin(diff).count("1")
            if tx[i] != rx[i]:
                errors += 1

        # self.total_bits += n * 2
        # self.total_bits += n 
        # self.error_bits += errors

        # ber = self.error_bits / self.total_bits if self.total_bits > 0 else 0.0
        # ber = errors / n if n > 0 else 0.0
        # print(f"Current BER: {ber:.6f} ({errors} errors out of {n} bits)")
        WINDOW_SIZE = 10000

        self.window_symbols += n
        self.window_errors += errors

        if self.window_symbols >= WINDOW_SIZE:
            ber = self.window_errors / self.window_symbols
            
            print("WINDOW BER:", ber)
            
            
                
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

            #RESET WINDOW
            self.window_symbols = 0
            self.window_errors = 0
            
        return n
    # def reset(self):
    #     self.total_bits = 0
    #     self.error_bits = 0
