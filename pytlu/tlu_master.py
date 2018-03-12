#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

from basil.HL.RegisterHardwareLayer import RegisterHardwareLayer


class tlu_master(RegisterHardwareLayer):
    '''
    '''
    _registers = {'RESET':      {'descr': {'addr': 0, 'size': 8, 'properties': ['writeonly']}},
                  'VERSION':    {'descr': {'addr': 0, 'size': 8, 'properties': ['ro']}},
                  'START': {'descr': {'addr': 1, 'size': 8, 'properties': ['writeonly']}},
                  'READY': {'descr': {'addr': 1, 'size': 1, 'properties': ['ro']}},
                  
                  'EN_INPUT':           {'descr': {'addr': 3, 'size': 4, 'offset': 0}},
                  'INVERT_INPUT':       {'descr': {'addr': 3, 'size': 4, 'offset': 4}},
                  
                  'MAX_DISTANCE':       {'descr': {'addr': 4, 'size': 5, 'offset': 0}},
                  'THRESHOLD':          {'descr': {'addr': 5, 'size': 5, 'offset': 0}},
                  'EN_OUTPUT':          {'descr': {'addr': 6, 'size': 6, 'offset': 0}},
                  
                  'TIMEOUT':            {'descr': {'addr': 7, 'size': 16, 'offset': 0}},

                  'N_BITS_TRIGGER_ID':  {'descr': {'addr': 9, 'size': 5, 'offset': 0}},
                 
                 'TIME_STAMP': {'descr': {'addr': 16, 'size': 64, 'properties': ['ro']}},
                 'TRIGGER_ID': {'descr': {'addr': 24, 'size': 32, 'properties': ['ro']}},
                 'SKIP_TRIG_COUNTER': {'descr': {'addr': 28, 'size': 32, 'properties': ['ro']}},
                 'TIMEOUT_COUNTER': {'descr': {'addr': 32, 'size': 8, 'properties': ['ro']}},
                 'LOST_DATA_CNT': {'descr': {'addr': 33, 'size': 8, 'properties': ['ro']}},

                  }
    
    _require_version = "==1"

    def __init__(self, intf, conf):
        super(tlu_master, self).__init__(intf, conf)

    def reset(self):
        '''Soft reset the module.'''
        self.RESET = 0

