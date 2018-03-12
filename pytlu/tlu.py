#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

import yaml
import basil
from basil.dut import Dut
import logging
import os
import time
import argparse
import signal
import tables as tb
import numpy as np

from fifo_readout import FifoReadout
from contextlib import contextmanager

signal.signal(signal.SIGINT, signal.default_int_handler)
logging.getLogger().setLevel(logging.DEBUG)


class Tlu(Dut):

    VERSION = 4
    I2C_MUX = {'DISPLAY': 0, 'LEMO': 1, 'HDMI': 2, 'MB': 3}
    I2C_ADDR = {'LED': 0x40, 'TRIGGER_EN': 0x42, 'RESET_EN': 0x44, 'IPSEL': 0x46}
    PCA9555 = {'DIR': 6, 'OUT': 2}
    IP_SEL = {'RJ45': 0b11, 'LEMO': 0b10}

    def __init__(self, conf=None, log_file=None, data_file=None, monitor_addr=None):

        cnfg = conf
        logging.info("Loading configuration file from %s" % conf)
        if conf is None:
            conf = os.path.dirname(os.path.abspath(__file__)) + os.sep + "tlu.yaml"

        self.data_dtype = np.dtype([('le0', 'u1'), ('le1', 'u1'), ('le2', 'u1'),('le3', 'u1'), 
        #self.data_dtype = np.dtype([('le0', 'u2'), ('le2', 'u2'),
                                    ('time_stamp', 'u8'), ('trigger_id', 'u4')])
        self.meta_data_dtype = np.dtype([('index_start', 'u4'), ('index_stop', 'u4'), ('data_length', 'u4'),
                                         ('timestamp_start', 'f8'), ('timestamp_stop', 'f8'), ('error', 'u4')])

        self.run_name = time.strftime("tlu_%Y%m%d_%H%M%S")
        self.output_filename = self.run_name
        self._first_read = False

        self.log_file = self.output_filename + '.log'
        if log_file:
            self.log_file = log_file

        self.fh = logging.FileHandler(self.log_file)
        self.fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)-5.5s] %(message)s"))
        self.fh.setLevel(logging.DEBUG)
        self.logger = logging.getLogger()
        self.logger.addHandler(self.fh)
        logging.info('Initializing %s', self.__class__.__name__)

        self.data_file = self.output_filename + '.h5'
        if data_file:
            self.data_file = data_file

        logging.info('Data file name: %s', self.data_file)

        ### open socket for monitor
        if (monitor_addr==None): 
            self.socket=None
        else:
            import pytlu.online_monitor.sender as sender
            try:
                self.socket = sender.init(monitor_addr)
                self.logger.info('Inintialiying online_monitor: connected=%s'%monitor_addr)
            except:
                self.logger.warn('Inintialiying online_monitor: failed addr=%s'%monitor_addr)
                self.socket=None

        super(Tlu, self).__init__(conf)

    def init(self):
        super(Tlu, self).init()

        fw_version = self['intf'].read(0x2000, 1)[0]
        logging.info("TLU firmware version: %s" % (fw_version))
        if fw_version != self.VERSION:
            raise Exception("TLU firmware version does not satisfy version requirements (read: %s, require: %s)" % (fw_version, self.VERSION))

        # Who know why this is needed but other way first bytes are mising
        # every secount time?
        self['stream_fifo'].SET_COUNT = 8 * 512
        self['intf'].read(0x0001000000000000, 8 * 512)

        self.write_i2c_config()

    def write_i2c_config(self):
        self.write_rj45_leds()
        self.write_lemo_leds()
        self.write_trigger_en()
        self.write_reset_en()
        self.write_ip_sel()

    def write_rj45_leds(self):
        self['I2C_MUX']['SEL'] = self.I2C_MUX['MB']
        self['I2C_MUX'].write()

        self['i2c'].write(self.I2C_ADDR['LED'], [self.PCA9555['DIR'], 0x00, 0x00])

        val = self['I2C_LED_CNT'].tobytes().tolist()
        self['i2c'].write(self.I2C_ADDR['LED'], [self.PCA9555['OUT'], ~val[0] & 0xff, ~val[1] & 0xff])

    def write_lemo_leds(self):
        self['I2C_MUX']['SEL'] = self.I2C_MUX['LEMO']
        self['I2C_MUX'].write()

        self['i2c'].write(self.I2C_ADDR['LED'], [self.PCA9555['DIR'], 0x00, 0x00])

        val = self['I2C_LEMO_LEDS'].tobytes().tolist()
        self['i2c'].write(self.I2C_ADDR['LED'], [self.PCA9555['OUT'], ~val[0] & 0xff, val[1] & 0xff])

    def write_trigger_en(self):
        self['I2C_MUX']['SEL'] = self.I2C_MUX['MB']
        self['I2C_MUX'].write()

        self['i2c'].write(self.I2C_ADDR['TRIGGER_EN'], [self.PCA9555['DIR'], 0x00, 0x00])
        val = self['I2C_TRIGGER_EN'].tobytes().tolist()
        self['i2c'].write(self.I2C_ADDR['TRIGGER_EN'], [self.PCA9555['OUT'], val[0] & 0xff, val[1] & 0xff])

    def write_reset_en(self):
        self['I2C_MUX']['SEL'] = self.I2C_MUX['MB']
        self['I2C_MUX'].write()

        self['i2c'].write(self.I2C_ADDR['RESET_EN'], [self.PCA9555['DIR'], 0x00, 0x00])
        val = self['I2C_RESET_EN'].tobytes().tolist()
        self['i2c'].write(self.I2C_ADDR['RESET_EN'], [self.PCA9555['OUT'], val[0] & 0xff, val[1] & 0xff])

    def write_ip_sel(self):
        self['I2C_MUX']['SEL'] = self.I2C_MUX['MB']
        self['I2C_MUX'].write()

        self['i2c'].write(self.I2C_ADDR['IPSEL'], [self.PCA9555['DIR'], 0x00, 0x00])
        val = self['I2C_IP_SEL'].tobytes().tolist()
        self['i2c'].write(self.I2C_ADDR['IPSEL'], [self.PCA9555['OUT'], val[0] & 0xff, val[1] & 0xff])

    def get_fifo_data(self):
        stream_fifo_size = self['stream_fifo'].SIZE
        if stream_fifo_size >= 16:
            how_much_read = (stream_fifo_size / 512 + 1) * 512
            self['stream_fifo'].SET_COUNT = how_much_read
            ret = self['intf'].read(0x0001000000000000, how_much_read)
        #if len(ret) >= 16:
            retint = np.frombuffer(ret, dtype=self.data_dtype)
            #retint = np.frombuffer(self.ret[:(len(self.ret)//16)*16], dtype=self.data_dtype)
            #print len(retint),
            retint = retint[retint['time_stamp'] > 0]
            #print len(retint),
            if len(ret)>=16:
            #    print type(ret)
                for i in range(16):
                    print hex(ret[i]),
                print len(retint),len(ret)//16, retint[0]
            #self.ret=self.ret[(len(self.ret)//16)*16:]
            #print len(self.ret)
            #    for i in range(8):
            #        print i,retint[i]
            return retint
        else:
            return np.array([], dtype=self.data_dtype)

    @contextmanager
    def readout(self, *args, **kwargs):
        if not self._first_read:
            time.sleep(0.1)

            self.filter_data = tb.Filters(complib='blosc', complevel=5)
            self.filter_tables = tb.Filters(complib='zlib', complevel=5)
            self.h5_file = tb.open_file(self.data_file, mode='w', title='TLU')
            self.data_table = self.h5_file.create_table(self.h5_file.root, name='raw_data', description=self.data_dtype, title='data', filters=self.filter_data)
            self.meta_data_table = self.h5_file.create_table(self.h5_file.root, name='meta_data', description=self.meta_data_dtype, title='meta_data', filters=self.filter_tables)

            self.fifo_readout = FifoReadout(self)
            self.fifo_readout.print_readout_status()
            self._first_read = True

        self.fifo_readout.start(
            callback=self.handle_data, errback=self.handle_err)
        yield
        self.fifo_readout.stop()
        self.fifo_readout.print_readout_status()

    def close(self):
        ### close socket
        if self.socket!=None:
           try:
               sender.close(self.socket)
           except:
               pass

    def handle_data(self, data_tuple):
        '''Handling of the data.
        '''

        total_words = self.data_table.nrows

        #print data_tuple[0]

        self.data_table.append(data_tuple[0])
        self.data_table.flush()

        len_raw_data = data_tuple[0].shape[0]
        self.meta_data_table.row['timestamp_start'] = data_tuple[1]
        self.meta_data_table.row['timestamp_stop'] = data_tuple[2]
        self.meta_data_table.row['error'] = data_tuple[3]
        self.meta_data_table.row['data_length'] = len_raw_data
        self.meta_data_table.row['index_start'] = total_words
        total_words += len_raw_data
        self.meta_data_table.row['index_stop'] = total_words
        self.meta_data_table.row.append()
        self.meta_data_table.flush()
        

        ##### sending data to online monitor
        if self.socket!=None:
            try:
                sender.send_data(self.socket,data_tuple)
            except:
                self.logger.warn('ScanBase.hadle_data:sender.send_data failed')
                try:
                    sender.close(self.socket)
                except:
                    pass
                self.socket=None

    def handle_err(self, exc):
        pass


