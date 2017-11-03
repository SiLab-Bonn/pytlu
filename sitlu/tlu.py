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
logging.getLogger().setLevel(logging.DEBUG)
import os
import time
import argparse
import signal
signal.signal(signal.SIGINT, signal.default_int_handler)

class Tlu(Dut):
    
    VERSION = 4 
    I2C_MUX = {'DISPLAY': 0 ,'LEMO': 1, 'HDMI': 2, 'MB': 3}
    I2C_ADDR = {'LED': 0x40, 'TRIGGER_EN': 0x42, 'RESET_EN': 0x44, 'IPSEL': 0x46}
    PCA9555 = {'DIR': 6, 'OUT': 2}
    IP_SEL = {'RJ45': 0b11, 'LEMO': 0b10}
    
    def __init__(self,conf=None):
        
        cnfg = conf
        logging.info("Loading configuration file from %s" % conf)
        if conf==None:
            conf = os.path.dirname(os.path.abspath(__file__)) + os.sep + "tlu.yaml"
            
        super(Tlu, self).__init__(conf)

    def init(self):
        super(Tlu, self).init()
        
        fw_version = self['intf'].read(0x2000,1)[0]
        logging.info("TLU firmware version: %s" % (fw_version))        
        if fw_version != self.VERSION:       
            raise Exception("TLU firmware version does not satisfy version requirements (read: %s, require: %s)" % ( fw_version, self.VERSION))

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

        self['i2c'].write(self.I2C_ADDR['LED'], [self.PCA9555['DIR'],0x00,0x00]) 

        val = self['I2C_LED_CNT'].tobytes().tolist()
        self['i2c'].write(self.I2C_ADDR['LED'], [self.PCA9555['OUT'], ~val[0] & 0xff, ~val[1] & 0xff])
        
    
    def write_lemo_leds(self):
        self['I2C_MUX']['SEL'] = self.I2C_MUX['LEMO']
        self['I2C_MUX'].write()
        
        self['i2c'].write(self.I2C_ADDR['LED'], [self.PCA9555['DIR'],0x00,0x00]) 
        
        val = self['I2C_LEMO_LEDS'].tobytes().tolist()
        self['i2c'].write(self.I2C_ADDR['LED'], [self.PCA9555['OUT'], ~val[0] & 0xff, val[1] & 0xff])
        
    def write_trigger_en(self):
        self['I2C_MUX']['SEL'] = self.I2C_MUX['MB']
        self['I2C_MUX'].write()

        self['i2c'].write(self.I2C_ADDR['TRIGGER_EN'], [self.PCA9555['DIR'],0x00,0x00]) 
        val = self['I2C_TRIGGER_EN'].tobytes().tolist()
        self['i2c'].write(self.I2C_ADDR['TRIGGER_EN'], [self.PCA9555['OUT'], val[0] & 0xff, val[1] & 0xff])
    
    def write_reset_en(self):
        self['I2C_MUX']['SEL'] = self.I2C_MUX['MB']
        self['I2C_MUX'].write()

        self['i2c'].write(self.I2C_ADDR['RESET_EN'], [self.PCA9555['DIR'],0x00,0x00]) 
        val = self['I2C_RESET_EN'].tobytes().tolist()
        self['i2c'].write(self.I2C_ADDR['RESET_EN'], [self.PCA9555['OUT'], val[0] & 0xff, val[1] & 0xff])
        
    def write_ip_sel(self):
        self['I2C_MUX']['SEL'] = self.I2C_MUX['MB']
        self['I2C_MUX'].write()

        self['i2c'].write(self.I2C_ADDR['IPSEL'], [self.PCA9555['DIR'],0x00,0x00]) 
        val = self['I2C_IP_SEL'].tobytes().tolist()
        self['i2c'].write(self.I2C_ADDR['IPSEL'], [self.PCA9555['OUT'], val[0] & 0xff, val[1] & 0xff])
        
