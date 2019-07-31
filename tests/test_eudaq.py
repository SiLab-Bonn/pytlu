#
# ------------------------------------------------------------
# Copyright (c) All rights reserved
# SiLab, Institute of Physics, University of Bonn
# ------------------------------------------------------------
#

'''
This test case needs a working eudaq 1.x-dev installation and the
eudaq/python folder added to the python path, see:
https://github.com/SiLab-Bonn/pytlu/blob/development/README.md

The installation has to done at std. location (bin/lib in
eudaq folder)

Otherwise the unit tests are all skipped.
'''

import os
import time
import unittest
import threading
import subprocess
import sys
from queue import Queue, Empty

import tables as tb
import psutil
import numpy as np

from pytlu import tlu_eudaq
from tests import utils

pytlu_path = os.path.dirname(tlu_eudaq.__file__)
data_folder = os.path.abspath(os.path.join(pytlu_path, '..', 'data'))
dir_path = os.path.dirname(os.path.realpath(__file__))


def run_process_with_queue(command, arguments=None):
    if os.name == 'nt':
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        creationflags = 0
    args = [command]
    if arguments:
        args += [str(a) for a in arguments]
    ON_POSIX = 'posix' in sys.builtin_module_names
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         bufsize=1, close_fds=ON_POSIX, creationflags=creationflags)
    print_queue = Queue()
    t = threading.Thread(target=enqueue_output, args=(p.stdout, print_queue))
    t.daemon = True  # thread dies with the program
    t.start()

    return p, print_queue


def kill(proc):
    ''' Kill process by id, including subprocesses.

        Works for Linux and Windows
    '''
    process = psutil.Process(proc.pid)
    for child_proc in process.children(recursive=True):
        child_proc.kill()
    process.kill()


def eurun_control(min_connections=2, run_time=5):
    ''' Start a EUDAQ run control instance

    Waits for min_connections to send configure command.
    Start the run for run_time and then send EOR.
    '''
    from PyEUDAQWrapper import PyRunControl
    prc = PyRunControl("44000")
    while prc.NumConnections < min_connections:
        time.sleep(1)
        print("Number of active connections: ", prc.NumConnections)
    # Load configuration file
    prc.Configure(os.path.join(dir_path, "TestConfig.conf"))
    # Wait that the connections can receive the config
    time.sleep(2)
    # Wait until all connections answer with 'OK'
    while not prc.AllOk:
        time.sleep(0.5)
        print("Successfullly configured!")
    # Start the run
    prc.StartRun()
    # Wait for run start
    while not prc.AllOk:
        time.sleep(0.5)
    # Main run loop
    time.sleep(run_time)
    # Stop run
    prc.StopRun()
    time.sleep(2)


def enqueue_output(out, queue):
    ''' https://stackoverflow.com/questions/375427/non-blocking-read-on-a-subprocess-pipe-in-python '''
    for line in iter(out.readline, b''):
        queue.put(line)
    out.close()


def queue_to_string(queue, max_lines=1000):
    return_str = ''
    for _ in range(max_lines):
        try:
            line = queue.get_nowait()
        except Empty:
            break
        else:  # got line
            return_str += line.decode("utf-8") + '\n'
    return return_str


