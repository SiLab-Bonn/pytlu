# pytlu

[![Build Status](https://travis-ci.org/SiLab-Bonn/pytlu.svg?branch=master)](https://travis-ci.org/SiLab-Bonn/pytlu)

DAQ software and firmware for the EUDAQ [Trigger Logic Unit (TLU)](https://twiki.cern.ch/twiki/bin/view/MimosaTelescope/TLU).

## Description

The main features of the DAQ software and FPGA firmware are:

- Protocol compatible with original EUDAQ TLU firmware
- Integrated TDC (1.5625ns resolution, 640 MHz)
- Configurable input inversion
- Configurable input acceptance based on the pulse width
- Trigger acceptance based on the distance of the input pulse leading edge
- Continuous data storage of accepted triggers (trigger ID, timestamp, TDC)
- Testbench for software and firmware
- Example FPGA module provided by basil: [TLU/trigger FSM](https://github.com/SiLab-Bonn/basil/tree/master/firmware/modules/tlu)
- Data monitoring provided by the [online_monitor](https://github.com/SiLab-Bonn/online_monitor) package

The data of all accepted triggers will be stored in a HDF5/PyTables file. It contains the following data:

- Timestamp of the trigger (64-bit number, 40 MHz)
- Trigger ID (32-bit number)
- Distance between leading edge of input pulse and generation of trigger signal for each input channel (each of them 8-bit numbers)


## Online Monitor

The pytlu online monitor displays the trigger rate vs. time.
![Pytlu online monitor](online_monitor.png)

## Installation

Installation of [Anaconda Python](https://www.anaconda.com/download) or [Miniconda Python](https://conda.io/miniconda.html) is recommended.

Install dependencies:
```bash
conda install numpy psutil qtpy pyqt pyyaml pyzmq pytables
pip install pyusb pySiLibUSB
pip install 'basil_daq>=2.4.10,<3.0.0'
```

Install pytlu from PyPI:
```bash
pip install pytlu
```

OR install pytlu from sources:
```bash
python setup.py develop
```

For development/testing see [.travis.yml](https://github.com/SiLab-Bonn/pytlu/blob/master/.travis.yml) for details.

### USB Driver

Install libusb library by following the pySiLibUSB [installation guide](https://github.com/SiLab-Bonn/pySiLibUSB/wiki).

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

## EUDAQ integration

Pytlu can connect to the data acquisition framework [EUDAQ 1](https://github.com/eudaq/eudaq/tree/v1.x-dev), which is the common run control software used at *pixel test beams*. For the installation of EUDAQ 1.x please follow this [wiki](https://telescopes.desy.de/EUDAQ). To use the EUDAQ libraries within pytlu a [python wrapper](https://github.com/eudaq/eudaq/blob/v1.x-dev/python/PyEUDAQWrapper.py) is used. This wrapper is not build with default settings, thus the following cmake option must be specified when building EUDAQ `-DBUILD_python=ON`.

### Example minimal installation
The following commands setup EUDAQ 1.x development version for pytlu with minimum requirements (no [ROOT](https://root.cern.ch/), no [Qt](https://www.qt.io/)) and are tested on *Ubuntu 14.04 LTS*. This installation is sufficient to use and test the pytlu eudaq producer. The paths `/home/user/git` have to be adjusted to your system, of course.
#### Install dependencies
EUDAQ needs a recent [cmake3](https://cmake.org/download/) version that might not be shipped with your distribution. This is a [known issue](https://github.com/eudaq/eudaq/issues/466). To install a recent version under Ubuntu do
```bash
wget https://cmake.org/files/v3.11/cmake-3.11.1.tar.gz
tar xf cmake-3.11.1.tar.gz
cd cmake-3.11.1
./configure
make -j 4
sudo apt-get install checkinstall
sudo checkinstall
```
#### Install eudaq
```bash
git clone -b v1.x-dev https://github.com/eudaq/eudaq
cd eudaq/build
cmake -DBUILD_python=ON -DBUILD_gui=OFF -DBUILD_onlinemon=OFF -DBUILD_runsplitter=OFF -DUSE_ROOT=OFF ..
make install -j 4
```
The producer has to know the installation path of EUDAQ. One way is to specify `PYTHONPATH` to include the `python` folder in the EUDAQ directory, e.g.:
```bash
export PYTHONPATH="${PYTHONPATH}:/home/user/git/eudaq/python"
```
This is not needed when you mention the path of the eudaq installation for every call to `pytlu_eudaq` (see below).

**Run control GUI**

When you want to have the run control GUI for more convenient testing change the CMAKE option to:
```
-DBUILD_gui=ON
```
Warning: you have to avoid calling `cmake` within the anaconda environment, since the anaconda QT5 version cannot easily be used to build code.

### Usage with Pytlu
A simple command line interface is provided to start the pytlu producer:
```bash
pytlu_eudaq --help
```
Please read the help output for program parameters.
Since there are configuration parameters which exist within the [EUDAQ TLU controller](https://github.com/eudaq/eudaq/blob/v1.x-dev/producers/tlu/src/TLUController.cc) but not within the 
pytlu producer and vice versa, only the following configuration parameters can be set using the EUDAQ config file:
 
 - `TriggerInterval`
 - `AndMask`
 - `DutMask`

These are mapped properly to the format needed by pytlu. Of course, the usual parameters supplied by pytlu can be specified, e.g.:

```
pytlu_eudaq --timeout 5  -f /path/to/data/
```

Please note that the settings specified in the EUDAQ configuration file will overwrite the settings specified by the command line interface.


If you did not add the EUDAQ directory to the `PYTHONPATH` explicitly after installation (see above) you can give the path when running `pytlu_eudaq`, e.g.:

```
pytlu_eudaq --path /home/user/git/eudaq
```

### Debugging and testing
#### Replay feature
It is possible to replay a recorded pytlu raw data file with correct timing to test the system. This allows development and debugging without hardware. To replay a [pytlu raw data file](https://github.com/SiLab-Bonn/pytlu/blob/development/data/tlu_example_data.h5) one has to type:

```
pytlu_eudaq --replay /home/user/git/pytlu/data/tlu_example_data.h5
```

Sometimes it is not needed to replay the data in real time. You can delay the data sending for every read out by an arbitrary time by specifying a `delay` parameter. For example to add a delay of one second you can type:

```
pytlu_eudaq --replay tlu_example_data.h5 --delay 1
```

#### Unit test
A unit test is also available to test the complete chain: pytlu producer + DataConverter + Run Control. To test if everything is setup correctly open a console and make sure you added eudaq to you python path (see above). Then go to the [pytlu/tests](https://github.com/SiLab-Bonn/pytlu/tree/development/tests) folder and type
```
python test_eudaq.py
```
This test succeeds if everything is setup correctly.
