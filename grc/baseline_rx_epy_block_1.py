"""
Embedded Python Blocks:

Each time this file is saved, GRC will instantiate the first class it finds
to get ports and parameters of your block. The arguments to __init__  will
be the parameters. All of them are required to have default values!
"""

import numpy as np
from gnuradio import gr
import time


class blk(gr.sync_block):  # other base classes are basic_block, decim_block, interp_block

    def __init__(self, threshold=1e-4):  # only default arguments here
        """arguments to this function show up as parameters in GRC"""
        gr.sync_block.__init__(
            self,
            name='signal_status',   # will show up in GRC
            in_sig=[np.float32],
            out_sig=None
        )
        # if an attribute with the same name as a parameter is found,
        # a callback is registered (properties work, too).
        self.threshold = threshold
        self.time_last_print = time.time()
        self.last_state = None

    def work(self, input_items, output_items):
        power = input_items[0][-1]
        state = 'ACTIVE' if power >= self.threshold else 'INACTIVE'
        now = time.time()
        if state != self.last_state and (now - self.time_last_print) > 1.0:
            print(f"Signal is now {state} (Power: {power:.6f} dB)")
            self.last_state = state
            self.time_last_print = now
        return len(input_items[0])