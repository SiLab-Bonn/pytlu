#!/usr/bin/env python

from setuptools import setup
from setuptools import find_packages

import pytlu

with open('VERSION') as version_file:
    version = version_file.read().strip()

with open('requirements.txt') as f:
    install_requires = f.read().splitlines()

setup(
    name='pytlu',
    version=version,
    description='DAQ for EUDAQ TLU',
    url='https://github.com/SiLab-Bonn/pytlu',
    license='',
    long_description='',
    author='Janek Fleper, Tomasz Hemperek, Yannick Dieter, Jens Janssen',
    maintainer='Tomasz Hemperek',
    author_email='j.fleper@gmx.de, hemeprek@uni-bonn.de, dieter@physik.uni-bonn.de, janssen@physik.uni-bonn.de',
    maintainer_email='hemeprek@uni-bonn.de',
    packages=find_packages(),
    include_package_data=True,
    install_requires=install_requires,
    entry_points={
        'console_scripts': [
            'pytlu = pytlu.tlu:main',
            'pytlu_eudaq = pytlu.tlu_eudaq:main',
            'pytlu_monitor = pytlu.online_monitor.start_pytlu_online_monitor:main',
        ]
    },
    platforms='any'
)


# FIXME: bad practice to put code into setup.py
# Add the online_monitor pytlu plugins
try:
    import os
    from online_monitor.utils import settings
    # Get the absoulte path of this package
    package_path = os.path.dirname(pytlu.__file__)
    # Add online_monitor plugin folder to entity search paths
    settings.add_producer_sim_path(os.path.join(package_path,
                                                'online_monitor'))
    settings.add_converter_path(os.path.join(package_path,
                                             'online_monitor'))
    settings.add_receiver_path(os.path.join(package_path,
                                            'online_monitor'))
except ImportError:
    pass
