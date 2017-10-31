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
    #for i in range(8):
    #    chip['GPIO_LED']['LED'] = 0x01 << i
    #    chip['GPIO_LED'].write()
    #    time.sleep(0.2)
    
   
   
    chip['intf'].write(0x3002,[128])
    print 'read 0x3001', chip['intf'].read(0x3000,4)
    print 'read 0x2000', chip['intf'].read(0x2000,10)
    
    #ret = chip['intf']._dev.read_data(1024*1024)
    #print ret
    #print len(ret) #, ret
    #ret = chip['intf']._dev.read_data(1024*1024)
    #print ret
    #print len(ret) #, ret
    
    time.sleep(0.1)
    
    chip['I2C_LED_CNT']['CH3'] = 3
    chip.write_rj45_leds()
   
    print 'TIME_STAMP', chip['tlu_master'].TIME_STAMP
    time.sleep(0.1)
    print 'TIME_STAMP', chip['tlu_master'].TIME_STAMP
    
    #try:
    #chip['i2c'].write(0x41,[6,0x00,0x00])
    #chip['i2c'].write(0x41,[2,0xf0,0xf0])
    
    #chip['i2c'].write(0x81,[6,0xff,0xff])
    #chip['i2c'].write(0x81,[2,0xff,0xf])
    #chip['i2c'].write(0x21,[6,0xff,0xff])
    #chip['i2c'].write(0x21,[2,0xff,0xff])
    
    #chip['i2c'].write(0x42,[6,0xff,0x0ff])
    #chip['i2c'].write(0x42,[2,0xff,0xff])
    
    #chip['i2c'].write(0x44,[6,0xff,0x0ff])
    #chip['i2c'].write(0x44,[2,0xff,0xff])
    
    
    
    #except IOError:
    #    print 'except1'
    
    #print 'write1'
    
    #try:
    
    #except IOError:
    #    print 'except2'
    
    print "write1"
    print 0xe8
    
    #chip['i2c'].write(0x20,[2,0xff,0xff])
    #chip['i2c'].write(0x20,[2])
    #print chip['i2c'].read(0x20,2)