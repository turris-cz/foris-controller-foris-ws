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

import json
import logging
import re
import subprocess
import os

from http import HTTPStatus
from typing import Optional, Tuple
from websockets.http import Headers

logger = logging.getLogger(__name__)


def authenticate(path: str, request_headers: Headers) -> Optional[Tuple[int, Headers, bytes]]:
    """ Performs an authentication based on authentication token placed in cookie
        and ubus session object.

    :returns: None if auth was successfull or tuple(status_code, headers, body) to respond toclient
    """

    logger.debug("Logging using authentication cookie of the ubus session object.")

    if "Cookie" not in request_headers:
        logger.debug("Missing cookie.")
        return HTTPStatus.FORBIDDEN, Headers([]), b"Missing Cookie"

    foris_ws_session_re = re.search(r"foris.ws.session=([^;\s]*)", request_headers["Cookie"])
    if not foris_ws_session_re:
        logger.debug("Missing foris.ws.session in cookie.")
        return HTTPStatus.FORBIDDEN, Headers([]), b"Missing foris.ws.session in cookie"

    session_id = foris_ws_session_re.group(1)
    logger.debug("Using session id %s" % session_id)

    params = {
        "ubus_rpc_session": session_id or "",
        "scope": "ubus",
        "object": "websocket-listen",
        "function": "listen-allowed",
    }

    # Verify whether the client is able to access the listen function

    # We need to open a separate program to verify the session_id
    # beacause the program might be already listening on ubus in some mode
    args = ["ubus", "-S", "call", "session", "access", json.dumps(params)]
    if "FORIS_WS_UBUS_AUTH_SOCK" in os.environ:
        args.insert(1, os.environ["FORIS_WS_UBUS_AUTH_SOCK"])
        args.insert(1, "-s")

    proces = subprocess.Popen(args, stdout=subprocess.PIPE)
    stdout, _ = proces.communicate()
    if proces.returncode != 0:
        logger.debug("Session '%s' not found." % session_id)
        return HTTPStatus.FORBIDDEN, Headers([]), b"Session not found"

    data = json.loads(stdout)

    if not data["access"]:
        logger.debug("Connection denied.")
        return HTTPStatus.FORBIDDEN, Headers([]), b"Access for session denied"

    logger.debug("Connection granted.")
    return None
