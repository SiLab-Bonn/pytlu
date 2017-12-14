# pytlu

[![Build Status](https://travis-ci.org/SiLab-Bonn/pytlu.svg?branch=master)](https://travis-ci.org/SiLab-Bonn/pytlu)

DAQ software and firmware for the [Trigger Logic Unit (TLU)](https://twiki.cern.ch/twiki/bin/view/MimosaTelescope/TLU).

**WORK IN PROGRESS...** 

## Description

The main features of the DAQ software and FPGA firmware are:

- protocol compatible with original firmware 
- integrated TDC (1.5625ns resolution, 640 MHz)
- configurable input inversion
- configurable input acceptance based on the pulse width
- trigger acceptance based on input rising distance
- continuous data storage of accepted triggers (trigger id, timestamp, TDC)
- testbench for software and firmware
- example fpga receiver module : https://github.com/SiLab-Bonn/basil/tree/master/firmware/modules/tlu

The data of all accepted triggers will be stored in a .h5 file. It contains the following data:

- timestamp of the trigger (64 bit number, 40 MHz)
- trigger id (32 bit number)
- distance between leading edge of input pulse and generation of trigger signal for each input channel (each of them 8 bit numbers)

## Installation

Before installation of pytlu run the following commands:
```bash
sudo add-apt-repository -y ppa:team-electronics/ppa
sudo apt-get update
sudo apt-get -y install iverilog-daily
sudo apt-get install -qq libhdf5-serial-dev
```

Then, install [conda](http://conda.pydata.org).

After this, run the following commands to install the required packages:
```bash
conda install --yes numpy bitarray pytest pyyaml pytables 
pip install cocotb
```
Install [Basil](https://github.com/SiLab-Bonn/basil).

Finish the installation of pytlu via:
```bash
python setup.py develop
```
In order to test the installation run the following commands:
```bash
cd tests 
py.test -s
```

## Usage

In order to get a description of the possible input arguments run:
```bash
pytlu -h
```

Example:
```bash
pytlu -t 10000 -c 10000 -oe CH0 --timeout 2
```
