#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Not titled yet
# GNU Radio version: 3.10.9.2

from PyQt5 import Qt
from gnuradio import qtgui
from gnuradio import blocks
import pmt
from gnuradio import digital
from gnuradio import gr
from gnuradio.filter import firdes
from gnuradio.fft import window
import sys
import signal
from PyQt5 import Qt
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio import gr, pdu
from gnuradio import zeromq
import math
import phy_flowgraph_epy_block_0 as epy_block_0  # embedded python block
import phy_flowgraph_epy_block_1 as epy_block_1  # embedded python block
import phy_flowgraph_epy_block_3 as epy_block_3  # embedded python block
import sip



class phy_flowgraph(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "Not titled yet", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("Not titled yet")
        qtgui.util.check_set_qss()
        try:
            self.setWindowIcon(Qt.QIcon.fromTheme('gnuradio-grc'))
        except BaseException as exc:
            print(f"Qt GUI: Could not set Icon: {str(exc)}", file=sys.stderr)
        self.top_scroll_layout = Qt.QVBoxLayout()
        self.setLayout(self.top_scroll_layout)
        self.top_scroll = Qt.QScrollArea()
        self.top_scroll.setFrameStyle(Qt.QFrame.NoFrame)
        self.top_scroll_layout.addWidget(self.top_scroll)
        self.top_scroll.setWidgetResizable(True)
        self.top_widget = Qt.QWidget()
        self.top_scroll.setWidget(self.top_widget)
        self.top_layout = Qt.QVBoxLayout(self.top_widget)
        self.top_grid_layout = Qt.QGridLayout()
        self.top_layout.addLayout(self.top_grid_layout)

        self.settings = Qt.QSettings("GNU Radio", "phy_flowgraph")

        try:
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)
        except BaseException as exc:
            print(f"Qt GUI: Could not restore geometry: {str(exc)}", file=sys.stderr)

        ##################################################
        # Variables
        ##################################################
        self.Modulation = Modulation = 16
        self.samp_rate = samp_rate = 100000
        self.mod_type = mod_type = "QAM"
        self.bits_per_symbol = bits_per_symbol = int(math.log2(Modulation))

        ##################################################
        # Blocks
        ##################################################

        self.zeromq_pub_msg_sink_0_0 = zeromq.pub_msg_sink('tcp://127.0.0.1:5556', 100, True)
        self.zeromq_pub_msg_sink_0 = zeromq.pub_msg_sink('tcp://127.0.0.1:5555', 100, True)
        self.qtgui_const_sink_x_0 = qtgui.const_sink_c(
            1024, #size
            "", #name
            1, #number of inputs
            None # parent
        )
        self.qtgui_const_sink_x_0.set_update_time(0.10)
        self.qtgui_const_sink_x_0.set_y_axis((-2), 2)
        self.qtgui_const_sink_x_0.set_x_axis((-2), 2)
        self.qtgui_const_sink_x_0.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, "")
        self.qtgui_const_sink_x_0.enable_autoscale(False)
        self.qtgui_const_sink_x_0.enable_grid(False)
        self.qtgui_const_sink_x_0.enable_axis_labels(True)


        labels = ['', '', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "green", "black", "cyan",
            "magenta", "yellow", "dark red", "dark green", "dark blue"]
        styles = [0, 0, 0, 0, 0,
            0, 0, 0, 0, 0]
        markers = [0, 0, 0, 0, 0,
            0, 0, 0, 0, 0]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_const_sink_x_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_const_sink_x_0.set_line_label(i, labels[i])
            self.qtgui_const_sink_x_0.set_line_width(i, widths[i])
            self.qtgui_const_sink_x_0.set_line_color(i, colors[i])
            self.qtgui_const_sink_x_0.set_line_style(i, styles[i])
            self.qtgui_const_sink_x_0.set_line_marker(i, markers[i])
            self.qtgui_const_sink_x_0.set_line_alpha(i, alphas[i])

        self._qtgui_const_sink_x_0_win = sip.wrapinstance(self.qtgui_const_sink_x_0.qwidget(), Qt.QWidget)
        self.top_layout.addWidget(self._qtgui_const_sink_x_0_win)
        self.pdu_pdu_to_tagged_stream_0 = pdu.pdu_to_tagged_stream(gr.types.byte_t, 'packet_len')
        self.epy_block_3 = epy_block_3.blk(noise_voltage=0.0, snr_db=30.0, poll_interval=0.2, sample_rate=samp_rate)
        self.epy_block_1 = epy_block_1.blk()
        self.epy_block_0 = epy_block_0.blk(example_param=1.0)
        self.digital_diff_encoder_bb_0 = digital.diff_encoder_bb(Modulation if mod_type == "PSK" else 1, digital.DIFF_DIFFERENTIAL)
        self.digital_diff_decoder_bb_0 = digital.diff_decoder_bb(Modulation if mod_type == "PSK" else 1, digital.DIFF_DIFFERENTIAL)
        self.digital_constellation_encoder_bc_0 = digital.constellation_encoder_bc(( digital.constellation_bpsk().base() if (mod_type == "PSK" and Modulation == 2) else digital.constellation_qpsk().base() if (mod_type == "PSK" and Modulation == 4) else digital.constellation_8psk().base() if (mod_type == "PSK" and Modulation == 8) else digital.qam_constellation(Modulation, False).base() ))
        self.digital_constellation_decoder_cb_0 = digital.constellation_decoder_cb(( digital.constellation_bpsk().base() if (mod_type == "PSK" and Modulation == 2) else digital.constellation_qpsk().base() if (mod_type == "PSK" and Modulation == 4) else digital.constellation_8psk().base() if (mod_type == "PSK" and Modulation == 8) else digital.qam_constellation(Modulation, False).base() ))
        self.blocks_throttle2_0 = blocks.throttle( gr.sizeof_gr_complex*1, samp_rate, True, 0 if "auto" == "auto" else max( int(float(0.1) * samp_rate) if "auto" == "time" else int(0.1), 1) )
        self.blocks_selector_1_0 = blocks.selector(gr.sizeof_char*1,0 if mod_type == "PSK" else 1,0)
        self.blocks_selector_1_0.set_enabled(True)
        self.blocks_selector_1 = blocks.selector(gr.sizeof_char*1,0 if mod_type == "PSK" else 1,0)
        self.blocks_selector_1.set_enabled(True)
        self.blocks_repack_bits_bb_0 = blocks.repack_bits_bb(8, bits_per_symbol, 'packet_len', True, gr.GR_LSB_FIRST)
        self.blocks_message_strobe_0 = blocks.message_strobe(pmt.intern("TEST"), 1000)


        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.blocks_message_strobe_0, 'strobe'), (self.epy_block_0, 'trigger'))
        self.msg_connect((self.epy_block_0, 'out'), (self.pdu_pdu_to_tagged_stream_0, 'pdus'))
        self.msg_connect((self.epy_block_0, 'out'), (self.zeromq_pub_msg_sink_0, 'in'))
        self.msg_connect((self.epy_block_1, 'metrics'), (self.zeromq_pub_msg_sink_0_0, 'in'))
        self.connect((self.blocks_repack_bits_bb_0, 0), (self.blocks_selector_1, 1))
        self.connect((self.blocks_repack_bits_bb_0, 0), (self.digital_diff_encoder_bb_0, 0))
        self.connect((self.blocks_repack_bits_bb_0, 0), (self.epy_block_1, 0))
        self.connect((self.blocks_selector_1, 0), (self.digital_constellation_encoder_bc_0, 0))
        self.connect((self.blocks_selector_1_0, 0), (self.epy_block_1, 1))
        self.connect((self.blocks_throttle2_0, 0), (self.epy_block_3, 0))
        self.connect((self.digital_constellation_decoder_cb_0, 0), (self.blocks_selector_1_0, 1))
        self.connect((self.digital_constellation_decoder_cb_0, 0), (self.digital_diff_decoder_bb_0, 0))
        self.connect((self.digital_constellation_encoder_bc_0, 0), (self.blocks_throttle2_0, 0))
        self.connect((self.digital_diff_decoder_bb_0, 0), (self.blocks_selector_1_0, 0))
        self.connect((self.digital_diff_encoder_bb_0, 0), (self.blocks_selector_1, 0))
        self.connect((self.epy_block_3, 0), (self.digital_constellation_decoder_cb_0, 0))
        self.connect((self.epy_block_3, 0), (self.qtgui_const_sink_x_0, 0))
        self.connect((self.pdu_pdu_to_tagged_stream_0, 0), (self.blocks_repack_bits_bb_0, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("GNU Radio", "phy_flowgraph")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_Modulation(self):
        return self.Modulation

    def set_Modulation(self, Modulation):
        self.Modulation = Modulation
        self.set_bits_per_symbol(int(math.log2(self.Modulation)))
        self.digital_constellation_decoder_cb_0.set_constellation(( digital.constellation_bpsk().base() if (self.mod_type == "PSK" and self.Modulation == 2) else digital.constellation_qpsk().base() if (self.mod_type == "PSK" and self.Modulation == 4) else digital.constellation_8psk().base() if (self.mod_type == "PSK" and self.Modulation == 8) else digital.qam_constellation(self.Modulation, False).base() ))
        self.digital_constellation_encoder_bc_0.set_constellation(( digital.constellation_bpsk().base() if (self.mod_type == "PSK" and self.Modulation == 2) else digital.constellation_qpsk().base() if (self.mod_type == "PSK" and self.Modulation == 4) else digital.constellation_8psk().base() if (self.mod_type == "PSK" and self.Modulation == 8) else digital.qam_constellation(self.Modulation, False).base() ))

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.blocks_throttle2_0.set_sample_rate(self.samp_rate)
        self.epy_block_3.sample_rate = self.samp_rate

    def get_mod_type(self):
        return self.mod_type

    def set_mod_type(self, mod_type):
        self.mod_type = mod_type
        self.blocks_selector_1.set_input_index(0 if self.mod_type == "PSK" else 1)
        self.blocks_selector_1_0.set_input_index(0 if self.mod_type == "PSK" else 1)
        self.digital_constellation_decoder_cb_0.set_constellation(( digital.constellation_bpsk().base() if (self.mod_type == "PSK" and self.Modulation == 2) else digital.constellation_qpsk().base() if (self.mod_type == "PSK" and self.Modulation == 4) else digital.constellation_8psk().base() if (self.mod_type == "PSK" and self.Modulation == 8) else digital.qam_constellation(self.Modulation, False).base() ))
        self.digital_constellation_encoder_bc_0.set_constellation(( digital.constellation_bpsk().base() if (self.mod_type == "PSK" and self.Modulation == 2) else digital.constellation_qpsk().base() if (self.mod_type == "PSK" and self.Modulation == 4) else digital.constellation_8psk().base() if (self.mod_type == "PSK" and self.Modulation == 8) else digital.qam_constellation(self.Modulation, False).base() ))

    def get_bits_per_symbol(self):
        return self.bits_per_symbol

    def set_bits_per_symbol(self, bits_per_symbol):
        self.bits_per_symbol = bits_per_symbol
        self.blocks_repack_bits_bb_0.set_k_and_l(8,self.bits_per_symbol)




def main(top_block_cls=phy_flowgraph, options=None):

    qapp = Qt.QApplication(sys.argv)

    tb = top_block_cls()

    tb.start()

    tb.show()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        Qt.QApplication.quit()

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    timer = Qt.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    qapp.exec_()

if __name__ == '__main__':
    main()
