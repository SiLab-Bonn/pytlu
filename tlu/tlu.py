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

class Tlu(Dut):
    
    VERSION = 4 
    I2C_MUX = {'DISPLAY': 0 ,'LEMO': 1, 'HDMI': 2, 'MB': 3}
    I2C_ADDR = {'LED': 0x40, 'TRIGGER_EN': 0x42, 'RESET_EN': 0x44, 'IPSEL': 0x46}
    PCA9555 = {'DIR': 6, 'OUT': 2}
    IP_SEL = {'RJ45': 0, 'LEMO': 2}
    
    def __init__(self,conf=None):
        
        if conf==None:
            conf = os.path.dirname(os.path.abspath(__file__)) + os.sep + "tlu.yaml"
        
        logging.info("Loading configuration file from %s" % conf)
        #TODO:add loading bit file 
        
        super(Tlu, self).__init__(conf)
        
    def init(self):
        super(Tlu, self).init()
        
        fw_version = self['intf'].read(0x2000,1)[0]
        logging.info("TLU firmware version: %s" % (fw_version))        
        if fw_version != self.VERSION:       
            raise Exception("TLU firmware version does not satisfy version requirements (read: %s, require: %s)" % ( fw_version, self.VERSION))

        #LEDS OFF
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
        
        
        
if __name__=="__main__":
    chip = Tlu()
    chip.init()
   
    #TODO: make it work add setup arguments
