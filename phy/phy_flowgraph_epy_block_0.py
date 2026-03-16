"""
Embedded Python Blocks:

Each time this file is saved, GRC will instantiate the first class it finds
to get ports and parameters of your block. The arguments to __init__  will
be the parameters. All of them are required to have default values!
"""

import numpy as np
from gnuradio import gr
import pmt
import json
from time import time, sleep
import threading

CONTROL_FILE = "/home/georgia/Desktop/SDR/control/phy_control.txt"

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

        self.message_port_register_out(pmt.intern('out')) # packets
        self.message_port_register_out(pmt.intern('metrics')) # telemetry
       
        self.packet_id = 0
        self.running = True
        self.sender_thread = threading.Thread(target=self.run_sender, daemon=True)
        self.sender_thread.start()

    def read_packet_rate(self):
        try:
            with open(CONTROL_FILE, "r") as f:
                for line in f:
                    if line.startswith("rate="):
                        return max(0, int(line.strip().split("=", 1)[1]))
        except Exception:
            pass
        return 0

    def send_packet(self):
        length = 256

        data = np.random.randint(0, 256, length, dtype=np.uint8)

        # packet id on the first byte
        data[0] = self.packet_id % 256
        self.packet_id += 1

        pdu = pmt.cons(pmt.PMT_NIL, pmt.init_u8vector(len(data), data.tolist()))

        # publish pakcet 
        self.message_port_pub(pmt.intern('out'), pdu)

        #publish telemetry
        # self.publish_metrics()

    def run_sender(self):
        while self.running:
            rate = self.read_packet_rate()
            if rate > 0:
                self.send_packet()
                sleep(1.0 / rate)
            else:
                sleep(0.2)

    def handle_msg(self, msg):
        self.send_packet()

    def stop(self):
        self.running = False
        return True

    def publish_metrics(self):
        metrics = {
            'snr': 12.5,
            'ber': 0.00003,
            'rssi': -42.0,
            # 'packet_id': self.packet_id,
            # 'noise_voltage': noise_voltage,
            'timestamp': time()
        }
        print("SENT:", metrics)
        msg = json.dumps(metrics).encode('utf-8')

        # send directly as u8vector (no PDU wrapper )
        u8vec = pmt.init_u8vector(len(msg), list(msg))
        self.message_port_pub(pmt.intern('metrics'), u8vec)
        # msg_list = list(msg) # convert bytes to list of integers
        # pdu = pmt.cons(pmt.PMT_NIL, pmt.init_u8vector(len(msg_list), msg_list))
        # self.message_port_pub(pmt.intern('metrics'), pdu)