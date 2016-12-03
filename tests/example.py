#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

from tlu.tlu import Tlu
#from importlib import import_module
import time

if __name__ == '__main__':
    #mod = import_module('tlu.ZestSC1Usb')
    chip = Tlu()
    chip.init()
    for i in range(8):
        chip['GPIO_LED']['LED'] = 0x01 << i
        chip['GPIO_LED'].write()
        time.sleep(0.2)
    print chip['GPIO_LED'].get_data()
    chip['intf'].write(0x3002,[128])
    print 'read 0x3001', chip['intf'].read(0x3000,4)
    print 'read 0x2000', chip['intf'].read(0x2000,10)
    
    ret = chip['intf']._dev.read_data(1024*1024)
    #print ret
    print len(ret), ret
    ret = chip['intf']._dev.read_data(1024*1024)
    #print ret
    print len(ret), ret
