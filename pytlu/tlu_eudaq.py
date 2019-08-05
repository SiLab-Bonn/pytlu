#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

'''
    This script connects pytlu to the EUDAQ 1.x data acquisition system.
'''

import os
import time
import sys

import numpy as np
import tables as tb
from tqdm import tqdm
import yaml
import logging
from pytlu.tlu import Tlu
from pytlu import tlu

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.handlers[0].setFormatter(logging.Formatter("%(asctime)s [%(levelname)-3.3s] %(message)s"))


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
        skipped_triggers = data_tuple[4]
        raw_data = data_tuple[0]
        n_triggers = raw_data.shape[0]
        for i in range(n_triggers):
            # Split can return empty data, thus do not return send empty data
            # Otherwise fragile EUDAQ will fail. It is based on very simple event counting only
            if np.any(raw_data['trigger_id']):
                actual_trigger_number = raw_data[i]['trigger_id']
                data = raw_data[i]
                # Check for jumps in trigger number
                if actual_trigger_number != self.last_trigger_number + 1:
                    logging.warning('Expected != Measured trigger number: %d != %d', self.last_trigger_number + 1, actual_trigger_number)
                self.last_trigger_number = actual_trigger_number
                self.callback(data=data, skipped_triggers=skipped_triggers, event_counter=self.event_counter)
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
    chip = None

    args = tlu.parse_arguments(eudaq=True)

    # Create configuration dict
    config = tlu.create_configuration(args)

    # Import EUDAQ python wrapper with error handling
    try:
        from PyEUDAQWrapper import PyTluProducer
    except ImportError:
        if not config['path']:
            logging.error('Cannot find PyEUDAQWrapper! Please specify the path of your EUDAQ installation!')
            return
        else:
            wrapper_path = os.path.join(config['path'], 'python/')
            sys.path.append(os.path.join(config['path'], 'python/'))
            try:
                from PyEUDAQWrapper import PyTluProducer
            except ImportError:
                logging.error('Cannot find PyEUDAQWrapper in %s', wrapper_path)
                return

    logging.info('Connect to %s', config['address'])

    if config['replay']:
        if os.path.isfile(config['replay']):
            logging.info('Replay %s', config['replay'])
        else:
            logging.error('Cannot open %s for replay!', config['replay'])
    delay = config['delay'] if config['delay'] else 0.

    pp = PyTluProducer(config['address'])

    def get_dut_status():
        ''' Get DUT status and convert into EUDAQ format.
            For details see EUDAQ user manual.
        '''
        if chip is not None:
            tx_state = chip['tlu_master'].TX_STATE
        else:
            return
        tx_state_str = []
        for i in range(6):
            if (out_en >> i) & 0x01:
                dut_state = (tx_state >> (4 * i)) & 0xF
                if dut_state in [1, 2]:  # convert to ugly EUDAQ format
                    dut_state -= 1
                tx_state_str.append("-%i," % dut_state)
            else:
                tx_state_str.append("--,")
        tlu_status = ''.join(tx_state_str)
        tlu_status = tlu_status + ' (-,-)'  # no veto and DMA state availabe
        return tlu_status

    def send_data_to_eudaq(data, skipped_triggers, event_counter):
        '''
        Send data to EUDAQ.

        Parameters:
        ------------
            data: tuple
                Tuple containing (trigger number, trigger timestamp, skipped triggers) of actual readout data.
            event_counter: int
                Event number (number of received triggers)
        '''
        trg_number, trg_timestamp = data['trigger_id'], data['time_stamp']
        # According to EUDAQ nomenclature
        particles = trg_number + skipped_triggers  # amount of possible triggers (accepted + skipped)
        status = get_dut_status()  # TLU status according to EUDAQ format
        scalers = '-, -, -, -'  # input triggers on each scinitllator input (TODO: not yet implemented)
        pp.SendEventExtraInfo((event_counter, trg_timestamp, trg_number), particles, status, scalers)  # Send data to EUDAQ

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
            if not config['replay']:  # Only need configure step if not replaying data
                if chip is None:  # Init TLU
                    chip = EudaqScan(output_folder=config['output_folder'], log_file=config['log_file'], data_file=config['data_file'], monitor_addr=config['monitor_addr'])
                    chip.init()
                    chip.set_callback(send_data_to_eudaq)  # Set callback function in order to send data to EUDAQ

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
                in_en, out_en = chip.configure(config)
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

            if not config['replay']:
                # Start pytlu
                pp.StartingRun = True  # set status and send BORE
                with chip.readout():
                    if config["test"] > 0:
                        logging.info("Starting internal trigger generation...")
                        # Start test pulser
                        # FIXME: This is bad since belongs to configure step, but pulser cannot simply be stopped w/o reset?
                        chip['test_pulser'].DELAY = config["test"]
                        chip['test_pulser'].WIDTH = 1
                        chip['test_pulser'].REPEAT = config["count"]
                        chip['test_pulser'].START
                    else:
                        logging.info("Triggering on scintillator inputs: {0}".format(config['input_enable']))
                        # Enable inputs
                        chip['tlu_master'].EN_INPUT = in_en
                    stop_run = False
                    while not stop_run:
                        if pp.Error or pp.Terminating:
                            if pp.Error:
                                logging.warning('Received error')
                                logging.info('Stopping run...')
                            # Disable output
                            if config["test"]:
                                # FIXME: pusler cannot simply be stopped. Has to be resetted such that configuration is lost.
                                chip['test_pulser'].RESET
                            else:
                                chip['tlu_master'].EN_INPUT = 0
                            # FIXME: using not thread safe variable
                            stop_run = True
                            break
                        if pp.StoppingRun:
                            logging.info('Stopping run...')
                            # Disable output
                            if config["test"]:
                                # FIXME: pulser cannot simply be stopped. Has to be resetted such that configuration is lost.
                                chip['test_pulser'].RESET
                            else:
                                chip['tlu_master'].EN_INPUT = 0
                            # FIXME: using not thread safe variable
                            stop_run = True
                            break
                        # Calculate parameter for logging output
                        actual_time = time.time()
                        actual_trigger_id = chip['tlu_master'].TRIGGER_ID
                        actual_skipped_triggers = chip['tlu_master'].SKIP_TRIG_COUNTER
                        trg_rate_acc = (actual_trigger_id - trigger_id_start) / (actual_time - start_time)
                        trg_rate = trg_rate_acc + (actual_skipped_triggers - skipped_triggers_start) / (actual_time - start_time)
                        timeout_counter = chip['tlu_master'].TIMEOUT_COUNTER
                        tx_state = chip['tlu_master'].TX_STATE
                        start_time = actual_time
                        trigger_id_start = actual_trigger_id
                        skipped_triggers_start = actual_skipped_triggers
                        tlu.print_log(trg_rate, trg_rate_acc, actual_trigger_id, actual_skipped_triggers, timeout_counter, tx_state)
                        time.sleep(1)
            else:
                logging.info("Replaying data...")
                pp.StartingRun = True  # set status and send BORE
                for event_counter, data in enumerate(replay_tlu_data(data_file=config['replay'])):
                    trg_number, trg_timestamp, skipped_triggers = data
                    # According to EUDAQ nomenclature
                    particles = trg_number + skipped_triggers  # amount of possible triggers (accepted + skipped)
                    status = get_dut_status()  # TLU status (TX state)
                    pp.SendEventExtraInfo((event_counter, trg_timestamp, trg_number), particles, status)  # Send data to EUDAQ
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

    # Proper close and disable inputs and outputs in case of termination or error
    logging.info('Closing TLU...')
    chip['tlu_master'].EN_INPUT = 0
    chip['tlu_master'].EN_OUTPUT = 0
    chip['test_pulser'].RESET
    chip.close()


if __name__ == "__main__":
    # When run in development environment, eudaq path can be added with:
    sys.path.append('/home/user/git/eudaq/python/')
    main()
