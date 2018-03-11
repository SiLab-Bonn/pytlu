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
import numpy as np

from pytlu.tlu import Tlu

class TestSim(unittest.TestCase):

    def setUp(self):
        
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) #../
        print root_dir
        cocotb_compile_and_run(
            sim_bus ="StreamDriver",
            sim_files = [root_dir + '/tests/tb.v'],
            include_dirs = (root_dir, root_dir + "/firmware/src", root_dir + "/tests")
        )
       
        with open(root_dir + '/pytlu/tlu.yaml', 'r') as f:
            cnfg = yaml.load(f)
        cnfg['transfer_layer'][0]['type'] = 'SiSim'
        cnfg['hw_drivers'].append({'name' : 'SEQ_GEN_TB', 'type' : 'seq_gen', 'interface': 'intf', 'base_addr': 0xc000})
        cnfg['hw_drivers'].append({'name' : 'TLU_TB', 'type' : 'tlu', 'interface': 'intf', 'base_addr': 0xf000})
        cnfg['hw_drivers'].append({'name' : 'FIFO_TB', 'type' : 'bram_fifo', 'interface': 'intf', 'base_addr': 0xf100, 'base_data_addr' : 0x80000000})
        cnfg['hw_drivers'].append({'name' : 'TDC_TB', 'type' : 'tdc_s3', 'interface': 'intf', 'base_addr': 0xf200})
        
        seq_tracks = [{'name': 'T0', 'position': 0},{'name': 'T1', 'position': 1},{'name': 'T2', 'position': 2},{'name': 'T3', 'position': 3}]
        cnfg['registers'].append({'name' : 'SEQ_TB', 'type' : 'TrackRegister', 'hw_driver': 'SEQ_GEN_TB', 'seq_width': 8, 'seq_size': 8*1024, 'tracks': seq_tracks})

        self.dut = Tlu(conf=cnfg)
        self.dut.init()

    def test_single_simle_mode(self):
        
        self.dut['TLU_TB'].TRIGGER_COUNTER = 0
        self.dut['TLU_TB'].TRIGGER_MODE = 2
        self.dut['TLU_TB'].TRIGGER_SELECT = 1
        self.dut['TLU_TB'].TRIGGER_VETO_SELECT = 2
        self.dut['TLU_TB'].TRIGGER_ENABLE = 1

        self.dut['TDC_TB'].EN_TRIGGER_DIST = 1
        self.dut['TDC_TB'].ENABLE = 1
        
        self.dut['tlu_master'].EN_INPUT = 1
        self.dut['tlu_master'].MAX_DISTANCE = 10
        self.dut['tlu_master'].THRESHOLD = 5
        self.dut['tlu_master'].EN_OUTPUT = 1

        how_many = 25
        self.dut['SEQ_TB'].set_repeat(how_many)
        
        self.dut['SEQ_TB']['T0'][:] = 0
        self.dut['SEQ_TB']['T0'][16*40:16*44] = 1
        self.dut['SEQ_TB']['T1'][:] = 0
        self.dut['SEQ_TB']['T1'][16*45:16*49] = 1
            
        self.dut['SEQ_TB'].set_size(55*16+1)
        self.dut['SEQ_TB'].write(56*16)

        self.dut['SEQ_TB'].START
        
        while(not self.dut['SEQ_TB'].is_ready):
            pass
            
        self.check_data(how_many, tdc_en=True)
        
    def check_data(self, how_many, tdc_en = False, start = 0):
        
        for i in range(20):
            self.dut['SEQ_TB'].is_ready
        
        ret = self.dut['FIFO_TB'].get_data()
        
        #for k,w in enumerate(ret):
        #    print k, hex(w)
            
        self.assertEqual(ret.size, how_many * (tdc_en+1))
        
        tlu_word = ret >> 31 == 1
        exp_tlu = np.arange(0x80000000, 0x80000000 + how_many, dtype=np.uint32)
        self.assertEqual(ret[tlu_word].tolist(), exp_tlu.tolist())
        
        #distance is 0x71
        if tdc_en:
            exp_tdc = np.array([135]*how_many, dtype=np.uint32)
            ret_tdc = ret[~tlu_word] >> 20
            self.assertEqual((ret_tdc/2).tolist(), (exp_tdc/2).tolist())
        
        self.assertEqual(self.dut['tlu_master'].TRIGGER_ID, how_many)
        self.assertEqual(self.dut['tlu_master'].TIMEOUT_COUNTER, 0)
        return ret

    def tearDown(self):
        print "============TEARDOWN============="
        self.dut.close()
        time.sleep(10)
        cocotb_compile_clean()


if __name__ == '__main__':
    unittest.main()
