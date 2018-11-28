# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

from basil.HL.RegisterHardwareLayer import RegisterHardwareLayer


class stream_fifo(RegisterHardwareLayer):
    ''' Stream FIFO
    '''
    _registers = {'RESET': {'descr': {'addr': 0, 'size': 8, 'properties': ['writeonly']}},
                  'VERSION': {'descr': {'addr': 0, 'size': 8, 'properties': ['ro']}},
                  'SET_COUNT': {'descr': {'addr': 1, 'size': 24}},
                  'SIZE': {'descr': {'addr': 4, 'size': 24}},
                  }

    _require_version = "==2"

    def __init__(self, intf, conf):
        super(stream_fifo, self).__init__(intf, conf)

    def reset(self):
        '''Soft reset the module.'''
        self.RESET = 0
