#!/usr/bin/env python

from setuptools import setup
from setuptools import find_packages
from platform import system

version = '0.0.1'

setup(
    name='TLU',
    version=version,
    description='DAQ for TLU',
    url='https://github.com/SiLab-Bonn/tlu',
    license='',
    long_description='',
    author='Janek Fleper, Tomasz Hemperek',
    maintainer='Tomasz Hemperek',
    author_email='j.fleper@gmx.de,hemeprek@uni-bonn.de',
    maintainer_email='hemeprek@uni-bonn.de',
    install_requires=['basil-daq'],
    packages=find_packages(),
    include_package_data=True,  
    package_data={'': ['README.*', 'VERSION'], 'docs': ['*'], 'tlu': ['*.yaml', '*.bit']},
    platforms='any'
)
