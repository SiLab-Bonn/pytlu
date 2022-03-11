#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#
# Initial version by Chris Higgs <chris.higgs@potentialventures.com>
#

# pylint: disable=pointless-statement, expression-not-assigned


import cocotb
from cocotb.binary import BinaryValue
from cocotb.triggers import RisingEdge, Timer
from cocotb.clock import Clock
from cocotb_bus.drivers import BusDriver


class StreamDriver(BusDriver):
    """Abastract away interactions with the control bus.
    """
    _signals = ["BUS_CLK", "BUS_RST", "BUS_DATA", "BUS_ADD", "BUS_RD", "BUS_WR", "STREAM_READY", "STREAM_WRITE", "STREAM_DATA"]
    _optional_signals = ["BUS_BYTE_ACCESS"]

    def __init__(self, entity):
        BusDriver.__init__(self, entity, "", entity.BUS_CLK, case_insensitive=False)

        # Create an appropriately sized high-impedence value
        self._high_impedence = BinaryValue(n_bits=len(self.bus.BUS_DATA))
        self._high_impedence.binstr = "Z" * len(self.bus.BUS_DATA)

        # Create an appropriately sized high-impedence value
        self._x = BinaryValue(n_bits=len(self.bus.BUS_ADD))
        self._x.binstr = "x" * len(self.bus.BUS_ADD)

        self._has_byte_acces = False

        self.BASE_ADDRESS_STREAM = 0x0001000000000000

        # Kick off a clock generator
        cocotb.fork(Clock(self.clock, 20000).start())

    @cocotb.coroutine
    def init(self):
        # Defaults
        self.bus.BUS_RST.value = 1
        self.bus.BUS_RD.value = 0
        self.bus.BUS_WR.value = 0
        self.bus.BUS_ADD.value = self._x
        self.bus.BUS_DATA.value = self._high_impedence
        self.bus.STREAM_READY.value = 0

        for _ in range(8):
            yield RisingEdge(self.clock)

        self.bus.BUS_RST.value = 0

        for _ in range(2):
            yield RisingEdge(self.clock)

        # why this does not work? hasattr(self.bus, 'BUS_BYTE_ACCESS'):
        try:
            getattr(self.bus, 'BUS_BYTE_ACCESS')
        except Exception:
            self._has_byte_acces = False
        else:
            self._has_byte_acces = True

    @cocotb.coroutine
    def read(self, address, size):
        result = []

        if address >= self.BASE_ADDRESS_STREAM:
            result = yield self.read_stream(address, size)
        else:
            self.bus.BUS_DATA.value = self._high_impedence
            self.bus.BUS_ADD.value = self._x
            self.bus.BUS_RD.value = 0

            yield RisingEdge(self.clock)

            byte = 0
            while(byte <= size):
                if(byte == size):
                    self.bus.BUS_RD.value = 0
                else:
                    self.bus.BUS_RD.value = 1

                self.bus.BUS_ADD.value = address + byte

                yield RisingEdge(self.clock)

                if(byte != 0):
                    if(self._has_byte_acces and self.bus.BUS_BYTE_ACCESS.value.integer == 0):
                        result.append(self.bus.BUS_DATA.value.integer & 0x000000ff)
                        result.append((self.bus.BUS_DATA.value.integer & 0x0000ff00) >> 8)
                        result.append((self.bus.BUS_DATA.value.integer & 0x00ff0000) >> 16)
                        result.append((self.bus.BUS_DATA.value.integer & 0xff000000) >> 24)
                    else:
                        # result.append(self.bus.BUS_DATA.value[24:31].integer & 0xff)
                        if len(self.bus.BUS_DATA.value) == 8:
                            result.append(self.bus.BUS_DATA.value.integer & 0xff)
                        else:
                            # value = self.bus.BUS_DATA.value[24:31].integer & 0xff
                            # workaround for cocotb https://github.com/potentialventures/cocotb/pull/459
                            value = BinaryValue(self.bus.BUS_DATA.value.binstr[24:32])
                            result.append(value.integer)

                if(self._has_byte_acces and self.bus.BUS_BYTE_ACCESS.value.integer == 0):
                    byte += 4
                else:
                    byte += 1

            self.bus.BUS_ADD.value = self._x
            self.bus.BUS_DATA.value = self._high_impedence
            yield RisingEdge(self.clock)

        return result

    @cocotb.coroutine
    def write(self, address, data):

        self.bus.BUS_ADD.value = self._x
        self.bus.BUS_DATA.value = self._high_impedence
        self.bus.BUS_WR.value = 0

        yield RisingEdge(self.clock)

        for index, byte in enumerate(data):
            self.bus.BUS_DATA.value = byte
            self.bus.BUS_WR.value = 1
            self.bus.BUS_ADD.value = address + index
            yield Timer(1)  # This is hack for iverilog
            self.bus.BUS_DATA.value = byte
            self.bus.BUS_WR.value = 1
            self.bus.BUS_ADD.value = address + index

            yield RisingEdge(self.clock)

        if(self._has_byte_acces and self.bus.BUS_BYTE_ACCESS.value.integer == 0):
            raise NotImplementedError("BUS_BYTE_ACCESS for write to be implemented.")

        self.bus.BUS_DATA.value = self._high_impedence
        self.bus.BUS_ADD.value = self._x
        self.bus.BUS_WR.value = 0

        yield RisingEdge(self.clock)

    @cocotb.coroutine
    def read_stream(self, address, size):
        result = []

        yield RisingEdge(self.clock)
        self.bus.STREAM_READY.value = 1

        for _ in range(size // 2):

            yield RisingEdge(self.clock)

            while self.bus.STREAM_WRITE.value.integer == 0:
                yield RisingEdge(self.clock)

            result.append(self.bus.STREAM_DATA.value.integer & 0xff)
            result.append((self.bus.STREAM_DATA.value.integer >> 8) & 0xff)

        yield RisingEdge(self.clock)
        yield RisingEdge(self.clock)
        yield RisingEdge(self.clock)
        yield RisingEdge(self.clock)
        self.bus.STREAM_READY.value = 0
        yield RisingEdge(self.clock)

        return result
