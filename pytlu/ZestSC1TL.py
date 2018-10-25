#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

import logging
import os

from pytlu.ZestSC1 import TluDevice, find_tlu_devices, open_bitfile, modify_bitfile_image

from basil.TL.SiTransferLayer import SiTransferLayer


class ZestSC1Usb(SiTransferLayer):
    '''SiLab USB device
    '''

    BASE_ADDRESS_EXTERNAL = 0x00000
    HIGH_ADDRESS_EXTERNAL = BASE_ADDRESS_EXTERNAL + 0x10000

    BASE_ADDRESS_BLOCK = 0x0001000000000000
    HIGH_ADDRESS_BLOCK = 0xffffffffffffffff

    def __init__(self, conf):
        super(ZestSC1Usb, self).__init__(conf)
        self._dev = None

    def init(self):
        super(ZestSC1Usb, self).init()
        self._init.setdefault('board_sn', None)
        if self._init['board_sn'] and self._init['board_sn'] >= 0:
            self._sidev = TluDevice.from_board_sn(self._init['board_sn'])
        else:
            # search for any available device
            devices = find_tlu_devices()
            if not devices:
                raise IOError('Can\'t find TLU. Connect or reset TLU!')
            else:
                logging.info('Found TLU(s): {}'.format(', '.join(('%s with ID %s (Serial no. %s)' % ('ZestSC1', device.get_card_id(), device.get_serial_number())) for device in devices)))
                if len(devices) > 1:
                    raise ValueError('Found %d TLUs. Please specify "board_sn"' % len(devices))
                self._sidev = devices[0]

        logging.info('Using TLU: {}'.format(str(self._dev)))
        self._dev.open_card()
        if 'bit_file' in self._init.keys():
            if os.path.exists(self._init['bit_file']):
                bit_file = self._init['bit_file']
            elif os.path.exists(os.path.join(os.path.dirname(self.parent.conf_path), self._init['bit_file'])):
                bit_file = os.path.join(os.path.dirname(self.parent.conf_path), self._init['bit_file'])
            else:
                raise ValueError('No such bit file: %s' % self._init['bit_file'])
            logging.info("Programming FPGA: %s..." % (self._init['bit_file']))
            bitfile = open_bitfile(bit_file)
            bitarray = modify_bitfile_image(bitfile)
            self._dev.load_bitarray_to_board(bitarray)

    def write(self, addr, data):
        if(addr >= self.BASE_ADDRESS_EXTERNAL and addr < self.HIGH_ADDRESS_EXTERNAL):
            self._dev.write_register(addr - self.BASE_ADDRESS_EXTERNAL, data)
        elif(addr >= self.BASE_ADDRESS_BLOCK and addr < self.HIGH_ADDRESS_BLOCK):
            self._dev.write_data(data)

    def read(self, addr, size):
        if(addr >= self.BASE_ADDRESS_EXTERNAL and addr < self.HIGH_ADDRESS_EXTERNAL):
            data = self._dev.read_register(addr - self.BASE_ADDRESS_EXTERNAL, size)
            return data
        elif(addr >= self.BASE_ADDRESS_BLOCK and addr < self.HIGH_ADDRESS_BLOCK):
            return self._dev.read_data(size)

    def close(self):
        self._dev.close_board()
