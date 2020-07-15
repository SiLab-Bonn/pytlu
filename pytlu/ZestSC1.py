import logging
import struct
import array
from threading import RLock as Lock

import numpy as np
import usb.core


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


ID_VENDOR = 0x165d
ID_PRODUCT = 0x0001

BITFILE = {'name': 0x61, 'part': 0x62, 'date': 0x63, 'time': 0x64,
           'image': 0x65}

REQUEST = {'write_register': 0xd0, 'read_register': 0xd1,
           'write_config': 0xd2, 'read_config': 0xd3,
           'write_eeprom': 0xd7, 'read_eeprom': 0xd8,
           'firmware': 0xdc, 'reset_8051': 0xa0,
           'set_signal': 0xd5, 'get_signal': 0xd6,
           'signal_direction': 0xd4}

EEPROM = {'fpga_type': 0xfffa, 'card_id': 0xfffb,
          'serial_number': 0xfffc, 'memory_size': 0xfff6}

ENDPOINT = {'write_ctrl': 0x0040, 'read_ctrl': 0x00c0,
            'write_data': 0x0002, 'read_data': 0x0086,
            'read_int': 0x0081}

VALUE_8051 = 0xe600

# convert array [AB, CD, ...]  to ABCD... (in hex)


def byteshift(array):
    shifted_sum = 0
    for i in range(len(array)):
        shifted_sum += array[i] * 2**(8 * (len(array) - 1 - i))

    return shifted_sum

# the length of the section is saved in len_bytes


def read_bitfile_section(f, len_bytes):
    length = [struct.unpack('B', f.read(1))[0] for i in range(len_bytes)]
    length = byteshift(length)
    return length, f.read(length)

# 16 bytes per row, similar to wireshark capture


def print_bitfile_to_file(bitfile, length):
    f_out = open('f_out.txt', 'w')
    for i in range(0, length, 16):
        if ((length - i) < 16):
            j_max = length - i
        else:
            j_max = 16
        for j in range(j_max):
            f_out.write('{:02X} '.format(bitfile[i + j]))
        f_out.write('\n')
    f_out.close()

# "while byte:" loops over the bitfile until the end is reached
# struct.unpack converts byte to a readable format


def open_bitfile(path_to_file):
    ret = {}

    with open(path_to_file, mode='rb') as f:
        byte = f.read(1)
        while byte:
            value = struct.unpack('B', byte)[0]

            if value == BITFILE['name']:
                ret['name'] = read_bitfile_section(f, 2)
            if value == BITFILE['part']:
                ret['part'] = read_bitfile_section(f, 2)
            if value == BITFILE['date']:
                ret['date'] = read_bitfile_section(f, 2)
            if value is BITFILE['time']:
                ret['time'] = read_bitfile_section(f, 2)
            if value is BITFILE['image']:
                ret['image'] = read_bitfile_section(f, 4)

            byte = f.read(1)

#        self.print_bitfile_to_file(ret['image'][1], ret['image'][0])

    return ret

# weird size modification, no idea why it is necessary


def modify_bitfile_image(bitfile):
    image_size = bitfile['image'][0]
    length = (image_size + 511 + 512) & ~511
    ret = array.array('B', bitfile['image'][1])
    ret += array.array('B', [0] * (length - len(ret)))
    return ret


