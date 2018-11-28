# pytlu

[![Build Status](https://travis-ci.org/SiLab-Bonn/pytlu.svg?branch=master)](https://travis-ci.org/SiLab-Bonn/pytlu)

DAQ software and firmware for the EUDAQ [Trigger Logic Unit (TLU)](https://twiki.cern.ch/twiki/bin/view/MimosaTelescope/TLU).

## Description

The main features of the DAQ software and FPGA firmware are:

- protocol compatible with original firmware
- integrated TDC (1.5625ns resolution, 640 MHz)
- configurable input inversion
- configurable input acceptance based on the pulse width
- trigger acceptance based on the distance of the input pulse leading edge
- continuous data storage of accepted triggers (trigger id, timestamp, TDC)
- testbench for software and firmware
- example fpga receiver module : https://github.com/SiLab-Bonn/basil/tree/master/firmware/modules/tlu
- data monitoring via [online monitor](https://github.com/SiLab-Bonn/online_monitor)

The data of all accepted triggers will be stored in a .h5 file. It contains the following data:

- timestamp of the trigger (64 bit number, 40 MHz)
- trigger id (32 bit number)
- distance between leading edge of input pulse and generation of trigger signal for each input channel (each of them 8 bit numbers)


## Online Monitor

The pytlu online monitor displays the trigger rate vs. time.
![Pytlu online monitor](online_monitor.png)

## Installation

Install [conda](http://conda.pydata.org).

Install dependencies:
```bash
conda install numpy psutil qtpy pyqt pyyaml pyzmq pytables
pip install pyusb
pip install 'basil_daq>=2.4.10,<3.0.0'
```

Install pytlu:
```bash
pip install pytlu
```

Install libusb library by following this [guide](https://github.com/SiLab-Bonn/pySiLibUSB/wiki).

For development/testing see [.travis.yml](https://github.com/SiLab-Bonn/pytlu/blob/master/.travis.yml) for details.


If you are using the TLU for the first time, you need to add a permanent udev rule in order to access the TLU. Create the file `/etc/udev/rules.d/tlu.rules` and add the following lines.
For a RedHat-based distribution (e.g., SL7/Centos 7) use:
```
SUBSYSTEM=="usb", ATTR{idVendor}=="165d", ATTR{idProduct}=="0001", GROUP="NOROOTUSB", MODE="0666"
```
OR for a Debian-based distribution (e.g., Ubuntu) use:
```
SUBSYSTEM=="usb", ATTR{idVendor}=="165d", ATTR{idProduct}=="0001", MODE="0666"
```

## Usage

In order to get a description of the possible input arguments run:
```bash
pytlu -h
```

In order to start pytlu online monitor run:
```bash
pytlu_monitor
```

Example:
```bash
pytlu -t 10000 -c 10000 -oe CH1 --timeout 2
```
