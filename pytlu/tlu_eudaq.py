#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

import logging

import time
import argparse
import signal
import sys
import numpy as np
import re
from pytlu.tlu import Tlu
# set path to PyEUDAQWrapper
sys.path.append('/home/luetticke/eudaq1/python/')
from PyEUDAQWrapper import PyTluProducer
default_address = 'localhost:44000'


root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.handlers[0].setFormatter(logging.Formatter("%(asctime)s [%(levelname)-3.3s] %(message)s"))

stop_run = False


def handle_sig(signum, frame):
    logging.info('Pressed Ctrl-C')
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    global stop_run
    stop_run = True




def run_producer(runcontrol,tlu_config):
    tluprod = PyTluProducer(runcontrol)
    tlu = None
    enable_mask=0
    event_count=0
    def print_log(freq=None, freq_all=None):
        global tlu
        if freq is None:
            freq = 0
        if freq_all is None:
            freq_all = 0
        logging.info("Trigger: %8d | Skip: %8d | Timeout: %2d | Rate: %.2f (%.2f) Hz | TxState: %06x" % (
            tlu['tlu_master'].TRIGGER_ID, tlu['tlu_master'].SKIP_TRIG_COUNTER, tlu['tlu_master'].TIMEOUT_COUNTER,
            freq, freq_all, tlu['tlu_master'].TX_STATE))
    def sendToEudaq(data):
        global event_count
        if data.shape[0] == 0:
            return
        for (evtNr, timestamp) in data[["trigger_id","time_stamp"]]:
            tluprod.SendEvent((evtNr, timestamp,event_count))
            event_count += 1


    running = False
    soon_stopping = False
    sleeptime=0.1
    printSlowdown_start = 10
    printSlowdown_late = 50
    global stop_run
    while not tluprod.Error and not tluprod.Terminating:
        time.sleep(0.001)
        # check if configuration received
        if tluprod.Configuring:
            assert running == False
            logging.info("Configuring...")
            #             for item in run_conf:
            #                 try:
            #                     run_conf[item] = pp.GetConfigParameter(item)
            #                 except Exception:
            #                     pass
            dutChannel=tluprod.GetConfigParameter("DUTs")
            scintilators=tluprod.GetConfigParameter("Scintilators")
            invertInputs = tluprod.GetConfigParameter("InvertedInputs")
            tlu_config["dut_channels"] = map(lambda x:x.strip().upper(), filter(None, re.split("\W+",dutChannel)))
            tlu_config["scintilators"] = map(lambda x: x.strip().upper(), filter(None, re.split("\W+",scintilators)))
            tlu_config["inverted_inputs"] = map(lambda x: x.strip().upper(), filter(None, re.split("\W+", invertInputs)))
            root_logger.info("DUTs %s"%str(dutChannel))
            root_logger.info("Scintilators %s"%str(scintilators))
            root_logger.info("InvertedInputs %s"%str(invertInputs))

            testpulse = int(tluprod.GetConfigParameter("Testpulse",0))
            if tlu:
                tlu.close()
            tlu, enable_mask = configureTLU(tlu_config,sendToEudaq)

            tluprod.Configuring = True

        # check if we are starting:
        if tluprod.StartingRun:
            assert running == False
            root_logger.info("Waiting for other DUTs")
            time.sleep(10)
            tluprod.StartingRun=True #Sends BORE
            if testpulse>0:
                tlu['test_pulser'].DELAY = testpulse
                tlu['test_pulser'].WIDTH = 1
                tlu['test_pulser'].REPEAT = 0
            tlu['tlu_master'].TRIGGER_COUNTER = 0
            tlu['tlu_master'].TRIGGER_ID = 0
            tlu['tlu_master'].SKIP_TRIG_COUNTER = 0
            running=True
            start_time = time.time()
            time_2 = 0
            trigger_id_2 = 0
            skip2 = 0
            slowdown=printSlowdown_start
            printcnt=0


        if running:
            assert soon_stopping == False
            root_logger.info("Entered Running!")
            with tlu.readout():
                if testpulse > 0:
                    tlu['test_pulser'].START
                else:
                    tlu['tlu_master'].EN_INPUT = enable_mask
                while not stop_run:
                    if printcnt%slowdown==0:
                        time_1 = time.time()
                        trigger_id_1 = tlu['tlu_master'].TRIGGER_ID
                        skip1 = tlu['tlu_master'].SKIP_TRIG_COUNTER
                        freq = (trigger_id_1 - trigger_id_2) / (time_1 - time_2)
                        freq_all = freq + np.uint32(skip1 - skip2) / (time_1 - time_2)
                        print_log(freq=freq, freq_all=freq_all)
                        time_2 = time_1
                        trigger_id_2 = trigger_id_1
                        skip2 = skip1
                        if time_1-start_time > 30:
                            slowdown=printSlowdown_late
                    printcnt+=1
                    time.sleep(sleeptime)
                    if soon_stopping:
                        time.sleep(sleeptime)
                        stop_run=True
                        soon_stopping=False

                    if tluprod.StoppingRun:
                        root_logger.info("Stop requested!")
                        soon_stopping = True
                        printcnt = 0
                        if testpulse > 0:
                            tlu['test_pulser'].RESET
                        else:
                            tlu['tlu_master'].EN_INPUT = 0

            root_logger.info("TLU stopped!")
            running = False
            tluprod.StoppingRun = True  # set status and send EORE
    if tlu:
        tlu.close()

