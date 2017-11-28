# pytlu

[![Build Status](https://travis-ci.org/SiLab-Bonn/pytlu.svg?branch=master)](https://travis-ci.org/SiLab-Bonn/pytlu)

DAQ software and firmware for the [Trigger Logic Unit (TLU)](https://twiki.cern.ch/twiki/bin/view/MimosaTelescope/TLU).

**WORK IN PROGRESS...** 

## Description

TBD...

- protocol compatible with original firmware 
- integrated TDC (1.5625ns resolution)
- configurable input inversion
- configurable input acceptance based on the pulse with
- trigger acceptance based on input rising distance
- continuous data storage (trigger id, timestamp, TDC)
- testbanch for software and firmware
- example fpga reciver module : https://github.com/SiLab-Bonn/basil/tree/master/firmware/modules/tlu

## Instalation
Use [conda](http://conda.pydata.org) for python. 
See [.travis.yml](https://github.com/SiLab-Bonn/pytlu/blob/master/.travis.yml) for detail.

TBD...

## Usage

See:
```bash
pytlu -h
```

Example:
```bash
pytlu -t 10000 -c 10000 -oe CH0 --timeout 2
```
