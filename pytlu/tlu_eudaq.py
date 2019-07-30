#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

'''
    This script connects pytlu to the EUDAQ 1.x data acquisition system.
'''

import argparse
import os
import time
import sys
import re

import numpy as np
import tables as tb
from tqdm import tqdm
import yaml
import logging
from pytlu.tlu import Tlu

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.handlers[0].setFormatter(logging.Formatter("%(asctime)s [%(levelname)-3.3s] %(message)s"))


def configure_tlu(chip, config, output_ch):
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


class EudaqScan(Tlu):
    def set_callback(self, fun):
        '''
        Set function to be called for each raw data chunk of one trigger
        '''

        self.callback = fun
        self.last_trigger_number = -1
        self.event_counter = 0  # FIXME: Start at 0 or 1?

    def handle_data(self, data_tuple):
        '''
        Called on every readout (a few Hz)
        Sends data per event by checking for the trigger word that comes first.
        '''

        super(EudaqScan, self).handle_data(data_tuple)
        trigger_number = data_tuple[0]["trigger_id"]
        trigger_timestamp = data_tuple[0]["time_stamp"]
        skipped_triggers = data_tuple[4]
        n_triggers = trigger_number.shape[0]
        for i in range(n_triggers):
            # Split can return empty data, thus do not return send empty data
            # Otherwise fragile EUDAQ will fail. It is based on very simple event counting only
            if np.any(trigger_number):
                actual_trigger_number = trigger_number[i]
                trigger_data = (trigger_number[i], trigger_timestamp[i], skipped_triggers)
                # Check for jumps in trigger number
                if actual_trigger_number != self.last_trigger_number + 1:
                    logging.warning('Expected != Measured trigger number: %d != %d', self.last_trigger_number + 1, actual_trigger_number)
                self.last_trigger_number = actual_trigger_number
                self.callback(data=trigger_data, event_counter=self.event_counter)
                self.event_counter += 1


def replay_tlu_data(data_file, real_time=True):
    '''
    Replay data from file.

    Parameters
    ----------
    real_time: boolean
        Delays return if replay is too fast to keep
        replay speed at original data taking speed.
    '''

    with tb.open_file(data_file, mode="r") as in_file_h5:
        meta_data = in_file_h5.root.meta_data[:]
        raw_data = in_file_h5.root.raw_data
        n_readouts = meta_data.shape[0]

        last_readout_time = time.time()

        # Leftover data from last readout
#         last_readout_data = np.array([], dtype=np.uint32)
        last_trigger_number = -1

        for i in tqdm(range(n_readouts)):
            # Raw data indeces of readout
            i_start = meta_data['index_start'][i]
            i_stop = meta_data['index_stop'][i]

            t_start = meta_data[i]['timestamp_start']

            # Determine replay delays
            if i == 0:  # Initialize on first readout
                last_timestamp_start = t_start
            now = time.time()
            delay = now - last_readout_time
            additional_delay = t_start - last_timestamp_start - delay
            if real_time and additional_delay > 0:
                # Wait if send too fast, especially needed when readout was
                # stopped during data taking (e.g. for mask shifting)
                time.sleep(additional_delay)
            last_readout_time = time.time()
            last_timestamp_start = t_start

            actual_data = raw_data[i_start:i_stop]

            skipped_triggers = meta_data[i]['skipped_triggers']
            for dat in actual_data:
                    actual_trigger_number = dat['trigger_id']
                    trg_number, trg_timestamp = dat['trigger_id'], dat['time_stamp']
                    # Check for jumps in trigger number
                    if actual_trigger_number != last_trigger_number + 1:
                        logging.warning('Expected != Measured trigger number: %d != %d', last_trigger_number + 1, actual_trigger_number)
                    last_trigger_number = actual_trigger_number

                    yield trg_number, trg_timestamp, skipped_triggers


