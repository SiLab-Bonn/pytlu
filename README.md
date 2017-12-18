# pytlu

[![Build Status](https://travis-ci.org/SiLab-Bonn/pytlu.svg?branch=master)](https://travis-ci.org/SiLab-Bonn/pytlu)

DAQ software and firmware for the [Trigger Logic Unit (TLU)](https://twiki.cern.ch/twiki/bin/view/MimosaTelescope/TLU).

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

Install [conda](http://conda.pydata.org).

Install required packages:
```bash
conda install numpy bitarray pyyaml pytables 
```

Install pytlu via:
```bash
pip install pytlu
```

For development/testing see [.travis.yml](https://github.com/SiLab-Bonn/pytlu/blob/master/.travis.yml) for details.

## Usage

In order to get a description of the possible input arguments run:
```bash
pytlu -h
```

Example:
```bash
pytlu -t 10000 -c 10000 -oe CH1 --timeout 2
```
