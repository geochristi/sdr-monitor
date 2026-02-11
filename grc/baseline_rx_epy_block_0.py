"""
Embedded Python Blocks:

Each time this file is saved, GRC will instantiate the first class it finds
to get ports and parameters of your block. The arguments to __init__  will
be the parameters. All of them are required to have default values!
"""

import numpy as np
from gnuradio import gr
import socket
import time 

# this block prints the average power of the input signal every second. 
# The power is printed in decibels (dB).
class blk(gr.sync_block):  # other base classes are basic_block, decim_block, interp_block
    """Embedded Python Block example - a simple multiply const"""

    def __init__(self):  # only default arguments here
        """arguments to this function show up as parameters in GRC"""
        gr.sync_block.__init__(
            self,
            name='power_monitor',   
            in_sig=[np.float32],
            out_sig=None
        )
        # self.last_print = time.time()
        self.last_send = time.time()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def work(self, input_items, output_items):
        samples = input_items[0]

        now = time.time()
        
        if now - self.last_send > 1.0:
            # power = input_items[0][-1]
            avg_power = float(np.mean(samples))
            print(f"Average Power: {avg_power:.6f} dB")
            self.last_send = now

            # IPC επικοινωνία
            self.sock.sendto(str(avg_power).encode(), ("127.0.0.1", 9999))
        
        return len(samples)
