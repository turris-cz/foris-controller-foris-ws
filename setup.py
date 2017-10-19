#!/usr/bin/env python

#
# foris-ws
# Copyright (C) 2017 CZ.NIC, z.s.p.o. (http://www.nic.cz/)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA
#

from setuptools import setup
from foris_ws import version

DESCRIPTION = """
Implementation of websocket server for foris notification system.
"""

setup(
    name='foris-ws',
    version=version,
    author='CZ.NIC, z.s.p.o. (http://www.nic.cz/)',
    author_email='stepan.henek@nic.cz',
    packages=[
        'foris_ws',
        'foris_ws/authentication',
    ],
    scripts=['bin/foris-ws'],
    url='https://gitlab.labs.nic.cz/turris/foris-ws',
    license='COPYING',
    description=DESCRIPTION,
    long_description=open('README.rst').read(),
    requires=[
        'foris_client',
        'websocket_server',
    ],
    setup_requires=[
        'pytest-runner',
    ],
    tests_require=[
        'pytest',
        'websocket-client',
    ],
)
