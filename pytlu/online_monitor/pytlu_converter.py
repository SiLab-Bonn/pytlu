import numpy as np

from zmq.utils import jsonapi
from online_monitor.converter.transceiver import Transceiver
from online_monitor.utils import utils


class PyTLU(Transceiver):
    def setup_transceiver(self):
        self.set_bidirectional_communication()  # We want to be able to change the histogrammmer settings

    def setup_interpretation(self):
        # array for simulated status data
        self.status_data = np.zeros(shape=1, dtype=[('trigger_rate', 'f4')])
        # set array size; must be shape=(2, x); increase x to plot longer time span
        self.array_size = (2, 1600)

        # add arrays for plots; array[0] is time axis
        self.trigger_rate_array = np.zeros(shape=self.array_size)

        # add dicts for individual handling of each parameter
        # Using structured np.arrays produces weird VisibleDeprecationWarning
        # dict with all data arrays
        self.all_arrays = {'trigger_rate': self.trigger_rate_array}

        # dict with set of current data indices
        self.array_indices = {'trigger_rate': 0}

        # dict with set of start times of each key since last shifted through
        self.shift_cycle_times = {'trigger_rate': 0}

        # dict with set of current time indices
        self.update_time_indices = {'trigger_rate': 0}

        # dict with set of current times corresponding current data
        self.now = {'trigger_rate': 0}

        self.updateTime = 0
        self.fps = 0
        self.readout = 0
        self.n_readouts = 0

    def deserialze_data(self, data):  # According to pyBAR data serilization
        try:
            self.meta_data = jsonapi.loads(data)
        except ValueError:
            try:
                dtype = self.meta_data.pop('dtype')
                shape = self.meta_data.pop('shape')
                if self.meta_data:
                    try:
                        raw_data_array = np.frombuffer(buffer(data), dtype=dtype).reshape(shape)
                        return raw_data_array
                    except (KeyError, ValueError, TypeError):  # KeyError happens if meta data read is omitted; ValueError if np.frombuffer fails due to wrong sha
                        return None
            except AttributeError:  # Happens if first data is not meta data
                return None
        return {'meta_data': self.meta_data}

    def interpret_data(self, data):
        # add function to fill arrays with data and shift through
        def fill_arrays(array, data, time, time_index):
            array[0][time_index] = time
            array[1] = np.roll(array[1], 1)
            array[1][0] = data
            return array

        if data[0][1] is not None:
            meta_data = data[0][1]['meta_data']
            data_length = meta_data['data_length']
            timestamp_start = meta_data['timestamp_start']
            timestamp_stop = meta_data['timestamp_stop']
            self.status_data['trigger_rate'] = data_length / (timestamp_stop - timestamp_start) / 1e3  # trigger rate in kHz

            # fill time and data axes, here only one key (trigger rate) up to now
            for key in self.all_arrays:
                # update starting time (self.shift_cycle_time) if we just started or once shifted through the data array
                if self.array_indices[key] == 0 or self.array_indices[key] % self.array_size[1] == 0:

                    self.shift_cycle_times[key] = meta_data['timestamp_start']
                    self.update_time_indices[key] = 0

                # time since we started or last shifted through
                self.now[key] = self.shift_cycle_times[key] - meta_data['timestamp_start']

                self.all_arrays[key] = fill_arrays(self.all_arrays[key], self.status_data[key][0], self.now[key], self.update_time_indices[key])

                # increase indices for timing and data
                self.update_time_indices[key] += 1
                self.array_indices[key] += 1

            now = float(meta_data['timestamp_stop'])
            recent_fps = 1.0 / (now - self.updateTime)  # calculate FPS
            self.updateTime = now
            self.fps = self.fps * 0.7 + recent_fps * 0.3

            return [{'tlu': self.all_arrays, 'indices': self.array_indices, 'fps': self.fps, 'timestamp_stop': now}]

        self.readout += 1

        if self.n_readouts != 0:  # = 0 for infinite integration
            if self.readout % self.n_readouts == 0:
                self.trigger_rate_array = np.zeros_like(self.trigger_rate_array)
                self.array_indices['trigger_rate'] = 0
                self.update_time_indices['trigger_rate'] = 0
                self.readouts = 0

    def serialze_data(self, data):
        return jsonapi.dumps(data, cls=utils.NumpyEncoder)

    def handle_command(self, command):
        # received signal is 'ACTIVETAB tab' where tab is the name (str) of the selected tab in online monitor
        if command[0] == 'RESET':
            self.trigger_rate_array = np.zeros_like(self.trigger_rate_array)
            self.array_indices['trigger_rate'] = 0
            self.update_time_indices['trigger_rate'] = 0
        else:
            self.n_readouts = int(command[0])
