#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

import logging
import os
import sys
import time
import argparse
import signal
from contextlib import contextmanager

import yaml
import tables as tb
import numpy as np

from basil.dut import Dut

from pytlu.fifo_readout import FifoReadout
from pytlu.online_monitor import pytlu_sender

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.handlers[0].setFormatter(logging.Formatter("%(asctime)s [%(levelname)-3.3s] %(message)s"))

stop_run = False


def handle_sig(signum, frame):
    logging.info('Pressed Ctrl-C')
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    global stop_run
    stop_run = True


class Tlu(Dut):
    I2C_MUX = {'DISPLAY': 0, 'LEMO': 1, 'HDMI': 2, 'MB': 3}
    I2C_ADDR = {'LED': 0x40, 'TRIGGER_EN': 0x42, 'RESET_EN': 0x44, 'IPSEL': 0x46}
    PCA9555 = {'DIR': 6, 'OUT': 2}
    IP_SEL = {'RJ45': 0b11, 'LEMO': 0b10}

    def __init__(self, conf=None, output_folder=None, log_file=None, data_file=None, monitor_addr=None):
        if conf is None:
            conf = os.path.dirname(os.path.abspath(__file__)) + os.sep + "tlu.yaml"
        logging.info("Loading configuration file from %s" % conf)

        self.data_dtype = np.dtype([('le0', 'u1'), ('le1', 'u1'), ('le2', 'u1'),
                                    ('le3', 'u1'), ('time_stamp', 'u8'), ('trigger_id', 'u4')])
        self.meta_data_dtype = np.dtype([('index_start', 'u4'), ('index_stop', 'u4'), ('data_length', 'u4'),
                                         ('timestamp_start', 'f8'), ('timestamp_stop', 'f8'), ('error', 'u4'),
                                         ('skipped_triggers', 'u8')])

        self.run_name = time.strftime("%Y%m%d_%H%M%S_tlu")
        self.output_filename = self.run_name
        self._first_read = False

        if output_folder:
            self.output_folder = output_folder
        else:
            self.output_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output_data')
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)

        if log_file:
            self.log_file = os.path.join(self.output_folder, log_file + ".log")
        else:
            self.log_file = os.path.join(self.output_folder, self.output_filename + ".log")

        if data_file:
            self.data_file = os.path.join(self.output_folder, data_file + ".h5")
        else:
            self.data_file = os.path.join(self.output_folder, self.output_filename + ".h5")

        logging.info('Log file name: %s', self.log_file)
        logging.info('Data file name: %s', self.data_file)

        self.fh = logging.FileHandler(self.log_file)
        self.fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)-5.5s] %(message)s"))
        self.fh.setLevel(logging.DEBUG)
        self.logger = logging.getLogger()
        self.logger.addHandler(self.fh)
        logging.info('Initializing %s', self.__class__.__name__)

        # open socket for monitor
        if monitor_addr is None:
            self.socket = None
        else:
            try:
                self.socket = pytlu_sender.init(monitor_addr)
                self.logger.info('Initializing online_monitor: connected to %s' % monitor_addr)
            except Exception:
                self.logger.warning('Initializing online_monitor: failed to connect to %s' % monitor_addr)
                self.socket = None

        super(Tlu, self).__init__(conf)

    def init(self):
        super(Tlu, self).init()

        fw_version = self['intf'].read(0x2000, 1)[0]
        logging.info("TLU firmware version: %s" % (fw_version))
        if int(self.version) != fw_version:
            raise Exception("TLU firmware version does not match DUT configuration file (read: %s, require: %s)" % (fw_version, int(self.version)))

        # Who know why this is needed but other way first bytes are mising
        # every secount time?
        self['stream_fifo'].SET_COUNT = 8 * 512
        self['intf'].read(0x0001000000000000, 8 * 512)
        self['tlu_master'].get_configuration()

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
            how_much_read = (stream_fifo_size // 512 + 1) * 512
            self['stream_fifo'].SET_COUNT = how_much_read
            ret = self['intf'].read(0x0001000000000000, how_much_read)
            retint = np.frombuffer(ret, dtype=self.data_dtype)
            retint = retint[retint['time_stamp'] > 0]
            return retint
            # return ret
        else:
            return np.array([], dtype=self.data_dtype)
            # return np.empty([], dtype=np.uint8)

    @contextmanager
    def readout(self, *args, **kwargs):
        if not self._first_read:
            self.filter_data = tb.Filters(complib='blosc', complevel=5)
            self.filter_tables = tb.Filters(complib='zlib', complevel=5)
            self.h5_file = tb.open_file(self.data_file, mode='w', title='TLU')
            self.data_table = self.h5_file.create_table(self.h5_file.root, name='raw_data', description=self.data_dtype, title='data', filters=self.filter_data)
            self.meta_data_table = self.h5_file.create_table(self.h5_file.root, name='meta_data', description=self.meta_data_dtype, title='meta_data', filters=self.filter_tables)
            self.meta_data_table.attrs.kwargs = yaml.dump(kwargs)

            self.fifo_readout = FifoReadout(self)
            self.fifo_readout.print_readout_status()
            self._first_read = True

        self.fifo_readout.start(callback=self.handle_data,
                                errback=self.handle_err)
        try:
            yield
        finally:
            try:
                self.fifo_readout.stop()
            except Exception:
                self.fifo_readout.stop(timeout=0.0)
            self.fifo_readout.print_readout_status()
            self.meta_data_table.attrs.config = yaml.dump(self.get_configuration())

    def close(self):
        try:
            self.h5_file.close()
        except Exception:
            pass
        # close socket
        if self.socket is not None:
            try:
                pytlu_sender.close(self.socket)
            except Exception:
                pass
        super(Tlu, self).close()

    def handle_data(self, data_tuple):
        '''Handling of the data.
        '''

        total_words = self.data_table.nrows
        self.data_table.append(data_tuple[0])
        self.data_table.flush()

        len_raw_data = data_tuple[0].shape[0]
        self.meta_data_table.row['timestamp_start'] = data_tuple[1]
        self.meta_data_table.row['timestamp_stop'] = data_tuple[2]
        self.meta_data_table.row['error'] = data_tuple[3]
        self.meta_data_table.row['skipped_triggers'] = data_tuple[4]
        self.meta_data_table.row['data_length'] = len_raw_data
        self.meta_data_table.row['index_start'] = total_words
        total_words += len_raw_data
        self.meta_data_table.row['index_stop'] = total_words
        self.meta_data_table.row.append()
        self.meta_data_table.flush()

        # sending data to online monitor
        if self.socket is not None:
            try:
                pytlu_sender.send_data(self.socket, data_tuple, len_raw_data)
            except Exception:
                self.logger.warning('online_monitor.pytlu_sender.send_data failed %s' % str(sys.exc_info()))
                try:
                    pytlu_sender.close(self.socket)
                except Exception:
                    pass
                self.socket = None

    def handle_err(self, exc):
        self.logger.warning(exc[1].__class__.__name__ + ": " + str(exc[1]))

    def configure(self, chip, config, output_ch):
        ''' Configure TLU.
        '''
        ch_no = [int(x[-1]) for x in config['output_enable']]
        for i in range(4):
            if ch_no.count(i) > 1:
                raise argparse.ArgumentTypeError("Output channels. CHx and LEM0x are exclusive")

        for oe in config['output_enable']:
            if oe[0] == 'C':
                chip['I2C_LED_CNT'][oe] = 3
            else:  # LEMO
                chip['I2C_LEMO_LEDS']['BUSY' + oe[-1]] = 1
                chip['I2C_LEMO_LEDS']['TRIG' + oe[-1]] = 1
                chip['I2C_LEMO_LEDS']['RST' + oe[-1]] = 1

        for oe in config['output_enable']:
            no = oe[-1]
            if oe in output_ch[:4]:  # TODO: why is this needed
                chip['I2C_IP_SEL'][no] = chip.IP_SEL['RJ45'] if oe[0] == 'C' else chip.IP_SEL['LEMO']

        chip.write_i2c_config()

        chip['tlu_master'].MAX_DISTANCE = config['coincidence_window']
        chip['tlu_master'].THRESHOLD = config['threshold']
        chip['tlu_master'].TIMEOUT = config['timeout']
        chip['tlu_master'].N_BITS_TRIGGER_ID = config['n_bits_trig_id']

        in_en = 0
        for ie in config['input_enable']:
            in_en = in_en | (0x01 << int(ie[-1]))

        out_en = 0
        for oe in config['output_enable']:
            out_en = out_en | (0x01 << int(oe[-1]))
        chip['tlu_master'].EN_OUTPUT = out_en

        in_inv = 0
        for ie in config['input_invert']:
            in_inv = in_inv | (0x01 << int(ie[-1]))
        chip['tlu_master'].INVERT_INPUT = in_inv

        if config['test']:
            chip['test_pulser'].DELAY = config['test']
            chip['test_pulser'].WIDTH = 1
            chip['test_pulser'].REPEAT = config['count']

        return in_en, out_en


def main():
    input_ch = ['CH0', 'CH1', 'CH2', 'CH3']
    output_ch = ['CH0', 'CH1', 'CH2', 'CH3', 'CH4', 'CH5', 'LEMO0', 'LEMO1', 'LEMO2', 'LEMO3']

    def th_type(x):
        if int(x) > 31 or int(x) < 0:
            raise argparse.ArgumentTypeError("Threshold is 0 to 31")
        return int(x)

    parser = argparse.ArgumentParser(usage="pytlu -ie CH0 -oe CH0",
                                     description='TLU DAQ\n TX_STATE: 0= DISABLED 1=WAIT 2=TRIGGERED (wait for busy HIGH) 4=READ_TRIG (wait for busy LOW) LBS is CH0', formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('-ie', '--input_enable', nargs='+', type=str, choices=input_ch, default=[],
                        help='Enable input channels. Allowed values are ' + ', '.join(input_ch), metavar='CHx')
    parser.add_argument('-oe', '--output_enable', nargs='+', type=str, choices=output_ch, required=True,
                        help='Enable ouput channels. CHx and LEM0x are exclusive. Allowed values are ' + ', '.join(output_ch), metavar='CHx/LEMOx')
    parser.add_argument('-th', '--threshold', type=th_type, default=0,
                        help="Digital threshold for input (in units of 1.5625ns). Default=0", metavar='0...31')
    parser.add_argument('-b', '--n_bits_trig_id', type=th_type, default=16,
                        help="Number of bits for trigger ID. Should correspond to TLU_TRIGGER_MAX_CLOCK_CYCLES - 1 which is set for TLU module. Default=0", metavar='0...31')
    parser.add_argument('-ds', '--coincidence_window', type=th_type, default=31,
                        help="Maximum distance between inputs rise time (in units of 1.5625ns). Default=31, 0=disabled", metavar='0...31')
    parser.add_argument('-t', '--test', type=int,
                        help="Generate triggers with given distance (in units of 25 ns).", metavar='1...n')
    parser.add_argument('-c', '--count', type=int, default=0,
                        help="Number of generated triggers. 0=infinite (default) ", metavar='0...n')
    parser.add_argument('--timeout', type=int, default=0x0000,
                        help="Timeout to wait for DUT. Default=0, 0=disabled. If you need to be synchronous with multiple DUTs choose timeout = 0.", metavar='0...65535')
    parser.add_argument('-inv', '--input_invert', nargs='+', type=str, choices=input_ch, default=[],
                        help='Invert input and detect positive edges. Allowed values are ' + ', '.join(input_ch), metavar='CHx')
    parser.add_argument('-f', '--output_folder', type=str,
                        default=None, help='Output folder of data and log file.  Default: /pytlu/output_data')
    parser.add_argument('-l', '--log_file', type=str,
                        default=None, help='Name of log file')
    parser.add_argument('-d', '--data_file', type=str,
                        default=None, help='Name of data file')
    parser.add_argument('--monitor_addr', type=str, default=None,
                        help="Address for online monitor wait for DUT. Default=disabled, Example=tcp://127.0.0.1:5550")
    parser.add_argument('--scan_time', type=int, default=0,
                        help="Scan time in seconds. Default=disabled, disable=0")

    args = parser.parse_args()

    # Create configuration dict
    config = {"input_enable": args.input_enable, "output_enable": args.output_enable, "threshold": args.threshold,
              "n_bits_trig_id": args.n_bits_trig_id, "coincidence_window": args.coincidence_window, "test": args.test,
              "count": args.count, "timeout": args.timeout, "input_invert": args.input_invert,
              "output_folder": args.output_folder, "log_file": args.log_file, "data_file": args.data_file,
              "monitor_addr": args.monitor_addr, "scan_time": args.scan_time}

    chip = Tlu(output_folder=args.output_folder, log_file=args.log_file, data_file=args.data_file, monitor_addr=args.monitor_addr)
    chip.init()

    in_en, _ = chip.configure(chip, config, output_ch)

    def print_log(trg_rate=None, trg_rate_acc=None):
        '''
        Print logging message.

        Parameters:
        -----------
            trg_rate: float
                Trigger rate on scintillator inputs
            trg_rate_acc: float
                Real trigger rate (rate of triggers accepted by DUTs)
        '''

        if trg_rate is None:
            trg_rate = 0
        if trg_rate_acc is None:
            trg_rate_acc = 0
        logging.info("Trigger: %8d | Skip: %8d | Timeout: %2d | Rate: %.2f (%.2f) Hz | TxState: %06x" % (
            chip['tlu_master'].TRIGGER_ID, chip['tlu_master'].SKIP_TRIG_COUNTER, chip['tlu_master'].TIMEOUT_COUNTER,
            trg_rate_acc, trg_rate, chip['tlu_master'].TX_STATE))

    start_time = 0
    trigger_id_start = 0
    skipped_triggers_start = 0

    logging.info("Starting... Press Ctrl+C to exit...")
    signal.signal(signal.SIGINT, handle_sig)
    if args.test:
        logging.info("Starting internal trigger generation...")
        with chip.readout():
            chip['test_pulser'].START  # Start test pulser
            while not chip['test_pulser'].is_ready and not stop_run:
                # Calculate parameter for logging output
                actual_time = time.time()
                actual_trigger_id = chip['tlu_master'].TRIGGER_ID
                actual_skipped_triggers = chip['tlu_master'].SKIP_TRIG_COUNTER
                trg_rate_acc = (actual_trigger_id - trigger_id_start) / (actual_time - start_time)
                trg_rate = trg_rate_acc + (actual_skipped_triggers - skipped_triggers_start) / (actual_time - start_time)
                print_log(trg_rate=trg_rate, trg_rate_acc=trg_rate_acc)
                start_time = actual_time
                trigger_id_start = actual_trigger_id
                skipped_triggers_start = actual_skipped_triggers
                time.sleep(1)
            # reset pulser in case of abort
            chip['test_pulser'].RESET
    else:
        logging.info("Triggering on scintillator inputs: {0}".format(args.input_enable))
        with chip.readout():
            chip['tlu_master'].EN_INPUT = in_en  # Enable inputs
            while not stop_run:
                # Calculate parameter for logging output
                actual_time = time.time()
                actual_trigger_id = chip['tlu_master'].TRIGGER_ID
                actual_skipped_triggers = chip['tlu_master'].SKIP_TRIG_COUNTER
                trg_rate_acc = (actual_trigger_id - trigger_id_start) / (actual_time - start_time)
                trg_rate = trg_rate_acc + (actual_skipped_triggers - skipped_triggers_start) / (actual_time - start_time)
                print_log(trg_rate=trg_rate, trg_rate_acc=trg_rate_acc)
                start_time = actual_time
                trigger_id_start = actual_trigger_id
                skipped_triggers_start = actual_skipped_triggers
                time.sleep(1)

    # close and disable inputs and outputs
    chip['tlu_master'].EN_INPUT = 0
    chip['tlu_master'].EN_OUTPUT = 0
    chip.close()


if __name__ == '__main__':
    main()
