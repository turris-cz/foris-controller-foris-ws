#
# foris-ws
# Copyright (C) 2019 CZ.NIC, z.s.p.o. (http://www.nic.cz/)
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
import re

from http import HTTPStatus
from typing import Optional, Tuple
from websockets.http import Headers
from werkzeug.contrib.cache import FileSystemCache

logger = logging.getLogger(__name__)

SESSIONS_DIR = "/tmp/foris-sessions"


def authenticate(path: str, request_headers: Headers) -> Optional[Tuple[int, Headers, bytes]]:
    """ Performs an authentication based on authentication token placed in cookie
    and session saved by Flask to filesystem.

    :param message: should contain clients initial request
    :rtype: bool
    """

    logger.debug("Logging using authentication cookie of the filesystem session.")

    if "Cookie" not in request_headers:
        logger.debug("Missing cookie.")
        return HTTPStatus.FORBIDDEN, Headers([]), b'Missing Cookie'

    foris_ws_session_re = re.search(r'session=([^;\s]*)', request_headers["Cookie"])
    if not foris_ws_session_re:
        logger.debug("Missing foris.ws.session in cookie.")
        return HTTPStatus.FORBIDDEN, Headers([]), b'Missing foris.ws.session in cookie'

    session_id = foris_ws_session_re.group(1)
    logger.debug("Using session id %s" % session_id)

    fs_cache = FileSystemCache(SESSIONS_DIR)
    data = fs_cache.get('session:' + session_id)

    if data is None:
        logger.debug("Session '%s' not found." % session_id)
        return HTTPStatus.FORBIDDEN, Headers([]), b'Session not found'

    if not data.get('logged', None):
        logger.debug("Session '%s' found but not logged." % session_id)
        return HTTPStatus.FORBIDDEN, Headers([]), b'Session not logged'

    logger.debug("Connection granted.")
    return None
