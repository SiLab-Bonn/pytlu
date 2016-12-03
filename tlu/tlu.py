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

class Tlu(Dut):
    
    VERSION = 4 

    def __init__(self,conf=None):
        
        if conf==None:
            conf = os.path.dirname(os.path.abspath(__file__)) + os.sep + "tlu.yaml"
        
        logging.info("Loading configuration file from %s" % conf)
       
        super(Tlu, self).__init__(conf)
    
    def init(self):
        super(Tlu, self).init()
        
        fw_version = self['intf'].read(0x2000,1)[0]
        logging.info("TLU firmware version: %s" % (fw_version))        
        if fw_version != self.VERSION:       
            raise Exception("TLU firmware version does not satisfy version requirements (read: %s, require: %s)" % ( fw_version, self.VERSION))

if __name__=="__main__":
    chip = Tlu()
    chip.init()
    chip.power_up()
    
