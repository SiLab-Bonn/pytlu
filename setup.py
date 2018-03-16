#!/usr/bin/env python

from setuptools import setup
from setuptools import find_packages
from platform import system

version = '0.1.0'

setup(
    name='pytlu',
    version=version,
    description='DAQ for TLU',
    url='https://github.com/SiLab-Bonn/pytlu',
    license='',
    long_description='',
    author='Janek Fleper, Tomasz Hemperek, Yannick Dieter',
    maintainer='Tomasz Hemperek',
    author_email='j.fleper@gmx.de,hemeprek@uni-bonn.de,dieter@physik.uni-bonn.de',
    maintainer_email='hemeprek@uni-bonn.de',
    packages=find_packages(),
    include_package_data=True,  
    package_data={'': ['README.*'], 'pytlu': ['*.yaml', '*.bit']},
    entry_points={
        'console_scripts': [
            'pytlu = pytlu.tlu:main',
        ]
    },
    install_requires=[
          'basil_daq >= 2.4.10',
          'tables'
    ],
    platforms='any'
)