class TluDevice:
    # device is not None if usb.core.find() does not find any boards
    def __init__(self, device=None):
        self._lock = Lock()
        self.dev = device
        self.dev.set_configuration()

    @classmethod
    def from_board_sn(cls, board_sn):
        usb_devices = usb.core.find(find_all=True, idVendor=ID_VENDOR, idProduct=ID_PRODUCT)
        if usb_devices is None:
            raise ValueError('No device found')

        boards = []
        for usb_device in usb_devices:
            try:
                tlu_device = cls(device=usb_device)
            except usb.core.USBError:
                pass
            else:
                try:
                    curr_board_sn = tlu_device.board_sn
                except usb.core.USBError:
                    pass
                else:
                    if curr_board_sn == board_sn:
                        usb_device.append(usb_device)
                usb_device.dispose()
        if not boards:
            raise ValueError('No device found with SN %d' % board_sn)
        elif len(boards) > 1:
            raise ValueError('Found %d devices with SN %d' % (len(boards), board_sn))
        else:
            return boards[0]

    @property
    def fpga_type(self):
        return self.get_fpga_type()

    @property
    def card_id(self):
        return self.get_card_id()

    @property
    def board_sn(self):
        return self.get_serial_number()

    @property
    def memory_size(self):
        return self.get_memory_size()

    @property
    def fw_version(self):
        return self.get_firmware_version()

    def read_eeprom(self, address):
        return self.dev.ctrl_transfer(ENDPOINT['read_ctrl'],
                                      REQUEST['read_eeprom'], address, 0, 3, timeout=1000)

    def get_fpga_type(self):
        return self.read_eeprom(EEPROM['fpga_type'])[2]

    def get_card_id(self):
        return self.read_eeprom(EEPROM['card_id'])[2]

    def get_serial_number(self):
        return struct.unpack('>I', bytearray(''.join([chr(self.read_eeprom(EEPROM['serial_number'] + i)[2]) for i in range(4)]), 'utf-8'))[0]

    def get_memory_size(self):
        return struct.unpack('>I', bytearray(''.join([chr(self.read_eeprom(EEPROM['memory_size'] + i)[2]) for i in range(4)]), 'utf-8'))[0]

    def get_firmware_version(self):
        return np.array(self.dev.ctrl_transfer(ENDPOINT['read_ctrl'],
                                               REQUEST['firmware'], 0, 0, 3)[0:3:], timeout=1000)

    def __str__(self):
        return str({'card_id': '{}'.format(self.get_card_id()),
                    'fpga_type': '{}'.format(self.get_fpga_type()),
                    'serial_number': ' {}'.format(self.get_serial_number()),
                    'memory_size': '{}'.format(self.get_memory_size()),
                    # 'firmware_version': '{}?'.format(self.get_firmware_version())
                    })

    def _reset_8051(self):
        ret = np.array([0, 0])
        ret[0] = self.dev.ctrl_transfer(ENDPOINT['write_ctrl'],
                                        REQUEST['reset_8051'], VALUE_8051, 0, [1], timeout=1000)
        ret[1] = self.dev.ctrl_transfer(ENDPOINT['write_ctrl'],
                                        REQUEST['reset_8051'], VALUE_8051, 0, [0], timeout=1000)

# Not sure why endpoint is 'read_ctrl' and not 'write_ctrl'
    def write_register(self, index, data):
        with self._lock:
            for i, d in enumerate(data):
                ret = self.dev.ctrl_transfer(ENDPOINT['read_ctrl'],
                                             REQUEST['write_register'], wValue=index + i, wIndex=d,
                                             data_or_wLength=1, timeout=1000)
                logger.debug('write_register: {}'.format(ret))

    def read_register(self, index, length):
        ret = array.array('B',  ('\x00' * length).encode('utf-8'))
        with self._lock:
            for i in range(length):
                ctrl_ret = self.dev.ctrl_transfer(ENDPOINT['read_ctrl'],
                                                  REQUEST['read_register'], wValue=index + i, wIndex=0,
                                                  data_or_wLength=2, timeout=1000)
                ret[i] = ctrl_ret[1]

        logger.debug('read_register: {}'.format(ret))
        return ret

