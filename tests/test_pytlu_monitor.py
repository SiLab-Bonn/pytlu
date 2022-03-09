''' Script to check the pytlu modules for the online monitor

    Simulation producer, converter and receiver.
'''

import os
import sys
import unittest
import yaml
import subprocess
import time
import psutil
from PyQt5.QtWidgets import QApplication

from online_monitor import OnlineMonitor

import pytlu
pytlu_path = os.path.dirname(pytlu.__file__)
data_folder = os.path.abspath(os.path.join(pytlu_path, '..', 'data'))


# Create online monitor yaml config with pytlu monitor entities
def create_config_yaml():
    conf = {}
    # Add producer
    devices = {}
    devices['TLU_Producer'] = {'backend': 'tcp://127.0.0.1:8600',
                               'kind': 'pytlu_producer_sim',
                               'delay': 0.1,
                               'data_file': os.path.join(data_folder, 'tlu_example_data.h5')
                               }
    conf['producer_sim'] = devices
    # Add converter
    devices = {}
    devices['TLU_Converter'] = {'kind': 'pytlu_converter',
                                'frontend': 'tcp://127.0.0.1:8600',
                                'backend': 'tcp://127.0.0.1:8700'
                                }
    conf['converter'] = devices
    # Add receiver
    devices = {}
    devices['TLU'] = {'kind': 'pytlu_receiver',
                      'frontend': 'tcp://127.0.0.1:8700'
                      }
    conf['receiver'] = devices
    return yaml.dump(conf, default_flow_style=False)


# kill process by id, including subprocesses; works for linux and windows
def kill(proc):
    process = psutil.Process(proc.pid)
    for child_proc in process.children(recursive=True):
        child_proc.kill()
    process.kill()


def get_python_processes():  # return the number of python processes
    n_python = 0
    for proc in psutil.process_iter():
        try:
            if 'python' in proc.name():
                n_python += 1
        except psutil.AccessDenied:
            pass
    return n_python


def run_script_in_shell(script, arguments, command=None):
    if os.name == 'nt':
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        creationflags = 0
    return subprocess.Popen(
        "%s %s %s" % ('python' if not command else command, script, arguments),
        shell=True, creationflags=creationflags)


class TestOnlineMonitor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open('tmp_cfg.yml', 'w') as outfile:
            config_file = create_config_yaml()
            outfile.write(config_file)
        # Linux CIs run usually headless, thus virtual x server is needed for
        # gui testing
        if os.getenv('CI', False):
            from xvfbwrapper import Xvfb
            cls.vdisplay = Xvfb()
            cls.vdisplay.start()
        # Start the simulation producer to create some fake data
        cls.prod_sim_proc = run_script_in_shell('', 'tmp_cfg.yml',
                                                'start_producer_sim')
        # Start converter
        cls.conv_manager_proc = run_script_in_shell('', 'tmp_cfg.yml',
                                                    command='start_converter')
        # Create Gui
        time.sleep(2)
        cls.app = QApplication(sys.argv)
        cls.online_monitor = OnlineMonitor.OnlineMonitorApplication(
            'tmp_cfg.yml')
        time.sleep(2)

    @classmethod
    def tearDownClass(cls):  # Remove created files
        time.sleep(1)
        kill(cls.prod_sim_proc)
        kill(cls.conv_manager_proc)
        time.sleep(1)
        os.remove('tmp_cfg.yml')
        cls.online_monitor.close()
        time.sleep(1)

    def test_data_chain(self):
        ''' Checks for received data for the 2 receivers

            This effectively checks the full chain:
            producer --> converter --> receiver
        '''

        # Qt evsent loop does not run in tests, thus we have to trigger the
        # event queue manually
        self.app.processEvents()
        # Check all receivers present
        self.assertEqual(len(self.online_monitor.receivers), 1,
                         'Number of receivers wrong')
        self.app.processEvents()  # Clear event queue

        # Case 1: Activate status widget, data should be received since do not care about active tab
        self.online_monitor.tab_widget.setCurrentIndex(0)
        self.app.processEvents()
        time.sleep(1)
        self.app.processEvents()
        time.sleep(0.2)
        # Data structure to check for no data since receiver widget
        # is not active
        data_recv_0 = []
        self.app.processEvents()
        for receiver in self.online_monitor.receivers:
            data_recv_0.append(receiver.trigger_rate_acc_curve.getData())

        # Case 2: Activate TLU widget, receiver should show data
        self.online_monitor.tab_widget.setCurrentIndex(1)
        self.app.processEvents()
        time.sleep(1)
        self.app.processEvents()
        time.sleep(0.2)
        # Data structure to check for data since receiver widget
        # is active
        data_recv_1 = []
        for receiver in self.online_monitor.receivers:
            data_recv_1.append(receiver.trigger_rate_acc_curve.getData())

        self.assertTrue(len(data_recv_0[0][0]) != 0)  # check for emptyness of data list
        self.assertTrue(len(data_recv_1[0][0]) != 0)  # check for emptyness of data list

    #  Test the UI
    def test_ui(self):
        # 1 receiver + status widget expected
        self.assertEqual(self.online_monitor.tab_widget.count(), 2,
                         'Number of tab widgets wrong')


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestOnlineMonitor)
    unittest.TextTestRunner(verbosity=2).run(suite)
