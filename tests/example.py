#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

from pytlu.tlu import Tlu
#from importlib import import_module
import numpy as np

import time

if __name__ == '__main__':
    #mod = import_module('tlu.ZestSC1Usb')
    chip = Tlu()
    chip.init()
   
    
    np.set_printoptions( linewidth=120 )
    
    #raw_input("Press Enter to continue...")
     
    #size = 512*8
    #chip['stream_fifo'].SET_COUNT = size
    #ret = chip['intf'].read(0x0001000000000000, size)
    #print size, len(ret), ret
    
    #chip['stream_fifo'].SET_COUNT = size
    #ret = chip['intf'].read(0x0001000000000000, size)
            
    #for k in range(2):
    chip['tlu_master'].EN_INPUT = 0
    chip['tlu_master'].MAX_DISTANCE = 31
    chip['tlu_master'].THRESHOLD = 10
    chip['tlu_master'].EN_OUTPUT = 0
    chip['tlu_master'].TIMEOUT = 20

    
    how_many = 10*10**6
    chip['test_pulser'].DELAY = 200 -5
    chip['test_pulser'].WIDTH = 5
    chip['test_pulser'].REPEAT = how_many
    chip['test_pulser'].START

    #time.sleep(0.1)
    
    def get_data(tid):
        retint = chip.get_fifo_data()
        
        if len(retint):
            ok = np.array_equal(retint['trigger_id'], np.arange(tid, tid + len(retint)))
            #print retint['trigger_id']
            print 'ok:', ok, retint['trigger_id'][0], '-', retint['trigger_id'][-1] , float(retint['time_stamp'][-1]) / (40*(10**6)), retint['trigger_id'][-1] - retint['trigger_id'][0], chip['tlu_master'].LOST_DATA_CNT
            
        time.sleep(0.1)
        
        return len(retint)
        
    tid = 0
    while(not chip['test_pulser'].is_ready):
        tid += get_data(tid)
        
    for _ in range(3):
        tid += get_data(tid)
        
    print 'TRIGGER_ID', chip['tlu_master'].TRIGGER_ID
    print 'LOST_DATA_CNT', chip['tlu_master'].LOST_DATA_CNT
    print 'TIMEOUT_COUNTER', chip['tlu_master'].TIME_STAMP, chip['tlu_master'].TIME_STAMP/(40*(10**6))
        