def main():
    
    input_ch = ['CH0','CH1','CH2', 'CH3']
    output_ch = ['CH0','CH1','CH2', 'CH3','CH4','CH5','LEMO0', 'LEMO1', 'LEMO2', 'LEMO3']
    
    def th_type(x):
        if int(x) > 31 or int(x) < 0:
            raise argparse.ArgumentTypeError("Threshold is 0 to 31")
        return int(x)
    
    parser = argparse.ArgumentParser(description='TLU DAQ \n example: sitlu -ie CH0 -oe CH0', formatter_class=argparse.RawTextHelpFormatter)
    
    parser.add_argument('-ie', '--input_enable', nargs='+', type=str, choices=input_ch, default=[],
                        help='Enabel input channels. Allowed values are '+', '.join(input_ch), metavar='CHx')
    parser.add_argument('-oe','--output_enable', nargs='+', type=str, choices=output_ch, required=True,
                        help='Enabel ouput channels. CHx and LEM0x are exclusiove. Allowed values are '+', '.join(output_ch), metavar='CHx/LEMOx')
    parser.add_argument('-th', '--threshold', type=th_type, default=0, help="Digital threshold for input (in units of 1.5625ns). default=0",metavar='0...31')
    parser.add_argument('-ds', '--distance', type=th_type, default=31, help="Maximum distance betwean inputs rise time (in units of 1.5625ns). default=31",metavar='0...31')
    parser.add_argument('-t', '--test', type=int, help="Generate triggers with given distance.", metavar='1...n')
    parser.add_argument('-c', '--count', type=int, default=0, help="How many triggers. 0=infinite (default) ", metavar='0...n')
    parser.add_argument('--timeout', type=int, default=0xffff, help="Timeout. default=65535", metavar='0...65535')
    parser.add_argument('-inv', '--input_invert', nargs='+', type=str, choices=input_ch, default=[],
                        help='Invert input. Allowed values are '+', '.join(input_ch), metavar='CHx')
    
    args = parser.parse_args()
    
    chip = Tlu()
    chip.init()

    ch_no = [int(x[-1]) for x in args.output_enable]
    for i in range(4):
        if ch_no.count(i) > 1:
            raise argparse.ArgumentTypeError("Output channels. CHx and LEM0x are exclusiove")

    for oe in args.output_enable:
        if oe[0] == 'C':
            chip['I2C_LED_CNT'][oe] = 3
        else:#LEMO
            chip['I2C_LEMO_LEDS']['BUSY'+oe[-1]] = 1
            chip['I2C_LEMO_LEDS']['TRIG'+oe[-1]] = 1
            chip['I2C_LEMO_LEDS']['RST'+oe[-1]] = 1
    
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
    
    chip['tlu_master'].EN_INPUT = in_en
    
    in_inv = 0
    for ie in args.input_invert:
        in_inv = in_inv | (0x01 << int(ie[-1]))
    
    chip['tlu_master'].INVERT_INPUT = in_inv
    
    out_en = 0
    for oe in args.output_enable:
        out_en = out_en | (0x01 << int(oe[-1]))
        
    chip['tlu_master'].EN_OUTPUT = out_en
    
    def print_log(): 
            logging.info("Time: %.2f TriggerId: %8d TimeStamp: %16d Skiped: %2d" % (time.time() - start_time, chip['tlu_master'].TRIGGER_ID, chip['tlu_master'].TIME_STAMP, chip['tlu_master'].SKIP_TRIGGER_COUNT))
        
    if args.test:
        logging.info("Starting test...")
        
        chip['test_pulser'].DELAY = args.test
        chip['test_pulser'].WIDTH = 1
        chip['test_pulser'].REPEAT = args.count
        chip['test_pulser'].START
        
        start_time = time.time()
        while(not chip['test_pulser'].is_ready):
            print_log()
            time.sleep(1)
        print_log()
        return
    
    logging.info("Starting ... Ctrl+C to exit")
    start_time = time.time()
    while True:
        try:
            print_log()
            time.sleep(1)
        except KeyboardInterrupt:
            print_log()
            return
            
if __name__ == '__main__':
    main()