def main():
    tlu = None
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
    parser.add_argument('-oe', '--output_enable', nargs='+', type=str, choices=output_ch, default=[],
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

    # EUDAQ related
    parser.add_argument('address', metavar='address',
                        help='Destination address',
                        default='tcp://localhost:44000',
                        nargs='?')
    parser.add_argument('--path', type=str,
                        help='Absolute path of your eudaq installation')
    parser.add_argument('--replay', type=str,
                        help='Raw data file to replay for testing')
    parser.add_argument('--delay', type=float,
                        help='Additional delay when replaying data in seconds')

    args = parser.parse_args()

    # Create configuration dict,
    config = {"input_enable": args.input_enable, "output_enable": args.output_enable, "threshold": args.threshold,
              "n_bits_trig_id": args.n_bits_trig_id, "coincidence_window": args.coincidence_window, "test": args.test,
              "count": args.count, "timeout": args.timeout, "input_invert": args.input_invert,
              "output_folder": args.output_folder, "log_file": args.log_file, "data_file": args.data_file,
              "monitor_addr": args.monitor_addr, "scan_time": args.scan_time}

    # Import EUDAQ python wrapper with error handling
    try:
        from PyEUDAQWrapper import PyTluProducer
    except ImportError:
        if not args.path:
            logging.error('Cannot find PyEUDAQWrapper! Please specify the path of your EUDAQ installation!')
            return
        else:
            wrapper_path = os.path.join(args.path, 'python/')
            sys.path.append(os.path.join(args.path, 'python/'))
            try:
                from PyEUDAQWrapper import PyTluProducer
            except ImportError:
                logging.error('Cannot find PyEUDAQWrapper in %s', wrapper_path)
                return

    logging.info('Connect to %s', args.address)

    if args.replay:
        if os.path.isfile(args.replay):
            logging.info('Replay %s', args.replay)
        else:
            logging.error('Cannot open %s for replay!', args.replay)
    delay = args.delay if args.delay else 0.

    pp = PyTluProducer(args.address)

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
            tlu['tlu_master'].TRIGGER_ID, tlu['tlu_master'].SKIP_TRIG_COUNTER, tlu['tlu_master'].TIMEOUT_COUNTER,
            trg_rate_acc, trg_rate, tlu['tlu_master'].TX_STATE))

    def get_tx_state():
        if tlu is not None:
            tx_state = tlu['tlu_master'].TX_STATE
        else:
            return
        tx_state_str = []
        for i in range(6):
            if in_en & (0x20 >> i):
                tx_state_str.append(" %x" % ((tx_state >> (4 * i)) & 0xF))
            else:
                tx_state_str.append(" -")
        return ",".join(tx_state_str)

    def send_data_to_eudaq(data, event_counter):
        '''
        Send data to EUDAQ.

        Parameters:
        ------------
            data: tuple
                Tuple containing (trigger number, trigger timestamp, skipped triggers) of actual readout data.
            event_counter: int
                Event number (number of received triggers)
        '''
        trg_number, trg_timestamp, skipped_triggers = data
        # According to EUDAQ nomenclature
        particles = trg_number + skipped_triggers  # amount of possible triggers (accepted + skipped)
        scalers = get_tx_state()  # TLU status (TX state)
        pp.SendEventExtraInfo((event_counter, trg_timestamp, trg_number), particles, scalers)  # Send data to EUDAQ

    # Start state mashine, keep connection until termination of euRun
    while not pp.Error and not pp.Terminating:
        # Wait for configure cmd from RunControl
        while not pp.Configuring and not pp.Terminating:
            if pp.StartingRun:
                break
            time.sleep(0.1)

        # Check if configuration received
        if pp.Configuring:
            logging.info('Configuring...')
            if not args.replay:  # Only need configure step if not replaying data
                if tlu is None:  # Init TLU
                    tlu = EudaqScan(output_folder=args.output_folder, log_file=args.log_file, data_file=args.data_file, monitor_addr=args.monitor_addr)
                    tlu.init()
                    tlu.set_callback(send_data_to_eudaq)  # Set callback function in order to send data to EUDAQ

                # Read configuration file, map to pytlu format and update already existing config
                trigger_interval = float(pp.GetConfigParameter(item="TriggerInterval", default=False))  # (auto) trigger interval in units of 1 ms
                config["test"] = int(trigger_interval * 1e-3 / (25 * 1e-9))  # map to pytlu format (in units of 25 ns)

                and_mask = int(pp.GetConfigParameter(item="AndMask", default=0))  # bitmask for scintillator input channels
                and_mask_list = []
                if and_mask > 0:
                    for i in range(6):
                        if and_mask & (0b1 << i):
                            and_mask_list.append('CH%i' % i)
                    config['input_enable'] = and_mask_list
                else:
                    config['input_enable'] = []

                dut_mask = int(pp.GetConfigParameter(item="DutMask", default=0))  # bitmask for DUT channels
                dut_mask_list = []
                if dut_mask > 0:
                    for i in range(6):
                        if dut_mask & (0b1 << i):
                            dut_mask_list.append('CH%i' % i)
                    config['output_enable'] = dut_mask_list
                else:
                    config['output_enable'] = []

                # Configure TLU
                in_en, out_en = configure_tlu(tlu, config, output_ch)
            pp.Configuring = True

        # Check for start of run cmd from RunControl
        while not pp.StartingRun and not pp.Terminating:
            if pp.Configuring:
                break
            time.sleep(0.1)

        # Check if we are starting:
        if pp.StartingRun:
            logging.info('Starting run...')

            start_time = 0
            trigger_id_start = 0
            skipped_triggers_start = 0

            if not args.replay:
                # Start pytlu
                pp.StartingRun = True  # set status and send BORE
                with tlu.readout():
                    if config["test"] > 0:
                        logging.info("Starting internal trigger generation...")
                        # Start test pulser
                        # FIXME: This is bad, but pulser cannot simply be stopped w/o reset?
                        tlu['test_pulser'].DELAY = config["test"]
                        tlu['test_pulser'].WIDTH = 1
                        tlu['test_pulser'].REPEAT = config["count"]
                        tlu['test_pulser'].START
                    else:
                        logging.info("Triggering on scintillator inputs: {0}".format(args.input_enable))
                        # Enable inputs
                        tlu['tlu_master'].EN_INPUT = in_en
                    stop_run = False
                    while not stop_run:
                        if pp.Error or pp.Terminating:
                            if pp.Error:
                                logging.warning('Received error')
                                logging.info('Stopping run...')
                            # Disable output
                            if config["test"]:
                                # FIXME: pusler cannot simply be stopped. Has to be resetted such that configuration is lost.
                                tlu['test_pulser'].RESET
                            else:
                                tlu['tlu_master'].EN_INPUT = 0
                            # FIXME: using not thread safe variable
                            stop_run = True
                            break
                        if pp.StoppingRun:
                            logging.info('Stopping run...')
                            # Disable output
                            if config["test"]:
                                # FIXME: pusler cannot simply be stopped. Has to be resetted such that configuration is lost.
                                tlu['test_pulser'].RESET
                            else:
                                tlu['tlu_master'].EN_INPUT = 0
                            # FIXME: using not thread safe variable
                            stop_run = True
                            break
                        # Calculate parameter for logging output
                        actual_time = time.time()
                        actual_trigger_id = tlu['tlu_master'].TRIGGER_ID
                        actual_skipped_triggers = tlu['tlu_master'].SKIP_TRIG_COUNTER
                        trg_rate_acc = (actual_trigger_id - trigger_id_start) / (actual_time - start_time)
                        trg_rate = trg_rate_acc + (actual_skipped_triggers - skipped_triggers_start) / (actual_time - start_time)
                        print_log(trg_rate=trg_rate, trg_rate_acc=trg_rate_acc)
                        start_time = actual_time
                        trigger_id_start = actual_trigger_id
                        skipped_triggers_start = actual_skipped_triggers
                        time.sleep(1)
            else:
                logging.info("Replaying data...")
                pp.StartingRun = True  # set status and send BORE
                for event_counter, data in enumerate(replay_tlu_data(data_file=args.replay)):
                    trg_number, trg_timestamp, skipped_triggers = data
                    # According to EUDAQ nomenclature
                    particles = trg_number + skipped_triggers  # amount of possible triggers (accepted + skipped)
                    scalers = get_tx_state()  # TLU status (TX state)
                    pp.SendEventExtraInfo((event_counter, trg_timestamp, trg_number), particles, scalers)  # Send data to EUDAQ
                    if pp.Error or pp.Terminating:
                        break
                    if pp.StoppingRun:
                        break
                    time.sleep(delay)

            # Abort conditions
            if pp.Error or pp.Terminating:
                pp.StoppingRun = False  # Set status and send EORE
            # Check if the run is stopping regularly
            if pp.StoppingRun:
                pp.StoppingRun = True  # Set status and send EORE

        # Back to check for configured + start run state
        time.sleep(0.1)

    logging.info('Closing TLU...')
    # close and disable inputs and outputs
    tlu['tlu_master'].EN_INPUT = 0
    tlu['tlu_master'].EN_OUTPUT = 0
    tlu['test_pulser'].RESET
    tlu.close()


if __name__ == "__main__":
    # When run in development environment, eudaq path can be added with:
    sys.path.append('/home/user/git/eudaq/python/')
    main()
