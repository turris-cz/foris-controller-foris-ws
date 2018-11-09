#
# foris-ws
# Copyright (C) 2018 CZ.NIC, z.s.p.o. (http://www.nic.cz/)
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

import logging

from typing import Optional, Tuple
from websockets.http import Headers

logger = logging.getLogger(__name__)


def authenticate(path: str, request_headers: Headers) -> Optional[Tuple[int, Headers, bytes]]:
    """ Authentication method which bypasses any authentication procedure
    :returns: None if auth was successfull or tuple(status_code, headers, body) to respond to client
    """
    logger.debug("Logging without any authentication.")
    return None
