#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#
import os
import time
import unittest
import yaml

import numpy as np

from basil.utils.sim.utils import cocotb_compile_and_run, cocotb_compile_clean

from pytlu.tlu import Tlu


class TestSim(unittest.TestCase):
    def setUp(self):
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        print(root_dir)
        cocotb_compile_and_run(
            sim_bus="StreamDriver",
            sim_files=[root_dir + '/tests/tb.v'],
            include_dirs=(root_dir, root_dir + "/firmware/src", root_dir + "/tests"))

        with open(root_dir + '/pytlu/tlu.yaml', 'r') as f:
            cnfg = yaml.load(f)
        cnfg['transfer_layer'][0]['type'] = 'SiSim'
        cnfg['hw_drivers'].append({'name': 'SEQ_GEN_TB', 'type': 'seq_gen', 'interface': 'intf', 'base_addr': 0xc000})
        cnfg['hw_drivers'].append({'name': 'TLU_TB', 'type': 'tlu', 'interface': 'intf', 'base_addr': 0xf000})
        cnfg['hw_drivers'].append({'name': 'FIFO_TB', 'type': 'bram_fifo', 'interface': 'intf', 'base_addr': 0xf100, 'base_data_addr': 0x80000000})
        cnfg['hw_drivers'].append({'name': 'TDC_TB', 'type': 'tdc_s3', 'interface': 'intf', 'base_addr': 0xf200})
        cnfg['hw_drivers'].append({'name': 'VETO_PULSER_TB', 'type': 'pulse_gen', 'interface': 'intf', 'base_addr': 0xf300})

        seq_tracks = [{'name': 'T0', 'position': 0}, {'name': 'T1', 'position': 1}, {'name': 'T2', 'position': 2}, {'name': 'T3', 'position': 3}]
        cnfg['registers'].append({'name': 'SEQ_TB', 'type': 'TrackRegister', 'hw_driver': 'SEQ_GEN_TB', 'seq_width': 8, 'seq_size': 8 * 1024, 'tracks': seq_tracks})

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
        self.dut['SEQ_TB']['T0'][16 * 40:16 * 44] = 1

        self.dut['SEQ_TB'].set_size(45 * 16 + 1)
        self.dut['SEQ_TB'].write(46 * 16)

        self.dut['SEQ_TB'].START

        while not self.dut['SEQ_TB'].is_ready:
            pass

        self.check_data(how_many, tdc_en=True)

    def test_single_full_mode(self):
        self.dut['TLU_TB'].TRIGGER_COUNTER = 0
        self.dut['TLU_TB'].TRIGGER_MODE = 3
        self.dut['TLU_TB'].TRIGGER_SELECT = 1
        self.dut['TLU_TB'].TRIGGER_VETO_SELECT = 2
        self.dut['TLU_TB'].TRIGGER_ENABLE = 1
        self.dut['TLU_TB'].TRIGGER_DATA_DELAY = 2

        self.dut['tlu_master'].EN_INPUT = 1
        self.dut['tlu_master'].MAX_DISTANCE = 10
        self.dut['tlu_master'].THRESHOLD = 0
        self.dut['tlu_master'].EN_OUTPUT = 1
        self.dut['tlu_master'].N_BITS_TRIGGER_ID = 15

        self.dut['SEQ_TB'].set_repeat(1)
        self.dut['SEQ_TB']['T0'][:] = 0
        self.dut['SEQ_TB'].write(40 * 40)
        self.dut['SEQ_TB'].set_size(40 * 40)

        how_many = 25
        for i in range(how_many):
            self.dut['SEQ_TB']['T0'][:] = 0
            self.dut['SEQ_TB']['T0'][0:i + 1] = 1
            self.dut['SEQ_TB'].write(32)

            self.dut['SEQ_TB'].START

            while not self.dut['SEQ_TB'].is_ready:
                pass

        self.check_data(how_many)

    def test_injection_test(self):
        self.dut['TLU_TB'].TRIGGER_COUNTER = 0
        self.dut['TLU_TB'].TRIGGER_MODE = 3
        self.dut['TLU_TB'].TRIGGER_SELECT = 1
        self.dut['TLU_TB'].TRIGGER_VETO_SELECT = 2
        self.dut['TLU_TB'].TRIGGER_ENABLE = 1
        self.dut['TLU_TB'].TRIGGER_DATA_DELAY = 2

        self.dut['tlu_master'].EN_INPUT = 1
        self.dut['tlu_master'].MAX_DISTANCE = 10
        self.dut['tlu_master'].THRESHOLD = 0
        self.dut['tlu_master'].EN_OUTPUT = 1
        self.dut['tlu_master'].N_BITS_TRIGGER_ID = 15
        # self.dut['tlu_master'].TIMEOUT = 3
        
        how_many = 50
        self.dut['test_pulser'].DELAY = 200
        self.dut['test_pulser'].WIDTH = 10
        self.dut['test_pulser'].REPEAT = how_many
        self.dut['test_pulser'].START

        while not self.dut['test_pulser'].is_ready:
            pass

        self.check_data(how_many)

    def test_digital_threshold(self):
        self.dut['TLU_TB'].TRIGGER_COUNTER = 0
        self.dut['TLU_TB'].TRIGGER_MODE = 2
        self.dut['TLU_TB'].TRIGGER_SELECT = 1
        self.dut['TLU_TB'].TRIGGER_VETO_SELECT = 2
        self.dut['TLU_TB'].TRIGGER_ENABLE = 1

        self.dut['TDC_TB'].EN_TRIGGER_DIST = 1
        self.dut['TDC_TB'].ENABLE = 1

        self.dut['tlu_master'].EN_INPUT = 1
        self.dut['tlu_master'].EN_OUTPUT = 1
        self.dut['tlu_master'].MAX_DISTANCE = 10
        self.dut['tlu_master'].THRESHOLD = 0

        self.dut['SEQ_TB'].set_repeat(1)

        self.dut['SEQ_TB']['T0'][:] = 0
        self.dut['SEQ_TB']['T0'][0:1] = 1
        self.dut['SEQ_TB']['T0'][1000:1002] = 1
        self.dut['SEQ_TB']['T0'][2000:2003] = 1
        self.dut['SEQ_TB']['T0'][3000:3004] = 1
        self.dut['SEQ_TB']['T0'][4000:4030] = 1
        self.dut['SEQ_TB']['T0'][5000:5031] = 1
        self.dut['SEQ_TB']['T0'][6000:6032] = 1
        self.dut['SEQ_TB']['T0'][7000:7033] = 1

        self.dut['SEQ_TB'].set_size(7100)
        self.dut['SEQ_TB'].write(7100)

        start = 0
        exp = [8, 7, 6, 5, 4, 3, 2]
        for i, th in enumerate([0, 1, 2, 3, 10, 30, 31]):

            self.dut['tlu_master'].THRESHOLD = th
            self.dut['SEQ_TB'].START
            while not self.dut['SEQ_TB'].is_ready:
                pass

            ret = self.dut['FIFO_TB'].get_data()

            # for k,w in enumerate(ret):
            #    print(k, hex(w))

            self.assertEqual(ret.size, exp[i] * 2)

            tlu_word = ret >> 31 == 1
            exp_tlu = np.arange(0x80000000 + start, 0x80000000 + start + exp[i], dtype=np.uint32)
            self.assertEqual(np.array_equal(ret[tlu_word], exp_tlu), True)

            exp_tdc = np.array([134] * exp[i], dtype=np.uint32)
            # tdc referencee to previus
            if i != 0:
                exp_tdc[0] = 0xff
            ret_tdc = ret[~tlu_word] >> 20

            self.assertFalse(np.any(np.abs(ret_tdc - exp_tdc) > 1))

            self.assertEqual(self.dut['tlu_master'].TRIGGER_ID, start + exp[i])

            start += exp[i]

    def check_data(self, how_many, tdc_en=False, start=0):
        for i in range(20):
            self.dut['SEQ_TB'].is_ready

        ret = self.dut['FIFO_TB'].get_data()

        # check number of received triggers
        self.assertEqual(ret.size, how_many * (tdc_en + 1))

        tlu_word = ret >> 31 == 1
        exp_tlu = np.arange(0x80000000, 0x80000000 + how_many, dtype=np.uint32)

        # check if received trigger words from FIFO are correct
        self.assertEqual(ret[tlu_word].tolist(), exp_tlu.tolist())

        # distance is 0x71
        if tdc_en:
            exp_tdc = np.array([135] * how_many, dtype=np.uint32)
            ret_tdc = ret[~tlu_word] >> 20
            self.assertEqual((ret_tdc / 2).tolist(), (exp_tdc / 2).tolist())

        self.assertEqual(self.dut['tlu_master'].TRIGGER_ID, how_many)
        self.assertEqual(self.dut['tlu_master'].TIMEOUT_COUNTER, 0)
        return ret

    def test_timeout(self):
        self.dut['tlu_master'].EN_INPUT = 0
        self.dut['tlu_master'].MAX_DISTANCE = 31
        self.dut['tlu_master'].THRESHOLD = 0
        self.dut['tlu_master'].EN_OUTPUT = 1
        self.dut['tlu_master'].TIMEOUT = 5

        self.dut['TDC_TB'].EN_TRIGGER_DIST = 1
        self.dut['TDC_TB'].ENABLE = 1

        how_many = 300
        distance = 20
        self.dut['test_pulser'].DELAY = distance - 1
        self.dut['test_pulser'].WIDTH = 1
        self.dut['test_pulser'].REPEAT = how_many
        self.dut['test_pulser'].START

        while not self.dut['test_pulser'].is_ready:
            pass

        ret = self.dut['FIFO_TB'].get_data()
        self.assertEqual(ret.size, how_many)

        ret_fifo = self.dut.get_fifo_data()
        self.assertEqual(ret.size, how_many)
        self.assertEqual(range(how_many), ret_fifo['trigger_id'].tolist())
        self.assertEqual(range(ret_fifo['time_stamp'][0], int(ret_fifo['time_stamp'][0]) + how_many * distance, distance), ret_fifo['time_stamp'].tolist())

        self.assertEqual(self.dut['tlu_master'].TRIGGER_ID, how_many)
        self.assertEqual(self.dut['tlu_master'].TIMEOUT_COUNTER, 255 if how_many > 255 else how_many)

    def test_multi_input_distance(self):
        self.dut['TLU_TB'].TRIGGER_COUNTER = 0
        self.dut['TLU_TB'].TRIGGER_MODE = 2
        self.dut['TLU_TB'].TRIGGER_SELECT = 1
        self.dut['TLU_TB'].TRIGGER_VETO_SELECT = 2
        self.dut['TLU_TB'].TRIGGER_ENABLE = 1

        self.dut['tlu_master'].EN_INPUT = 0b1111
        self.dut['tlu_master'].EN_OUTPUT = 0b000001
        self.dut['tlu_master'].THRESHOLD = 0

        max_distances = [0, 15, 31]

        for max_distance in max_distances:
            self.dut['tlu_master'].MAX_DISTANCE = max_distance
            if max_distance == 0:
                # max distance of zero means disabled, thus expect no generated trigger
                delays = [0]
                exp = [0]
            if max_distance == 15:
                delays = [0, 5, 14, 15, 16, 17]
                exp = [4, 4, 4, 0, 0, 0]
            if max_distance == 31:
                delays = [0, 5, 30, 31, 32, 33]
                exp = [4, 4, 4, 0, 0, 0]
            for i, delay in enumerate(delays):
                self.dut['SEQ_TB'].set_repeat(1)
                self.dut['SEQ_TB']['T0'][:] = 0
                self.dut['SEQ_TB']['T1'][:] = 0
                self.dut['SEQ_TB']['T2'][:] = 0
                self.dut['SEQ_TB']['T3'][:] = 0

                self.dut['SEQ_TB']['T0'][0 + delay:31 + delay] = 1
                self.dut['SEQ_TB']['T1'][0:31] = 1
                self.dut['SEQ_TB']['T2'][0:31] = 1
                self.dut['SEQ_TB']['T3'][0:31] = 1

                self.dut['SEQ_TB']['T0'][1000:1031] = 1
                self.dut['SEQ_TB']['T1'][1000 + delay:1031 + delay] = 1
                self.dut['SEQ_TB']['T2'][1000:1031] = 1
                self.dut['SEQ_TB']['T3'][1000:1031] = 1

                self.dut['SEQ_TB']['T0'][2000:2031] = 1
                self.dut['SEQ_TB']['T1'][2000:2031] = 1
                self.dut['SEQ_TB']['T2'][2000 + delay:2031 + delay] = 1
                self.dut['SEQ_TB']['T3'][2000:2031] = 1

                self.dut['SEQ_TB']['T0'][3000:3031] = 1
                self.dut['SEQ_TB']['T1'][3000:3031] = 1
                self.dut['SEQ_TB']['T2'][3000:3031] = 1
                self.dut['SEQ_TB']['T3'][3000 + delay:3031 + delay] = 1

                self.dut['SEQ_TB'].set_size(4000)
                self.dut['SEQ_TB'].write(4000)

                self.dut['SEQ_TB'].START

                while(not self.dut['SEQ_TB'].is_ready):
                    pass

                ret = self.dut['FIFO_TB'].get_data()

                self.assertEqual(ret.size, exp[i])

    def test_fifo_readout(self):
        self.dut['tlu_master'].EN_INPUT = 0
        self.dut['tlu_master'].MAX_DISTANCE = 31
        self.dut['tlu_master'].THRESHOLD = 10
        self.dut['tlu_master'].EN_OUTPUT = 0
        self.dut['tlu_master'].TIMEOUT = 20

        how_many = 100
        self.dut['test_pulser'].DELAY = 200 - 5
        self.dut['test_pulser'].WIDTH = 5
        self.dut['test_pulser'].REPEAT = how_many

        with self.dut.readout():
            self.dut['test_pulser'].START
            while not self.dut['test_pulser'].is_ready:
                pass

        self.assertEqual(self.dut.fifo_readout.get_record_count(), how_many)

    def test_tlu_veto(self):
        self.dut['TLU_TB'].TRIGGER_COUNTER = 0
        self.dut['TLU_TB'].TRIGGER_MODE = 3
        self.dut['TLU_TB'].TRIGGER_SELECT = 0
        self.dut['TLU_TB'].TRIGGER_VETO_SELECT = 1  # veto on veto pulse
        self.dut['TLU_TB'].EN_TLU_VETO = 1  # enable TLU veto
        self.dut['TLU_TB'].TRIGGER_ENABLE = 1
        self.dut['TLU_TB'].TRIGGER_DATA_DELAY = 2
        self.dut['TLU_TB'].HANDSHAKE_BUSY_VETO_WAIT_CYCLES = 0  # be directly after de-asserting BUSY ready for incoming vetos
        self.dut['TLU_TB'].TRIGGER_HANDSHAKE_ACCEPT_WAIT_CYCLES = 1

        self.dut['tlu_master'].EN_INPUT = 1
        self.dut['tlu_master'].MAX_DISTANCE = 10
        self.dut['tlu_master'].THRESHOLD = 1
        self.dut['tlu_master'].EN_OUTPUT = 1

        # generate veto signals
        how_many_vetos = 80
        distance_veto = 80
        self.dut['VETO_PULSER_TB'].DELAY = distance_veto - 1
        self.dut['VETO_PULSER_TB'].WIDTH = 100
        self.dut['VETO_PULSER_TB'].REPEAT = how_many_vetos
        self.dut['VETO_PULSER_TB'].START

        how_many_triggers = 50
        self.dut['test_pulser'].DELAY = 200
        self.dut['test_pulser'].WIDTH = 1
        self.dut['test_pulser'].REPEAT = how_many_triggers
        self.dut['test_pulser'].START

        while not self.dut['test_pulser'].is_ready:
            pass

        expected_vetoed_triggers = 29  # 29 triggers will not be accepted due to veto signal
        self.check_data(how_many_triggers - expected_vetoed_triggers)

    def tearDown(self):
        self.dut.close()
        time.sleep(5)
        cocotb_compile_clean()


if __name__ == '__main__':
    unittest.main()
