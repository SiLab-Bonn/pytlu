#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

import unittest
import os
from basil.utils.sim.utils import cocotb_compile_and_run, cocotb_compile_clean
import sys
import yaml
import time

from tlu.tlu import Tlu

class TestSim(unittest.TestCase):

    def setUp(self):
        
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) #../
        print root_dir
        cocotb_compile_and_run(
            sim_files = [root_dir + '/tests/tb.v'],
            include_dirs = (root_dir, root_dir + "/firmware/src")
        )
       
        with open(root_dir + '/tlu/tlu.yaml', 'r') as f:
            cnfg = yaml.load(f)
        cnfg['transfer_layer'][0]['type'] = 'SiSim'
        
        self.dut = Tlu(conf=cnfg)
        self.dut.init()

    def test(self):
        
        for i in range(8):
            self.dut['GPIO_LED']['LED'] = 0x01 << i
            self.dut['GPIO_LED'].write()
            time.sleep(0.2)

    def tearDown(self):
        self.dut.close()
        time.sleep(5)
        cocotb_compile_clean()

if __name__ == '__main__':
    unittest.main()
