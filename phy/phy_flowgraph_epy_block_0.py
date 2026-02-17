"""
Embedded Python Blocks:

Each time this file is saved, GRC will instantiate the first class it finds
to get ports and parameters of your block. The arguments to __init__  will
be the parameters. All of them are required to have default values!
"""

import numpy as np
from gnuradio import gr
import pmt

class blk(gr.sync_block):  # other base classes are basic_block, decim_block, interp_block
    """Packet Generator Block - generates PDUs with random bytes"""

    def __init__(self, example_param=1.0):  # only default arguments here
        """arguments to this function show up as parameters in GRC"""
        gr.sync_block.__init__(
            self,
            name='packet generator',   # will show up in GRC
            in_sig=None,
            out_sig=None
        )
        self.message_port_register_in(pmt.intern('trigger'))
        self.set_msg_handler(pmt.intern('trigger'), self.handle_msg)

        self.message_port_register_out(pmt.intern('out'))
       
        self.packet_id = 0

    def handle_msg(self, msg):
        length = 256

        data = np.random.randint(0, 256, length, dtype=np.uint8)

        # packet id on the first byte
        data[0] = self.packet_id % 256
        self.packet_id += 1

        pdu = pmt.cons(pmt.PMT_NIL, pmt.init_u8vector(len(data), data.tolist()))

        self.message_port_pub(pmt.intern('out'), pdu)