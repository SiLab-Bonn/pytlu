import time

from PyQt5 import QtWidgets
import pyqtgraph as pg
from pyqtgraph.dockarea import DockArea, Dock

from online_monitor.utils import utils
from online_monitor.receiver.receiver import Receiver


class PyTLU(Receiver):

    def setup_receiver(self):
        self.set_bidirectional_communication()  # We want to change converter settings

    def setup_widgets(self, parent, name):
        dock_area = DockArea()
        parent.addTab(dock_area, name)
        # Docks
        dock_rate = Dock("Particle rate (Trigger rate)", size=(400, 400))
        dock_status = Dock("Status", size=(800, 40))
        dock_area.addDock(dock_rate, 'above')
        dock_area.addDock(dock_status, 'top')

        # Status dock on top
        cw = QtWidgets.QWidget()
        cw.setStyleSheet("QWidget {background-color:white}")
        layout = QtWidgets.QGridLayout()
        cw.setLayout(layout)
        self.rate_label = QtWidgets.QLabel("Readout Rate\n0 Hz")
        self.timestamp_label = QtWidgets.QLabel("Data Timestamp\n")
        self.plot_delay_label = QtWidgets.QLabel("Plot Delay\n")
        self.spin_box = QtWidgets.QSpinBox(value=0)
        self.spin_box.setMaximum(1000000)
        self.spin_box.setSuffix(" Readouts")
        self.reset_button = QtWidgets.QPushButton('Reset')
        layout.addWidget(self.timestamp_label, 0, 0, 0, 1)
        layout.addWidget(self.plot_delay_label, 0, 1, 0, 1)
        layout.addWidget(self.rate_label, 0, 2, 0, 1)
        layout.addWidget(self.spin_box, 0, 6, 0, 1)
        layout.addWidget(self.reset_button, 0, 7, 0, 1)
        dock_status.addWidget(cw)

        # Connect widgets
        self.reset_button.clicked.connect(lambda: self.send_command('RESET'))
        self.spin_box.valueChanged.connect(lambda value: self.send_command(str(value)))

        # particle rate dock
        trigger_rate_graphics = pg.GraphicsLayoutWidget()
        trigger_rate_graphics.show()
        plot_trigger_rate = pg.PlotItem(labels={'left': 'Trigger Rate / kHz', 'bottom': 'Time / s'})
        self.trigger_rate_acc_curve = pg.PlotCurveItem(pen='#B00B13')
        self.trigger_rate_real_curve = pg.PlotCurveItem(pen='#228B22')

        # add legend
        legend_acc = pg.LegendItem(offset=(80, 10))
        legend_acc.setParentItem(plot_trigger_rate)
        legend_acc.addItem(self.trigger_rate_acc_curve, 'Accepted Trigger Rate')
        legend_real = pg.LegendItem(offset=(80, 50))
        legend_real.setParentItem(plot_trigger_rate)
        legend_real.addItem(self.trigger_rate_real_curve, 'Real Trigger Rate')

        # add items to plots and customize plots viewboxes
        plot_trigger_rate.addItem(self.trigger_rate_acc_curve)
        plot_trigger_rate.addItem(self.trigger_rate_real_curve)
        plot_trigger_rate.vb.setBackgroundColor('#E6E5F4')
        plot_trigger_rate.setXRange(-60, 0)
        plot_trigger_rate.getAxis('left').setZValue(0)
        plot_trigger_rate.getAxis('left').setGrid(155)

        # add plots to graphicslayout and layout to dock
        trigger_rate_graphics.addItem(plot_trigger_rate, row=0, col=1, rowspan=1, colspan=2)
        dock_rate.addWidget(trigger_rate_graphics)

        # add dict of all used plotcurveitems for individual handling of each plot
        self.plots = {'trigger_rate_acc': self.trigger_rate_acc_curve,
                      'trigger_rate_real': self.trigger_rate_real_curve}
        self.plot_delay = 0

    def deserialize_data(self, data):
        datar, meta = utils.simple_dec(data)
        return meta

    def handle_data_if_active(self, data):
        # look for TLU data in data stream
        if 'tlu' in data:
            # fill plots
            for key in data['tlu']:
                # if array not full, plot data only up to current array_index, 'indices' is keyword
                if data['indices'][key] < data['tlu'][key].shape[1]:
                    # set the plot data to the corresponding arrays where only the the values up to self.array_index are plotted
                    self.plots[key].setData(data['tlu'][key][0][:data['indices'][key]],
                                            data['tlu'][key][1][:data['indices'][key]], autoDownsample=True)

                # if array full, plot entire array
                elif data['indices'][key] >= data['tlu'][key].shape[1]:
                    # set the plot data to the corresponding arrays
                    self.plots[key].setData(data['tlu'][key][0],
                                            data['tlu'][key][1], autoDownsample=True)

        # set timestamp, plot delay and readour rate
        self.rate_label.setText("Readout Rate\n%d Hz" % data['fps'])
        self.timestamp_label.setText("Data Timestamp\n%s" % time.asctime(time.localtime(data['timestamp_stop'])))
        now = time.time()
        self.plot_delay = self.plot_delay * 0.9 + (now - data['timestamp_stop']) * 0.1
        self.plot_delay_label.setText("Plot Delay\n%s" % 'not realtime' if abs(self.plot_delay) > 5 else "%1.2f ms" % (self.plot_delay * 1.e3))
