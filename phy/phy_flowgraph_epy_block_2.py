from gnuradio import gr
import pmt
import time

class blk(gr.basic_block):

    def __init__(self, control_file="phy_control.txt", refresh_s=0.5):
        gr.basic_block.__init__(
            self,
            name="noise_control",
            in_sig=None,
            out_sig=None
        )

        self.control_file = control_file
        self.refresh_s = refresh_s
        self.last_val = None

        self.message_port_register_out(pmt.intern("control"))

    def start(self):
        import threading

        def loop():
            while True:
                try:
                    with open(self.control_file) as f:
                        for line in f:
                            if line.startswith("noise="):
                                val = float(line.split("=")[1])

                                if val != self.last_val:
                                    self.last_val = val

                                    msg = pmt.cons(
                                        pmt.intern("noise_voltage"),
                                        pmt.from_double(val)
                                    )

                                    self.message_port_pub(
                                        pmt.intern("control"),
                                        msg
                                    )

                except:
                    pass

                time.sleep(self.refresh_s)

        threading.Thread(target=loop, daemon=True).start()
        return True