class TestEudaq(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            import PyEUDAQWrapper
            eudaq_wrapper_path = os.path.dirname(PyEUDAQWrapper.__file__)
            cls.eudaq_bin_folder = os.path.abspath(os.path.join(eudaq_wrapper_path, '..', 'bin'))
            cls.no_eudaq_install = False
        except ImportError:
            cls.no_eudaq_install = True

    @classmethod
    def tearDownClass(cls):
        os.remove(os.path.join(data_folder, 'tlu_example_data_out.h5'))
        os.remove(os.path.join(data_folder, 'tlu_example_data_snd.h5'))

    def test_replay_data(self):
        ''' Test the communication with replayed data using the replay data functionality.

            Starts a complete EUDAQ data taking scenario:
                Run control + TestDataConverter + pytlu producer

            Success of this test is checked by stdout inspection.
        '''

        if self.no_eudaq_install:
            self.skipTest("No working EUDAQ installation found, skip test!")
        t_rc = threading.Thread(target=eurun_control, kwargs={"min_connections": 2,
                                                              "run_time": 5})
        t_rc.start()
        time.sleep(2)
        # EUDAQ 1.7-dev --> EUDAQ 1.x-dev: Change of name from TestDataCollector --> DataCollector
        # EUDAQ 1.x-dev Another change of name from DataCollector --> euDataCollector
        data_coll_process, data_coll_q = run_process_with_queue(command=os.path.join(self.eudaq_bin_folder, 'euDataCollector.exe'))
        time.sleep(2)
        pytlu_prod_process, pytlu_prod_q = run_process_with_queue(
            command='pytlu_eudaq',
            arguments=['--replay',
                       '%s' % os.path.join(data_folder, 'tlu_example_data.h5'),
                       '--delay', '0.001'])
        time.sleep(10)
        t_rc.join()
        time.sleep(5)
        # Read up to 1000 lines from Data Collector output
        coll_output = queue_to_string(data_coll_q)
        prod_output = queue_to_string(pytlu_prod_q)

        # Subprocesses have to be killed since no terminate signal is available
        # from euRun wrapped with python
        kill(data_coll_process)
        kill(pytlu_prod_process)

        # Check configurig of entities
        self.assertTrue('Configuring' in coll_output, msg='Cannot find configuring step in log output!')
        self.assertTrue('Configured' in coll_output, msg='Cannot find finished configuring message in log output!')
        self.assertTrue('Received Configuration' in prod_output, msg='Cannot find received configuration message in log output!')

        # Check event building from replayed data
        self.assertTrue('Complete Event' in coll_output)

        # Check stop run signal received
        self.assertTrue('Received EORE Event' in coll_output)
        self.assertTrue('Stop Run received' in prod_output)

    def test_send_data(self):
        ''' Test the data sending function of the tlu_eudaq scan.

            The send raw data and stored raw data by the EudaqScan.handle_data() function is compared to the
            fixture to make sure that all data is handled.
        '''

        # Counter variable for calls to data send function
        self.n_calls = 0

        def SendEvent(data, skipped_triggers=None, event_counter=None):
            ''' Fake EUDAQ send function that is called per event.
            '''
            raw_data_table_snd.append(np.array([data]))
            self.n_calls += 1

        raw_data_file = os.path.join(data_folder, 'tlu_example_data.h5')
        raw_data_file_out = os.path.join(data_folder, 'tlu_example_data_out.h5')
        raw_data_file_snd = os.path.join(data_folder, 'tlu_example_data_snd.h5')

        scan = tlu_eudaq.EudaqScan()

        h5_file_snd = tb.open_file(raw_data_file_snd, mode='w')
        raw_data_table_snd = h5_file_snd.create_table(h5_file_snd.root, name='raw_data',
                                                      description=scan.data_dtype, title='data',
                                                      filters=tb.Filters(complib='blosc', complevel=5))

        scan.set_callback(SendEvent)

        # Create storage structures and variables that are not created since we fake readout
        scan.h5_file = tb.open_file(raw_data_file_out, mode='w')
        scan.data_table = scan.h5_file.create_table(scan.h5_file.root, name='raw_data',
                                                    description=scan.data_dtype, title='data',
                                                    filters=tb.Filters(complib='blosc', complevel=5))
        scan.meta_data_table = scan.h5_file.create_table(scan.h5_file.root, name='meta_data',
                                                         description=scan.meta_data_dtype, title='meta_data',
                                                         filters=tb.Filters(complib='blosc', complevel=5))
        # Fake data taking using raw data file
        with tb.open_file(raw_data_file) as in_file:
            meta_data = in_file.root.meta_data[:]
            raw_data = in_file.root.raw_data
            for readout in meta_data:
                index_start, index_stop = readout[0], readout[1]
                readout_meta_data = [readout[name] for name in readout.dtype.names]

                data_tuple = tuple([raw_data[index_start:index_stop]] + readout_meta_data)
                scan.handle_data(data_tuple)

        h5_file_snd.close()
        scan.h5_file.close()

        # Check raw data is stored locally when using scan_eudaq
        data_equal, error_msg = utils.compare_h5_files(raw_data_file, raw_data_file_out, node_names=['raw_data'])
        self.assertTrue(data_equal, msg=error_msg)

        # Check send raw data is complete and correct when using scan_eudaq
        data_equal, error_msg = utils.compare_h5_files(raw_data_file, raw_data_file_snd, node_names=['raw_data'])
        self.assertTrue(data_equal, msg=error_msg)

        self.assertEqual(scan.event_counter, self.n_calls)


if __name__ == '__main__':
    unittest.main()