def configureTLU(tlu_config,callback):
    # Allowed
    input_ch = ['CH0', 'CH1', 'CH2', 'CH3']
    output_ch = ['CH0', 'CH1', 'CH2', 'CH3', 'CH4', 'CH5', 'LEMO0', 'LEMO1', 'LEMO2', 'LEMO3']


    for dut in tlu_config["dut_channels"]:
        assert dut in output_ch, "Bad DUT channel"
    for dut in tlu_config["scintilators"]:
        assert dut in input_ch, "Bad Scintilator setting"
    for dut in tlu_config["inverted_inputs"]:
        assert dut in input_ch, "Bad Inverter setting"
    ch_no = [int(x[-1]) for x in tlu_config["dut_channels"]]
    for i in range(4):
        if ch_no.count(i) > 1:
            raise ValueError(
                "Output channels. CHx and LEM0x are exclusive")

    chip = Tlu(output_folder=tlu_config["output_folder"], log_file=tlu_config["log_file"],
               data_file=tlu_config["data_file"], monitor_addr=tlu_config["monitor_addr"],callback=callback)
    chip.init()

    for oe in tlu_config["dut_channels"]:
        if oe[0] == 'C':
            chip['I2C_LED_CNT'][oe] = 3
        else:  # LEMO
            chip['I2C_LEMO_LEDS']['BUSY' + oe[-1]] = 1
            chip['I2C_LEMO_LEDS']['TRIG' + oe[-1]] = 1
            chip['I2C_LEMO_LEDS']['RST' + oe[-1]] = 1

    for oe in tlu_config["dut_channels"]:
        no = oe[-1]
        if no < 4:
            chip['I2C_IP_SEL'][no] = chip.IP_SEL['RJ45'] if oe[0] == 'C' else chip.IP_SEL['LEMO']

    chip.write_i2c_config()

    chip['tlu_master'].MAX_DISTANCE = tlu_config["distance"]
    chip['tlu_master'].THRESHOLD = tlu_config["threshold"]
    chip['tlu_master'].TIMEOUT = tlu_config["timeout"]
    chip['tlu_master'].N_BITS_TRIGGER_ID = tlu_config["n_bits"]

    in_en = 0
    for ie in tlu_config["scintilators"]:
        in_en = in_en | (0x01 << int(ie[-1]))

    out_en = 0
    for oe in tlu_config["dut_channels"]:
        out_en = out_en | (0x01 << int(oe[-1]))

    chip['tlu_master'].EN_OUTPUT = out_en

    in_inv = 0
    for ie in tlu_config["inverted_inputs"]:
        in_inv = in_inv | (0x01 << int(ie[-1]))
    chip['tlu_master'].INVERT_INPUT = in_inv
    return chip, in_en

def main():


    def th_type(x):
        if int(x) > 31 or int(x) < 0:
            raise argparse.ArgumentTypeError("Threshold is 0 to 31")
        return int(x)

    parser = argparse.ArgumentParser(usage="pytlu",
                                     description='TLU DAQ\n TX_STATE: 0= DISABLED 1=WAIT 2=TRIGGERED (wait for busy HIGH) 4=READ_TRIG (wait for busy LOW) LBS is CH0', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-th', '--threshold', type=th_type, default=0,
                        help="Digital threshold for input (in units of 1.5625ns). Default=0", metavar='0...31')
    parser.add_argument('-b', '--n_bits', type=th_type, default=16,
                        help="Number of bits for trigger ID. Should correspond to TLU_TRIGGER_MAX_CLOCK_CYCLES - 1 which is set for TLU module. Default=16", metavar='0...31')
    parser.add_argument('-ds', '--distance', type=th_type, default=31,
                        help="Maximum distance between inputs rise time (in units of 1.5625ns). Default=31, 0=disabled", metavar='0...31')

    parser.add_argument('--timeout', type=int, default=0x0000,
                        help="Timeout to wait for DUT. Default=0, 0=disabled. If you need to be synchronous with multiple DUTs choose timeout = 0.", metavar='0...65535')

    parser.add_argument('-f', '--output_folder', type=str,
                        default=None, help='Output folder of data and log file.  Default: /pytlu/output_data')

    parser.add_argument('--monitor_addr', type=str, default=None,
                        help="Address for online monitor wait for DUT. Default=disabled, Example=tcp://127.0.0.1:5550")
    parser.add_argument('-r','--runcontrol', type=str, default="tcp://localhost:44000",
                        help="Address for eudaq runcontrol, Default=tcp://localhost:44000")

    args = parser.parse_args()

    tlu_config={"distance":args.distance,"threshold":args.threshold,"timeout":args.timeout,"n_bits":args.n_bits,
                "output_folder":args.output_folder,"log_file":None,"data_file":None,"monitor_addr":args.monitor_addr}

    run_producer(args.runcontrol, tlu_config)


if __name__ == '__main__':
    main()