# Not sure if timeout=1000 is necessary
    def write_data(self, data):
        with self._lock:
            assert self.dev.write(ENDPOINT['write_data'], data) == len(data)

    def read_data(self, length):
        with self._lock:
            ret = self.dev.read(ENDPOINT['read_data'], length, timeout=1000)

        logger.debug('read_data: {}'.format(ret))
        return ret

    def set_signal_direction(self, direction):
        with self._lock:
            ret = self.dev.ctrl_transfer(ENDPOINT['read_ctrl'],
                                         REQUEST['signal_direction'], wValue=direction, wIndex=0,
                                         data_or_wLength=1, timeout=1000)
        logger.debug('set_signal_direction: {}'.format(ret))

    def set_signal(self, signal):
        with self._lock:
            ret = self.dev.ctrl_transfer(ENDPOINT['read_ctrl'],
                                         REQUEST['set_signal'], wValue=signal, wIndex=0,
                                         data_or_wLength=1, timeout=1000)
        logger.debug('set_signal: {}'.format(ret))

    def get_signal(self):
        with self._lock:
            ret = self.dev.ctrl_transfer(ENDPOINT['read_ctrl'],
                                         REQUEST['get_signal'], wValue=0, wIndex=0,
                                         data_or_wLength=2, timeout=1000)
        logger.debug('get_signal: {}'.format(ret))
        return ret

    def read_int(self, length):
        with self._lock:
            ret = self.dev.read(ENDPOINT['read_int'], length, timeout=1000)
        logger.debug('read_int: {}'.format(ret))
        return ret

# Not certain if it is really necessary.
# One should send a 4096 byte dummy configuration if the first configuration
# fails? Default should be to use reset_8051() instead of open_card().
    def open_card(self):
        with self._lock:
            self._reset_8051()

            ret = self.dev.ctrl_transfer(ENDPOINT['read_ctrl'],
                                         REQUEST['write_config'], wValue=4096, wIndex=4096,
                                         data_or_wLength=array.array('B', [0, 0]), timeout=1000)
            logger.debug('ctrl_transfer: {}'.format(ret))

            Buffer = np.full(4096, 0, dtype=np.uint16)
            Buffer = array.array('B', Buffer)

            ret = self.dev.write(ENDPOINT['write_data'], Buffer, timeout=1000)
            logger.debug('bulk_write: {}'.format(ret))

            self._reset_8051()

    def load_bitarray_to_board(self, bitarray):
        with self._lock:
            self._reset_8051()

            length = len(bitarray)
            wValue = (length >> 16) & 0xffff
            wIndex = length & 0xffff
            ret = self.dev.ctrl_transfer(ENDPOINT['read_ctrl'],
                                         REQUEST['write_config'], wValue=wValue, wIndex=wIndex,
                                         data_or_wLength=array.array('B', [0, 0]), timeout=1000)
            logger.debug('ctrl_transfer: {}'.format(ret))

            ret = self.dev.write(ENDPOINT['write_data'], bitarray)
            logger.debug('bulk_write: {}'.format(ret))

            ret = self.dev.ctrl_transfer(ENDPOINT['read_ctrl'],
                                         REQUEST['read_config'], wValue=0, wIndex=0,
                                         data_or_wLength=array.array('B', [0, 0, 0]), timeout=1000)
            logger.debug('ctrl_transfer: {}'.format(ret))

    def close_board(self):
        with self._lock:
            ret = self.dev.ctrl_transfer(ENDPOINT['read_ctrl'],
                                         REQUEST['write_config'], wValue=4096, wIndex=4096,
                                         data_or_wLength=array.array('B', [0, 0]), timeout=1000)
            logger.debug('ctrl_transfer: {}'.format(ret))

            self._reset_8051()


# find_all=True: devs is not None if no boards are found, so it's pointless to
# check if any boards were found
# find_all=False: dev is None if no TLU is found
# the usb backend can be changed if required
def find_tlu_devices():
    # backend = usb.backend.libusb1.get_backend(find_library=lambda x:
    #                                           "/usr/lib/libusb-1.0.so")
    # devs = usb.core.find(find_all=True,
    #                      idVendor=ID_VENDOR,
    #                      idProduct=ID_PRODUCT,
    #                      backend=backend)

    devs = usb.core.find(find_all=True,
                         idVendor=ID_VENDOR,
                         idProduct=ID_PRODUCT)

    return [TluDevice(device=dev) for dev in devs]