def main():

    input_ch = ['CH0', 'CH1', 'CH2', 'CH3']
    output_ch = ['CH0', 'CH1', 'CH2', 'CH3', 'CH4', 'CH5', 'LEMO0', 'LEMO1', 'LEMO2', 'LEMO3']

    def th_type(x):
        if int(x) > 31 or int(x) < 0:
            raise argparse.ArgumentTypeError("Threshold is 0 to 31")
        return int(x)

    parser = argparse.ArgumentParser(
        description='TLU DAQ \n example: sitlu -ie CH0 -oe CH0', formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('-ie', '--input_enable', nargs='+', type=str, choices=input_ch, default=[],
                        help='Enable input channels. Allowed values are ' + ', '.join(input_ch), metavar='CHx')
    parser.add_argument('-oe', '--output_enable', nargs='+', type=str, choices=output_ch, required=True,
                        help='Enable ouput channels. CHx and LEM0x are exclusive. Allowed values are ' + ', '.join(output_ch), metavar='CHx/LEMOx')
    parser.add_argument('-th', '--threshold', type=th_type, default=0,
                        help="Digital threshold for input (in units of 1.5625ns). Default=0", metavar='0...31')
    parser.add_argument('-ds', '--distance', type=th_type, default=31,
                        help="Maximum distance between inputs rise time (in units of 1.5625ns). Default=31, 0=disabled", metavar='0...31')
    parser.add_argument('-t', '--test', type=int,
                        help="Generate triggers with given distance (in units of 25 ns).", metavar='1...n')
    parser.add_argument('-c', '--count', type=int, default=0,
                        help="Number of generated triggers. 0=infinite (default) ", metavar='0...n')
    parser.add_argument('--timeout', type=int, default=0xffff,
                        help="Timeout to wait for DUT. Default=65535, 0=disabled", metavar='0...65535')
    parser.add_argument('-inv', '--input_invert', nargs='+', type=str, choices=input_ch, default=[],
                        help='Invert input and detect positive edges. Allowed values are ' + ', '.join(input_ch), metavar='CHx')
    parser.add_argument('-l', '--log',  type=str,
                        default=None, help='Name of log file')
    parser.add_argument('-d', '--data',  type=str,
                        default=None, help='Name of data file')
    parser.add_argument('--monitor_addr', type=str, default=None,
                        help="Address for online monitor wait for DUT. Default=disabled, Example=tcp://127.0.0.1:5550")

    args = parser.parse_args()

    chip = Tlu(log_file=args.log, data_file=args.data,monitor_addr=args.monitor_addr)
    chip.init()

    ch_no = [int(x[-1]) for x in args.output_enable]
    for i in range(4):
        if ch_no.count(i) > 1:
            raise argparse.ArgumentTypeError(
                "Output channels. CHx and LEM0x are exclusive")

    for oe in args.output_enable:
        if oe[0] == 'C':
            chip['I2C_LED_CNT'][oe] = 3
        else:  # LEMO
            chip['I2C_LEMO_LEDS']['BUSY' + oe[-1]] = 1
            chip['I2C_LEMO_LEDS']['TRIG' + oe[-1]] = 1
            chip['I2C_LEMO_LEDS']['RST' + oe[-1]] = 1

    for oe in args.output_enable:
        no = oe[-1]
        if no < 4:
            chip['I2C_IP_SEL'][no] = chip.IP_SEL['RJ45'] if oe[0] == 'C' else chip.IP_SEL['LEMO']

    chip.write_i2c_config()

    chip['tlu_master'].MAX_DISTANCE = args.distance
    chip['tlu_master'].THRESHOLD = args.threshold
    chip['tlu_master'].TIMEOUT = args.timeout

    in_en = 0
    for ie in args.input_enable:
        in_en = in_en | (0x01 << int(ie[-1]))

    out_en = 0
    for oe in args.output_enable:
        out_en = out_en | (0x01 << int(oe[-1]))

    chip['tlu_master'].EN_OUTPUT = out_en

    in_inv = 0
    for ie in args.input_invert:
        in_inv = in_inv | (0x01 << int(ie[-1]))
    chip['tlu_master'].INVERT_INPUT = in_inv

    def print_log(freq=None):
        if freq is not None:
            logging.info("Time: %.2f TriggerId: %8d TimeStamp: %16d Skipped: %8d Timeout: %2d Av. Rate: %.2f Hz" % (time.time() - start_time,
                                                                                                                    chip['tlu_master'].TRIGGER_ID, chip['tlu_master'].TIME_STAMP, chip['tlu_master'].SKIP_TRIGGER_COUNT, chip['tlu_master'].TIMEOUT_COUNTER, freq))
        else:
            logging.info("Time: %.2f TriggerId: %8d TimeStamp: %16d Skipped: %2d Timeout: %2d" % (time.time() - start_time,
                                                                                                  chip['tlu_master'].TRIGGER_ID, chip['tlu_master'].TIME_STAMP, chip['tlu_master'].SKIP_TRIGGER_COUNT, chip['tlu_master'].TIMEOUT_COUNTER))


    if args.test:
        logging.info("Starting test...")
        with chip.readout():
            chip['test_pulser'].DELAY = args.test
            chip['test_pulser'].WIDTH = 1
            chip['test_pulser'].REPEAT = args.count
            chip['test_pulser'].START

            start_time = time.time()
            time_2 = 0
            trigger_id_2 = 0

            while(not chip['test_pulser'].is_ready):
                time_1 = time.time()
                trigger_id_1 = chip['tlu_master'].TRIGGER_ID
                freq = (trigger_id_1 - trigger_id_2) / (time_1 - time_2)
                print_log(freq=freq)
                time_2 = time.time()
                trigger_id_2 = chip['tlu_master'].TRIGGER_ID
                time.sleep(1)
            print_log()
        return

    logging.info("Starting ... Ctrl+C to exit")
    start_time = time.time()
    time_2 = 0
    trigger_id_2 = 0
    stop = False
    with chip.readout():
        chip['tlu_master'].EN_INPUT = in_en
        while not stop:
            try:
                time_1 = time.time()
                trigger_id_1 = chip['tlu_master'].TRIGGER_ID
                freq = (trigger_id_1 - trigger_id_2) / (time_1 - time_2)
                print_log(freq=freq)
                time_2 = time.time()
                trigger_id_2 = chip['tlu_master'].TRIGGER_ID
                time.sleep(1)
            except KeyboardInterrupt:
                chip['tlu_master'].EN_INPUT = 0
                chip['tlu_master'].EN_OUTPUT = 0
                stop = True
        print_log()
    chip.close()


if __name__ == '__main__':
    main()
